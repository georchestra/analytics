"""cut over OGC compatibility views to persistent stores

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DIMENSIONS = """
    app_id, app_name, user_name, org_name, request_method, status_code,
    server_address, workspaces, layers, service, request, tiled, is_download,
    download_format, user_agent_family, referrer
"""
VALUES = "nb_req, response_time_median, response_time_min, response_time_max"


def _assert_source_is_preserved(source: str, target: str, bucket: str) -> None:
    columns = f"{bucket}, {DIMENSIONS}, {VALUES}"
    op.execute(
        f"""
        DO $validation$
        DECLARE missing_rows bigint;
        BEGIN
            SELECT count(*) INTO missing_rows
            FROM (
                SELECT {columns} FROM analytics.{source}
                EXCEPT ALL
                SELECT {columns} FROM analytics.{target}
            ) difference;
            IF missing_rows <> 0 THEN
                RAISE EXCEPTION
                    'Cutover refused: % rows from {source} are absent or different in {target}',
                    missing_rows;
            END IF;
        END
        $validation$
        """
    )


def _create_grain_view(name: str, store: str, bucket: str) -> None:
    op.execute(
        f"""
        CREATE VIEW analytics.{name} AS
        SELECT {bucket}, {DIMENSIONS}, {VALUES}
        FROM analytics.{store}
        """
    )


def _create_combined_view() -> None:
    selects = []
    for period, view, bucket in (
        ("hour", "ogc_summary_hourly", "bucket_hourly"),
        ("day", "ogc_summary_daily", "bucket_daily"),
        ("month", "ogc_summary_monthly", "bucket_monthly"),
    ):
        selects.append(
            f"""
            SELECT '{period}' AS period, {bucket} AS bucket,
                   {DIMENSIONS}, {VALUES}
            FROM analytics.{view}
            """
        )
    op.execute("CREATE VIEW analytics.ogc_summary AS " + " UNION ".join(selects))


def upgrade() -> None:
    op.execute(
        "SELECT pg_advisory_xact_lock(hashtext("
        "'georchestra.analytics.ogc_aggregation'))"
    )
    op.execute(
        """
        DO $preflight$
        BEGIN
            IF EXISTS (SELECT 1 FROM analytics.ogc_aggregation_queue) THEN
                RAISE EXCEPTION 'Cutover refused: OGC aggregation queue is not empty';
            END IF;
        END
        $preflight$
    """
    )

    _assert_source_is_preserved(
        "ogc_summary_hourly", "ogc_summary_hourly_store", "bucket_hourly"
    )
    _assert_source_is_preserved(
        "ogc_summary_daily", "ogc_summary_daily_store", "bucket_daily"
    )
    _assert_source_is_preserved(
        "ogc_summary_monthly", "ogc_summary_monthly_store", "bucket_monthly"
    )

    op.execute("DROP VIEW analytics.ogc_summary")
    op.execute(
        "ALTER MATERIALIZED VIEW analytics.ogc_summary_monthly "
        "RENAME TO ogc_summary_monthly_legacy"
    )
    op.execute(
        "ALTER MATERIALIZED VIEW analytics.ogc_summary_daily "
        "RENAME TO ogc_summary_daily_legacy"
    )
    op.execute(
        "ALTER MATERIALIZED VIEW analytics.ogc_summary_hourly "
        "RENAME TO ogc_summary_hourly_legacy"
    )

    _create_grain_view(
        "ogc_summary_hourly", "ogc_summary_hourly_store", "bucket_hourly"
    )
    _create_grain_view("ogc_summary_daily", "ogc_summary_daily_store", "bucket_daily")
    _create_grain_view(
        "ogc_summary_monthly", "ogc_summary_monthly_store", "bucket_monthly"
    )
    _create_combined_view()

    op.execute(
        """
        CREATE TABLE analytics.ogc_legacy_job_state (
            job_id integer PRIMARY KEY,
            proc_name text NOT NULL,
            hypertable_name text NOT NULL,
            was_scheduled boolean NOT NULL,
            disabled_at timestamptz NOT NULL DEFAULT now(),
            reenabled_at timestamptz,
            dropped_at timestamptz
        )
    """
    )


def downgrade() -> None:
    op.execute(
        "SELECT pg_advisory_xact_lock(hashtext("
        "'georchestra.analytics.ogc_aggregation'))"
    )
    op.execute(
        """
        DO $preflight$
        BEGIN
            IF to_regclass('analytics.ogc_summary_hourly_legacy') IS NULL
               OR to_regclass('analytics.ogc_summary_daily_legacy') IS NULL
               OR to_regclass('analytics.ogc_summary_monthly_legacy') IS NULL THEN
                RAISE EXCEPTION
                    'Downgrade refused: legacy aggregates were already removed';
            END IF;
        END
        $preflight$
    """
    )
    op.execute(
        """
        DO $jobs$
        DECLARE saved record;
        BEGIN
            FOR saved IN
                SELECT job_id FROM analytics.ogc_legacy_job_state
                WHERE was_scheduled AND dropped_at IS NULL
            LOOP
                IF EXISTS (
                    SELECT 1 FROM timescaledb_information.jobs
                    WHERE job_id = saved.job_id
                ) THEN
                    PERFORM alter_job(saved.job_id, scheduled => true);
                END IF;
            END LOOP;
        END
        $jobs$
    """
    )
    op.execute("DROP VIEW analytics.ogc_summary")
    op.execute("DROP VIEW analytics.ogc_summary_monthly")
    op.execute("DROP VIEW analytics.ogc_summary_daily")
    op.execute("DROP VIEW analytics.ogc_summary_hourly")
    op.execute(
        "ALTER MATERIALIZED VIEW analytics.ogc_summary_hourly_legacy "
        "RENAME TO ogc_summary_hourly"
    )
    op.execute(
        "ALTER MATERIALIZED VIEW analytics.ogc_summary_daily_legacy "
        "RENAME TO ogc_summary_daily"
    )
    op.execute(
        "ALTER MATERIALIZED VIEW analytics.ogc_summary_monthly_legacy "
        "RENAME TO ogc_summary_monthly"
    )
    _create_combined_view()
    op.execute("DROP TABLE analytics.ogc_legacy_job_state")
