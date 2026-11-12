import logging
import pathlib
import time
from datetime import datetime, timedelta
from logging.config import dictConfig

import click
import sqlalchemy as sa
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    Summary,
    push_to_gateway,
    write_to_textfile,
)

import georchestra_analytics_cli
from georchestra_analytics_cli import __version__, dist_name
from georchestra_analytics_cli.access_logs.AccessLogProcessor import AccessLogProcessor
from georchestra_analytics_cli.config import Config, load_config_from
from georchestra_analytics_cli.legacy_ogc import (
    DROP_CONFIRMATION,
    disable_legacy_ogc,
    drop_legacy_ogc,
    enable_legacy_ogc,
    validate_legacy_ogc,
)
from georchestra_analytics_cli.ogc_aggregation import aggregate_queued_ogc_buckets
from georchestra_analytics_cli.timescaledb import sync_timescaledb_policies
from georchestra_analytics_cli.utils import (
    write_prometheus_metrics,
    _seconds_until_next_cron_run,
)

module_logger = logging.getLogger(__name__)

conf: Config = None  # Global CLI config. Initialized at startup in the cli() function.

registry = CollectorRegistry()

s = Summary(
    "job_duration_seconds",
    "Duration of a job run",
    registry=registry,
    labelnames=["command"],
)
g = Gauge(
    "job_last_success_unixtime",
    "Last time a batch job successfully finished",
    registry=registry,
    labelnames=["command"],
)


@click.group(invoke_without_command=True, no_args_is_help=True)
@click.option("--version", default=False, is_flag=True)
@click.option("--config-file", envvar="GEORCHESTRA_ANALYTICS_CLI_CONFIG_FILE")
def cli(version, config_file):
    if version:
        print(f"{dist_name} {__version__}")

    global conf
    conf = load_config_from(config_file)
    # Configure logging
    logging_conf = conf.get_logging_config_as_dict()
    if logging_conf:
        dictConfig(logging_conf)

    module_logger.debug(f"Logging config: {logging_conf}")


# click.echo(f"Debug mode is {'on' if debug else 'off'}")


@cli.command()
@click.option(
    "--cron",
    type=str,
    default=None,
    help="Cron expression for execution schedule (configured timezone), e.g. '0 2 * * *'. Requires --loop.",
)
def buffer2db(cron: str | None):
    """
    Retrieve the logs data from the database buffer table, process them, write the result into the access_logs
    (hyper)table.
    By default it runs once. Use --cron to run continuously.
    """

    if cron:
        _seconds_until_next_cron_run(cron, conf.get_timezone())

    try:
        while True:
            with s.labels(command="buffer2db").time():
                log_processor = AccessLogProcessor()
                log_processor.process_buffer_table()
                _drain_ogc_queue()

                g.labels(command="buffer2db").set_to_current_time()

            if conf.is_metrics_enabled():
                write_prometheus_metrics(
                    registry,
                    conf.get_metrics_metrics_file_path(),
                    conf.get_metrics_pushgateway_url(),
                )

            if not cron:
                break

            sleep_seconds = _seconds_until_next_cron_run(
                cron,
                conf.get_timezone(),
            )
            module_logger.info(
                f"Next buffer2db run scheduled with cron '{cron}' ({conf.get_timezone()}) in {int(sleep_seconds)}s"
            )

            time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        module_logger.info("Interrupted stopping buffer2db")
    except Exception:
        module_logger.exception("buffer2db failed")
        raise


@cli.command()
@click.option("--file")
@click.option("--extra_info", "-e", multiple=True)
def file2db(file, extra_info):
    """
    Read the logs data from an access log file, process them, write the result into the access_logs
    (hyper)table.
    Using the (repeatable) --extra_info option, you can provide hardcoded values to include in the parsed lines.
    Keys should match keys that will be persisted in the DB, otherwise it will be pretty much useless
    e.g. --extra_info server_address=demo.georchestra.org --extra_info app_id=mapserver
    """
    with s.labels(command="file2db").time():
        split_extras = [x.split("=") for x in extra_info]
        extras_as_dict = dict((k, v) for k, v in split_extras)
        log_processor = AccessLogProcessor()
        log_processor.process_file_logs(file, extra_info=extras_as_dict)

        g.labels(command="file2db").set_to_current_time()

    if conf.is_metrics_enabled():
        write_prometheus_metrics(
            registry,
            conf.get_metrics_metrics_file_path(),
            conf.get_metrics_pushgateway_url(),
        )


@cli.command()
@click.option(
    "--start",
    help="Start datetime to start generating fake data. ISO format, can be timezone-aware, e.g. 2026-01-01T12:23 CET. Defaults to now in UTC -1 hour.",
    type=str,
)
@click.option(
    "--stop",
    help="Stop datetime for generating fake data. ISO format, can be timezone-aware. Defaults to now in UTC.",
    type=str,
)
@click.option(
    "--last_n_hours",
    help="Sets start to `stop` - n hours (this case supposes you don't set start time",
    type=int,
    default=1,
)
@click.option(
    "--rate",
    help="Max number of fake request per hour. The actual nb of request is randomized between 0 and `rate`. Default to 10.",
    type=int,
    default=10,
)
def fake2db(start: str = None, stop: str = None, last_n_hours: int = 1, rate: int = 10):
    """
    Generate fake records and insert them into the DB. Time granularity is the hour.
    :return:
    """
    global conf
    import pytz

    tz = pytz.timezone(conf.get_timezone())
    with s.labels(command="fake2db").time():
        import dateutil.parser as date_parser

        if stop is not None:
            stop_ts = date_parser.parse(stop)
        else:
            stop_ts = datetime.now(tz)
        if start is not None:
            start_ts = date_parser.parse(start)
        else:
            start_ts = stop_ts - timedelta(hours=last_n_hours)

        log_processor = AccessLogProcessor()
        log_processor.fake_log_records(start_ts, stop_ts, int(rate))

        g.labels(command="fake2db").set_to_current_time()

    if conf.is_metrics_enabled():
        write_prometheus_metrics(
            registry,
            conf.get_metrics_metrics_file_path(),
            conf.get_metrics_pushgateway_url(),
        )


def _drain_ogc_queue(batch_size: int | None = None) -> int:
    processed = 0
    while True:
        result = aggregate_queued_ogc_buckets(conf, batch_size=batch_size)
        processed += result.processed_buckets
        if result.processed_buckets == 0:
            return processed


@cli.command("aggregate-ogc")
@click.option(
    "--batch-size",
    type=click.IntRange(min=1),
    default=None,
    help="Maximum queued hourly buckets per transaction.",
)
def aggregate_ogc(batch_size: int | None):
    """Drain the durable OGC aggregation queue."""
    processed = _drain_ogc_queue(batch_size=batch_size)
    click.echo(f"OGC aggregation complete: processed_buckets={processed}")


@cli.group("legacy-ogc")
def legacy_ogc():
    """Validate, pause, restore or remove legacy OGC aggregates."""
    pass


@legacy_ogc.command("validate")
def validate_legacy():
    """Compare legacy aggregates with persistent stores."""
    result = validate_legacy_ogc(conf)
    click.echo(f"queue_size={result.queue_size}")
    for grain in result.grains:
        click.echo(
            f"{grain.grain}: source_rows={grain.source_rows}, "
            f"store_rows={grain.store_rows}, "
            f"source_requests={grain.source_requests}, "
            f"store_requests={grain.store_requests}, "
            f"source_missing_or_different={grain.source_missing_or_different}, "
            f"store_only_or_different={grain.store_only_or_different}"
        )
    if not result.safe:
        raise click.ClickException("legacy OGC validation is not safe for cutover")


@legacy_ogc.command("disable")
def disable_legacy():
    """Pause legacy TimescaleDB OGC jobs without deleting data."""
    changed = disable_legacy_ogc(conf)
    click.echo(f"Legacy OGC jobs disabled: changed={changed}")


@legacy_ogc.command("enable")
def enable_legacy():
    """Restore legacy jobs previously paused by this CLI."""
    changed = enable_legacy_ogc(conf)
    click.echo(f"Legacy OGC jobs enabled: changed={changed}")


@legacy_ogc.command("drop")
@click.option(
    "--confirm",
    required=True,
    help=f"Required destructive confirmation: {DROP_CONFIRMATION}",
)
def drop_legacy(confirm: str):
    """Permanently remove disabled legacy OGC continuous aggregates."""
    try:
        dropped = drop_legacy_ogc(conf, confirm)
    except (RuntimeError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Legacy OGC continuous aggregates removed: dropped={dropped}")


def _get_alembic_config() -> AlembicConfig:
    pkg_root = pathlib.Path(georchestra_analytics_cli.__file__).parent
    alembic_cfg = AlembicConfig(str(pkg_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(pkg_root / "alembic"))
    # The top-level Click callback already loaded --config-file. Pass that exact
    # object to env.py instead of making Alembic silently reload only the env var.
    alembic_cfg.attributes["app_config"] = conf
    return alembic_cfg


@cli.group()
def db():
    """Database schema migration commands."""
    pass


@db.command()
@click.option("--revision", default="head", show_default=True, help="Target revision.")
def upgrade(revision):
    """Apply pending migrations up to the target revision."""
    alembic_command.upgrade(_get_alembic_config(), revision)


@db.command()
def current():
    """Show the current migration revision."""
    alembic_command.current(_get_alembic_config(), verbose=True)


def _database_revision_status(revision: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    alembic_cfg = _get_alembic_config()
    expected = tuple(
        sorted(item.revision for item in ScriptDirectory.from_config(alembic_cfg).get_revisions(revision))
    )
    engine = sa.create_engine(conf.get_db_connection_string())
    try:
        with engine.connect() as connection:
            current = tuple(
                sorted(
                    MigrationContext.configure(
                        connection, opts={"version_table_schema": "analytics"}
                    ).get_current_heads()
                )
            )
    finally:
        engine.dispose()
    return current, expected


@db.command("require-revision")
@click.option("--revision", default="head", show_default=True)
def require_revision(revision: str):
    """Fail unless the database is exactly at the requested revision."""
    current, expected = _database_revision_status(revision)
    if current != expected:
        raise click.ClickException(
            f"database revision mismatch: current={current or ('unversioned',)}, expected={expected}"
        )
    click.echo(f"Database revision ready: {', '.join(current)}")


@db.command()
@click.option(
    "--revision",
    default="0001",
    show_default=True,
    help="Revision to record without running migrations.",
)
def stamp(revision):
    """Record a revision without running migrations (existing installs only)."""
    alembic_command.stamp(_get_alembic_config(), revision)


@db.command("bootstrap-existing")
@click.option(
    "--revision",
    default="0001",
    show_default=True,
    help="Baseline revision to record after validating an existing schema.",
)
def bootstrap_existing(revision):
    """Safely baseline an existing, unversioned analytics database."""
    revisions, missing = _inspect_existing_baseline()
    if revisions:
        click.echo(
            "Database already versioned; baseline stamp skipped: "
            + ", ".join(revisions)
        )
        return
    if missing:
        raise click.ClickException(
            "Existing database does not match baseline 0001; missing relations: "
            + ", ".join(missing)
        )

    alembic_command.stamp(_get_alembic_config(), revision)
    click.echo(f"Existing database stamped at baseline revision {revision}")


def _inspect_existing_baseline():
    """Return recorded revisions and missing baseline relations without writes."""
    engine = sa.create_engine(conf.get_db_connection_string())
    required_relations = (
        "analytics.opentelemetry_buffer",
        "analytics.access_logs",
        "analytics.ogc_summary_hourly",
        "analytics.ogc_summary_daily",
        "analytics.ogc_summary_monthly",
        "analytics.ogc_summary",
    )

    try:
        with engine.connect() as connection:
            version_table = connection.scalar(
                sa.text("SELECT to_regclass('analytics.alembic_version')")
            )
            if version_table is not None:
                revisions = connection.execute(
                    sa.text("SELECT version_num FROM analytics.alembic_version")
                ).scalars().all()
                if revisions:
                    return revisions, []

            missing = [
                relation
                for relation in required_relations
                if connection.scalar(
                    sa.text("SELECT to_regclass(:relation)"),
                    {"relation": relation},
                )
                is None
            ]
    finally:
        engine.dispose()

    return [], missing


@db.command("check-baseline")
def check_baseline():
    """Read-only validation for adopting an existing database at 0001."""
    revisions, missing = _inspect_existing_baseline()
    if revisions:
        click.echo("Database already versioned: " + ", ".join(revisions))
        return
    if missing:
        raise click.ClickException(
            "Existing database does not match baseline 0001; missing relations: "
            + ", ".join(missing)
        )
    click.echo("Existing unversioned database matches baseline revision 0001")


@db.command("sync-policies")
def sync_policies():
    """Apply configured TimescaleDB policies to analytics.access_logs."""
    result = sync_timescaledb_policies(conf)
    click.echo(
        f"TimescaleDB policies synchronized: chunk_interval={result.chunk_interval}, "
        f"retention={result.retention_action}"
    )


@db.command()
@click.option("--revision", default="-1", show_default=True, help="Target revision.")
def downgrade(revision):
    """Downgrade to a previous revision."""
    alembic_command.downgrade(_get_alembic_config(), revision)


if __name__ == "__main__":
    # Run CLI
    cli()
