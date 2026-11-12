"""persist OGC aggregates in ordinary PostgreSQL tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05

This is a preservation migration. It creates and seeds persistent OGC stores while
leaving the existing TimescaleDB continuous aggregates and all their policies intact.
The application cutover is intentionally deferred to a later revision.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DIMENSION_COLUMNS = """
    app_id,
    app_name,
    user_name,
    org_name,
    request_method,
    status_code,
    server_address,
    workspaces,
    layers,
    service,
    request,
    tiled,
    is_download,
    download_format,
    user_agent_family,
    referrer
"""

VALUE_COLUMNS = """
    nb_req,
    response_time_median,
    response_time_min,
    response_time_max
"""


def _create_store(table: str, bucket: str, nb_req_type: str) -> None:
    op.execute(
        f"""
        CREATE TABLE analytics.{table} (
            {bucket} timestamptz NOT NULL,
            app_id text,
            app_name text,
            user_name text,
            org_name text,
            request_method text,
            status_code integer,
            server_address text,
            workspaces text,
            layers text,
            service text,
            request text,
            tiled text,
            is_download text,
            download_format text,
            user_agent_family text,
            referrer text,
            nb_req {nb_req_type} NOT NULL CHECK (nb_req >= 0),
            response_time_median double precision,
            response_time_min double precision,
            response_time_max double precision,
            CONSTRAINT uq_{table}_dimensions
                UNIQUE NULLS NOT DISTINCT (
                    {bucket},
                    app_id,
                    app_name,
                    user_name,
                    org_name,
                    request_method,
                    status_code,
                    server_address,
                    workspaces,
                    layers,
                    service,
                    request,
                    tiled,
                    is_download,
                    download_format,
                    user_agent_family,
                    referrer
                )
        )
        """
    )


def _seed_store(source: str, target: str, bucket: str) -> None:
    op.execute(
        f"""
        INSERT INTO analytics.{target} (
            {bucket},
            {DIMENSION_COLUMNS},
            {VALUE_COLUMNS}
        )
        SELECT
            {bucket},
            {DIMENSION_COLUMNS},
            {VALUE_COLUMNS}
        FROM analytics.{source}
        """
    )


def _validate_store(source: str, target: str, bucket: str) -> None:
    columns = f"{bucket}, {DIMENSION_COLUMNS}, {VALUE_COLUMNS}"
    op.execute(
        f"""
        DO $validation$
        DECLARE
            source_count bigint;
            target_count bigint;
            source_total numeric;
            target_total numeric;
            source_min timestamptz;
            target_min timestamptz;
            source_max timestamptz;
            target_max timestamptz;
        BEGIN
            SELECT count(*), sum(nb_req), min({bucket}), max({bucket})
              INTO source_count, source_total, source_min, source_max
              FROM analytics.{source};

            SELECT count(*), sum(nb_req), min({bucket}), max({bucket})
              INTO target_count, target_total, target_min, target_max
              FROM analytics.{target};

            IF source_count IS DISTINCT FROM target_count
               OR source_total IS DISTINCT FROM target_total
               OR source_min IS DISTINCT FROM target_min
               OR source_max IS DISTINCT FROM target_max THEN
                RAISE EXCEPTION
                    'OGC seed mismatch for {target}: source=(%, %, %, %), target=(%, %, %, %)',
                    source_count, source_total, source_min, source_max,
                    target_count, target_total, target_min, target_max;
            END IF;

            IF EXISTS (
                (SELECT {columns} FROM analytics.{source}
                 EXCEPT ALL
                 SELECT {columns} FROM analytics.{target})
                UNION ALL
                (SELECT {columns} FROM analytics.{target}
                 EXCEPT ALL
                 SELECT {columns} FROM analytics.{source})
            ) THEN
                RAISE EXCEPTION 'OGC row validation failed for {target}';
            END IF;
        END
        $validation$
        """
    )


def upgrade() -> None:
    op.execute(
        "SELECT pg_advisory_xact_lock(hashtext("
        "'georchestra.analytics.ogc_aggregation'))"
    )

    op.execute("""
        DO $preflight$
        BEGIN
            IF to_regclass('analytics.ogc_summary_hourly') IS NULL
               OR to_regclass('analytics.ogc_summary_daily') IS NULL
               OR to_regclass('analytics.ogc_summary_monthly') IS NULL THEN
                RAISE EXCEPTION
                    'Revision 0002 requires all three OGC continuous aggregates';
            END IF;
        END
        $preflight$
    """)

    _create_store("ogc_summary_hourly_store", "bucket_hourly", "bigint")
    _create_store("ogc_summary_daily_store", "bucket_daily", "numeric")
    _create_store("ogc_summary_monthly_store", "bucket_monthly", "numeric")

    op.execute("""
        CREATE TABLE analytics.ogc_aggregation_queue (
            bucket_hourly timestamptz PRIMARY KEY,
            queued_at timestamptz NOT NULL DEFAULT now(),
            attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            last_error text
        )
    """)

    op.execute("""
        CREATE TABLE analytics.ogc_aggregation_state (
            singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
            calculation_version integer NOT NULL CHECK (calculation_version > 0),
            seeded_at timestamptz NOT NULL,
            last_success_at timestamptz,
            last_error_at timestamptz,
            last_error text
        )
    """)

    _seed_store("ogc_summary_hourly", "ogc_summary_hourly_store", "bucket_hourly")
    _seed_store("ogc_summary_daily", "ogc_summary_daily_store", "bucket_daily")
    _seed_store("ogc_summary_monthly", "ogc_summary_monthly_store", "bucket_monthly")

    _validate_store(
        "ogc_summary_hourly", "ogc_summary_hourly_store", "bucket_hourly"
    )
    _validate_store("ogc_summary_daily", "ogc_summary_daily_store", "bucket_daily")
    _validate_store(
        "ogc_summary_monthly", "ogc_summary_monthly_store", "bucket_monthly"
    )

    op.execute("""
        INSERT INTO analytics.ogc_aggregation_state (
            singleton,
            calculation_version,
            seeded_at
        ) VALUES (true, 1, now())
    """)


def downgrade() -> None:
    op.execute(
        "SELECT pg_advisory_xact_lock(hashtext("
        "'georchestra.analytics.ogc_aggregation'))"
    )
    op.execute("DROP TABLE IF EXISTS analytics.ogc_aggregation_queue")
    op.execute("DROP TABLE IF EXISTS analytics.ogc_aggregation_state")
    op.execute("DROP TABLE IF EXISTS analytics.ogc_summary_monthly_store")
    op.execute("DROP TABLE IF EXISTS analytics.ogc_summary_daily_store")
    op.execute("DROP TABLE IF EXISTS analytics.ogc_summary_hourly_store")
