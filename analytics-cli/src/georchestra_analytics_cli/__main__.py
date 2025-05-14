import importlib
import logging
import timeit
from logging.config import dictConfig
from datetime import datetime, timedelta, timezone

import click
from prometheus_client import CollectorRegistry, Gauge, Summary, write_to_textfile, push_to_gateway

from georchestra_analytics_cli.access_logs.AccessLogProcessor import AccessLogProcessor
from georchestra_analytics_cli.config import Config, load_config_from
from georchestra_analytics_cli.utils import write_prometheus_metrics
from georchestra_analytics_cli import __version__, dist_name

module_logger = logging.getLogger(__name__)

conf: Config  = None # Global CLI config. Initialized at startup in the cli() function.

registry = CollectorRegistry()

s = Summary("job_duration_seconds", "Duration of a job run", registry=registry, labelnames=["command"])
g = Gauge(
            "job_last_success_unixtime",
            "Last time a batch job successfully finished",
            registry=registry,
            labelnames=["command"]
        )

@click.group(invoke_without_command=True, no_args_is_help=True)
@click.option("--version", default=False, is_flag=True)
@click.option("--config-file", envvar='GEORCHESTRA_ANALYTICS_CLI_CONFIG_FILE')
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
def buffer2db():
    """
    Retrieve the logs data from the database buffer table, process them, write the result into the access_logs
    (hyper)table.
    :return:
    """
    with s.labels(command="buffer2db").time():
        log_processor = AccessLogProcessor()
        log_processor.process_buffer_table()

        g.labels(command="buffer2db").set_to_current_time()

    if conf.is_metrics_enabled():
        write_prometheus_metrics(registry, conf.get_metrics_metrics_file_path(), conf.get_metrics_pushgateway_url())


@cli.command()
@click.option("--file")
def file2db(file):
    """
    Read the logs data from an access log file, process them, write the result into the access_logs
    (hyper)table.
    :return:
    """
    with s.labels(command="file2db").time():
        log_processor = AccessLogProcessor()
        log_processor.process_file_logs(file)

        g.labels(command="file2db").set_to_current_time()

    if conf.is_metrics_enabled():
        write_prometheus_metrics(registry, conf.get_metrics_metrics_file_path(), conf.get_metrics_pushgateway_url())


@cli.command()
@click.option("--start", help='Start datetime to start generating fake data. ISO format, in UTC timezone. Defaults to now - 8 days.')
@click.option("--stop", help='Stop datetime for generating fake data. ISO format, in UTC timezone. Default to now.')
@click.option("--rate", help='Max number of fake request per hour. The actual nb of request is randomized between 0 and `rate`. Default to 10.', default=10)
def fake2db(start, stop, rate = 10):
    """
    Generate fake records and insert them into the DB
    :return:
    """
    global conf
    with s.labels(command="fake2db").time():
        import dateutil.parser as date_parser
        if start is not None:
            start_ts = date_parser.parse(start)
        else:
            start_ts = datetime.now(timezone.utc) - timedelta(days=8)
        if stop is not None:
            stop_ts = date_parser.parse(stop)
        else:
            stop_ts = datetime.now(timezone.utc)

        log_processor = AccessLogProcessor()
        log_processor.fake_log_records(start_ts, stop_ts, int(rate))

        g.labels(command="fake2db").set_to_current_time()

    if conf.is_metrics_enabled():
        write_prometheus_metrics(registry, conf.get_metrics_metrics_file_path(), conf.get_metrics_pushgateway_url())


if __name__ == "__main__":
    # Run CLI
    cli()
