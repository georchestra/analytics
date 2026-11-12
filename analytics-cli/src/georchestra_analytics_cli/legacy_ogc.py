"""Validation and lifecycle operations for legacy TimescaleDB OGC aggregates."""

from dataclasses import dataclass

from sqlalchemy import create_engine, text

from georchestra_analytics_cli.config import Config

DROP_CONFIRMATION = "DROP_LEGACY_OGC_AGGREGATES"
DIMENSIONS = """
    app_id, app_name, user_name, org_name, request_method, status_code,
    server_address, workspaces, layers, service, request, tiled, is_download,
    download_format, user_agent_family, referrer
"""
VALUES = "nb_req, response_time_median, response_time_min, response_time_max"
GRAINS = (
    ("hourly", "bucket_hourly"),
    ("daily", "bucket_daily"),
    ("monthly", "bucket_monthly"),
)


@dataclass(frozen=True)
class GrainValidation:
    grain: str
    source_rows: int
    store_rows: int
    source_requests: int
    store_requests: int
    source_missing_or_different: int
    store_only_or_different: int


@dataclass(frozen=True)
class LegacyValidation:
    queue_size: int
    grains: tuple[GrainValidation, ...]

    @property
    def safe(self) -> bool:
        return self.queue_size == 0 and all(
            grain.source_missing_or_different == 0 for grain in self.grains
        )


def _source_name(connection, grain: str) -> str:
    legacy = f"ogc_summary_{grain}_legacy"
    if connection.scalar(
        text("SELECT to_regclass(:name) IS NOT NULL"),
        {"name": f"analytics.{legacy}"},
    ):
        return legacy
    return f"ogc_summary_{grain}"


def _validate_with_connection(connection) -> LegacyValidation:
    queue_size = connection.scalar(
        text("SELECT count(*) FROM analytics.ogc_aggregation_queue")
    )
    results = []
    for grain, bucket in GRAINS:
        source = _source_name(connection, grain)
        store = f"ogc_summary_{grain}_store"
        columns = f"{bucket}, {DIMENSIONS}, {VALUES}"
        row = (
            connection.execute(
                text(
                    f"""
                SELECT
                    (SELECT count(*) FROM analytics.{source}) AS source_rows,
                    (SELECT count(*) FROM analytics.{store}) AS store_rows,
                    COALESCE((SELECT sum(nb_req) FROM analytics.{source}), 0) AS source_requests,
                    COALESCE((SELECT sum(nb_req) FROM analytics.{store}), 0) AS store_requests,
                    (SELECT count(*) FROM (
                        SELECT {columns} FROM analytics.{source}
                        EXCEPT ALL
                        SELECT {columns} FROM analytics.{store}
                    ) missing) AS source_missing,
                    (SELECT count(*) FROM (
                        SELECT {columns} FROM analytics.{store}
                        EXCEPT ALL
                        SELECT {columns} FROM analytics.{source}
                    ) extra) AS store_only
                """
                )
            )
            .mappings()
            .one()
        )
        results.append(
            GrainValidation(
                grain=grain,
                source_rows=row["source_rows"],
                store_rows=row["store_rows"],
                source_requests=int(row["source_requests"]),
                store_requests=int(row["store_requests"]),
                source_missing_or_different=row["source_missing"],
                store_only_or_different=row["store_only"],
            )
        )
    return LegacyValidation(queue_size=queue_size, grains=tuple(results))


def validate_legacy_ogc(config: Config) -> LegacyValidation:
    engine = create_engine(config.get_db_connection_string())
    try:
        with engine.connect() as connection:
            return _validate_with_connection(connection)
    finally:
        engine.dispose()


def disable_legacy_ogc(config: Config) -> int:
    """Pause legacy OGC jobs without deleting policies or aggregate data."""
    engine = create_engine(config.get_db_connection_string())
    changed = 0
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "SELECT pg_advisory_xact_lock(hashtext("
                    "'georchestra.analytics.ogc_aggregation'))"
                )
            )
            jobs = connection.execute(
                text(
                    """
                    SELECT job_id, proc_name, hypertable_name, scheduled
                    FROM timescaledb_information.jobs
                    WHERE hypertable_schema = 'analytics'
                      AND hypertable_name IN (
                          'ogc_summary_hourly_legacy',
                          'ogc_summary_daily_legacy',
                          'ogc_summary_monthly_legacy'
                      )
                    ORDER BY job_id
                """
                )
            ).mappings()
            for job in jobs:
                existing = connection.scalar(
                    text(
                        """
                        SELECT 1 FROM analytics.ogc_legacy_job_state
                        WHERE job_id = :job_id
                    """
                    ),
                    {"job_id": job["job_id"]},
                )
                if job["scheduled"] or not existing:
                    connection.execute(
                        text(
                            """
                            INSERT INTO analytics.ogc_legacy_job_state (
                                job_id, proc_name, hypertable_name, was_scheduled,
                                disabled_at, reenabled_at, dropped_at
                            ) VALUES (
                                :job_id, :proc_name, :hypertable_name, :scheduled,
                                now(), NULL, NULL
                            )
                            ON CONFLICT (job_id) DO UPDATE SET
                                proc_name = EXCLUDED.proc_name,
                                hypertable_name = EXCLUDED.hypertable_name,
                                was_scheduled = EXCLUDED.was_scheduled,
                                disabled_at = now(),
                                reenabled_at = NULL,
                                dropped_at = NULL
                        """
                        ),
                        dict(job),
                    )
                if job["scheduled"]:
                    connection.execute(
                        text("SELECT alter_job(:job_id, scheduled => false)"),
                        {"job_id": job["job_id"]},
                    )
                    changed += 1
    finally:
        engine.dispose()
    return changed


def enable_legacy_ogc(config: Config) -> int:
    """Restore jobs that were scheduled when disable_legacy_ogc first paused them."""
    engine = create_engine(config.get_db_connection_string())
    changed = 0
    try:
        with engine.begin() as connection:
            jobs = connection.execute(
                text(
                    """
                    SELECT state.job_id
                    FROM analytics.ogc_legacy_job_state state
                    JOIN timescaledb_information.jobs job USING (job_id)
                    WHERE state.was_scheduled
                      AND state.dropped_at IS NULL
                      AND NOT job.scheduled
                    ORDER BY state.job_id
                """
                )
            ).scalars()
            for job_id in jobs:
                connection.execute(
                    text("SELECT alter_job(:job_id, scheduled => true)"),
                    {"job_id": job_id},
                )
                connection.execute(
                    text(
                        """
                        UPDATE analytics.ogc_legacy_job_state
                        SET reenabled_at = now()
                        WHERE job_id = :job_id
                    """
                    ),
                    {"job_id": job_id},
                )
                changed += 1
    finally:
        engine.dispose()
    return changed


def drop_legacy_ogc(config: Config, confirmation: str) -> int:
    """Permanently remove disabled legacy OGC continuous aggregates."""
    if confirmation != DROP_CONFIRMATION:
        raise ValueError(f"confirmation must be exactly {DROP_CONFIRMATION}")

    engine = create_engine(config.get_db_connection_string())
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "SELECT pg_advisory_xact_lock(hashtext("
                    "'georchestra.analytics.ogc_aggregation'))"
                )
            )
            missing_legacy = connection.scalar(
                text(
                    """
                    SELECT count(*)
                    FROM (VALUES
                        ('analytics.ogc_summary_hourly_legacy'),
                        ('analytics.ogc_summary_daily_legacy'),
                        ('analytics.ogc_summary_monthly_legacy')
                    ) names(name)
                    WHERE to_regclass(name) IS NULL
                """
                )
            )
            if missing_legacy:
                raise RuntimeError(
                    "legacy OGC removal refused: legacy aggregates are missing"
                )
            validation = _validate_with_connection(connection)
            if not validation.safe:
                raise RuntimeError(
                    "legacy OGC removal refused: queue or validation differences remain"
                )
            scheduled = connection.scalar(
                text(
                    """
                    SELECT count(*)
                    FROM timescaledb_information.jobs
                    WHERE hypertable_schema = 'analytics'
                      AND hypertable_name IN (
                          'ogc_summary_hourly_legacy',
                          'ogc_summary_daily_legacy',
                          'ogc_summary_monthly_legacy'
                      )
                      AND scheduled
                """
                )
            )
            if scheduled:
                raise RuntimeError(
                    "legacy OGC removal refused: disable legacy jobs first"
                )
            for grain in ("monthly", "daily", "hourly"):
                connection.execute(
                    text(
                        f"DROP MATERIALIZED VIEW "
                        f"analytics.ogc_summary_{grain}_legacy"
                    )
                )
            connection.execute(
                text(
                    """
                    UPDATE analytics.ogc_legacy_job_state
                    SET dropped_at = now()
                    WHERE dropped_at IS NULL
                """
                )
            )
            return 3
    finally:
        engine.dispose()
