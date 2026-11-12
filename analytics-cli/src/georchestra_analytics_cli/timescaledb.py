"""Reconcile operational TimescaleDB settings with the CLI configuration."""

from dataclasses import dataclass

from sqlalchemy import create_engine, text

from georchestra_analytics_cli.config import Config


@dataclass(frozen=True)
class PolicySyncResult:
    chunk_interval: str
    retention_action: str


def sync_timescaledb_policies(config: Config) -> PolicySyncResult:
    """Apply the configured access_logs chunk interval and retention policy."""
    engine = create_engine(config.get_db_connection_string())
    with engine.begin() as connection:
        connection.execute(
            text(
                "SELECT pg_advisory_xact_lock("
                "hashtext('georchestra_analytics_sync_timescaledb_policies'))"
            )
        )

        chunk_interval = config.get_timescaledb_chunk_interval()
        drop_after = config.get_timescaledb_retention_drop_after()
        schedule_interval = config.get_timescaledb_retention_schedule_interval()

        connection.execute(
            text(
                "SELECT set_chunk_time_interval("
                "'analytics.access_logs', CAST(:chunk_interval AS interval))"
            ),
            {"chunk_interval": chunk_interval},
        )

        retention_job = connection.execute(
            text(
                "SELECT job_id, "
                "       (config->>'drop_after')::interval = CAST(:drop_after AS interval) "
                "       AND schedule_interval = CAST(:schedule_interval AS interval) AS matches "
                "FROM timescaledb_information.jobs "
                "WHERE proc_name = 'policy_retention' "
                "  AND hypertable_schema = 'analytics' "
                "  AND hypertable_name = 'access_logs'"
            ),
            {
                "drop_after": drop_after,
                "schedule_interval": schedule_interval,
            },
        ).mappings().one_or_none()

        if retention_job is None:
            retention_action = "created"
        elif retention_job["matches"]:
            retention_action = "unchanged"
        else:
            connection.execute(
                text(
                    "SELECT remove_retention_policy("
                    "'analytics.access_logs', if_exists => TRUE)"
                )
            )
            retention_action = "updated"

        if retention_action != "unchanged":
            connection.execute(
                text(
                    "SELECT add_retention_policy("
                    "'analytics.access_logs', "
                    "drop_after => CAST(:drop_after AS interval), "
                    "schedule_interval => CAST(:schedule_interval AS interval))"
                ),
                {
                    "drop_after": drop_after,
                    "schedule_interval": schedule_interval,
                },
            )

    return PolicySyncResult(
        chunk_interval=chunk_interval,
        retention_action=retention_action,
    )
