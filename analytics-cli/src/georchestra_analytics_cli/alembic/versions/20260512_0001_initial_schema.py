"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-05-12

This revision captures the full schema as it existed at v2.0.0 — the baseline for all
future Alembic-managed migrations.

For existing deployments (schema already created by Docker entrypoint SQL files), run:
    analytics-cli db stamp head
This writes the alembic_version row without re-executing any DDL.

For fresh deployments, run:
    analytics-cli db upgrade head
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    op.execute("SET search_path = analytics, public")

    op.execute("""
        CREATE UNLOGGED TABLE IF NOT EXISTS analytics.opentelemetry_buffer (
            timestamp                   timestamptz,
            span_id                     text,
            trace_id                    text,
            message                     text,
            attributes                  jsonb,
            resources                   jsonb,
            scope                       jsonb,
            source_type                 text,
            severity_text               text,
            severity_number             integer,
            observed_timestamp          timestamptz,
            flags                       integer,
            dropped_attributes_count    integer
        )
    """)
    op.execute(
        "COMMENT ON TABLE analytics.opentelemetry_buffer IS "
        "'Opentelemetry buffer table. Receives incoming opentelemetry logs data, "
        "for further processing and proper storage. Only contains transient data.'"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS analytics.access_logs (
            oid                  serial,
            id                   text,
            ts                   timestamptz NOT NULL,
            message              text        NOT NULL,
            app_id               text        NOT NULL,
            app_path             text        NOT NULL,
            app_name             text        NOT NULL,
            ip                   text,
            user_id              text,
            user_name            text,
            org_id               text,
            org_name             text,
            roles                text[],
            auth_method          text,
            request_method       text,
            request_path         text,
            request_query_string text,
            request_details      jsonb,
            response_time        integer,
            response_size        integer,
            status_code          integer,
            client_ip            text,
            server_address       text,
            context_data         jsonb,
            PRIMARY KEY (ts, oid)
        )
    """)
    op.execute(
        "COMMENT ON TABLE analytics.access_logs IS "
        "'Storage (hyper)table for the access logs processed data. "
        "This is a timescaledb-enabled table.'"
    )

    # TimescaleDB: promote to hypertable.
    # If this fails with "cannot run inside a transaction block", wrap with:
    #   op.execute("COMMIT") ... op.execute("BEGIN")
    # That is rarely needed for TimescaleDB 2.x.
    op.execute(
        "SELECT create_hypertable('analytics.access_logs', by_range('ts', INTERVAL '7 days'))"
    )

    op.execute("""
        CREATE UNIQUE INDEX idx_id_timestamp
          ON analytics.access_logs(ts, id)
    """)

    op.execute(
        "SELECT add_retention_policy('analytics.access_logs', "
        "drop_after => INTERVAL '3 years', schedule_interval => INTERVAL '1 week')"
    )

    op.execute("""
        ALTER TABLE analytics.access_logs SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'id'
        )
    """)
    op.execute(
        "SELECT add_compression_policy('analytics.access_logs', compress_after => INTERVAL '1 day')"
    )

    # OGC continuous aggregates (from 101_analytics_ogc_views.sql)
    op.execute("""
        CREATE MATERIALIZED VIEW analytics.ogc_summary_hourly
        WITH (timescaledb.continuous) AS
        SELECT time_bucket(INTERVAL '1 h', ts, 'Europe/Paris') AS bucket_hourly,
            app_id,
            app_name,
            user_name,
            org_name,
            request_method,
            status_code,
            server_address,
            request_details ->> 'workspaces' AS workspaces,
            request_details ->> 'layers' AS layers,
            request_details ->> 'service'            AS service,
            request_details ->> 'request'            AS request,
            request_details ->> 'tiled'              AS tiled,
            request_details ->> 'is_download'       AS is_download,
            request_details ->> 'download_format'   AS download_format,
            request_details ->> 'user_agent_family' AS user_agent_family,
            request_details ->> 'referrer' AS referrer,
            count(id)                               AS nb_req,
            percentile_cont(0.5) WITHIN GROUP (
                ORDER BY
                    response_time::DOUBLE PRECISION
            ) AS response_time_median,
            min(response_time::DOUBLE PRECISION) AS response_time_min,
            max(response_time::DOUBLE PRECISION) AS response_time_max
        FROM analytics.access_logs
        WHERE request_details ->'tags' @> '["ogc"]'
        GROUP BY bucket_hourly, app_id, app_name, user_name, org_name, request_method, status_code, server_address,
            request_details ->> 'workspaces', request_details ->> 'layers', request_details ->> 'service',
            request_details ->> 'request' , request_details ->> 'tiled', request_details ->> 'is_download',
            request_details ->> 'download_format', request_details ->> 'user_agent_family', request_details ->> 'referrer'
    """)

    op.execute(
        "SELECT add_retention_policy('analytics.ogc_summary_hourly', "
        "drop_after => INTERVAL '3 weeks', schedule_interval => INTERVAL '1 day')"
    )
    op.execute("""
        SELECT add_continuous_aggregate_policy('analytics.ogc_summary_hourly',
          initial_start => '2025-11-11 00:05:05',
          start_offset => INTERVAL '7 days',
          end_offset => INTERVAL '0 hours',
          schedule_interval => INTERVAL '1 hour')
    """)

    op.execute("""
        CREATE MATERIALIZED VIEW analytics.ogc_summary_daily
        WITH (timescaledb.continuous) AS
        SELECT  time_bucket(INTERVAL '1 d', bucket_hourly, 'Europe/Paris') AS bucket_daily,
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
            referrer,
            SUM(nb_req)                       AS nb_req,
            percentile_cont(0.5) WITHIN GROUP (
                ORDER BY
                    response_time_median
            ) AS response_time_median,
            min(response_time_min) AS response_time_min,
            max(response_time_max) AS response_time_max
        FROM analytics.ogc_summary_hourly
        GROUP BY bucket_daily, app_id, app_name, user_name, org_name, request_method, status_code, server_address, workspaces,
             layers, service, request, tiled, is_download, download_format, user_agent_family, referrer
    """)

    op.execute(
        "SELECT add_retention_policy('analytics.ogc_summary_daily', "
        "drop_after => INTERVAL '2 years', schedule_interval => INTERVAL '1 week')"
    )
    op.execute("""
        SELECT add_continuous_aggregate_policy('analytics.ogc_summary_daily',
          initial_start => '2025-11-11 00:00:05',
          start_offset => INTERVAL '3 weeks',
          end_offset => INTERVAL '0 hours',
          schedule_interval => INTERVAL '1 d')
    """)

    op.execute("""
        CREATE MATERIALIZED VIEW analytics.ogc_summary_monthly
        WITH (timescaledb.continuous) AS
        SELECT  time_bucket(INTERVAL '1 month', bucket_daily, 'Europe/Paris') AS bucket_monthly,
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
            referrer,
            SUM(nb_req)                      AS nb_req,
            percentile_cont(0.5) WITHIN GROUP (
                ORDER BY
                    response_time_median
            ) AS response_time_median,
            min(response_time_min) AS response_time_min,
            max(response_time_max) AS response_time_max
        FROM analytics.ogc_summary_daily
        GROUP BY bucket_monthly, app_id, app_name, user_name, org_name, request_method, status_code, server_address, workspaces,
             layers, service, request, tiled, is_download, download_format, user_agent_family, referrer
    """)

    op.execute("""
        SELECT add_continuous_aggregate_policy('analytics.ogc_summary_monthly',
          initial_start => '2025-11-11 00:00:05',
          start_offset => INTERVAL '6 months',
          end_offset => INTERVAL '0 hours',
          schedule_interval => INTERVAL '1 month')
    """)

    op.execute("CALL refresh_continuous_aggregate('analytics.ogc_summary_hourly', '2021-05-01', '2026-05-14')")
    op.execute("CALL refresh_continuous_aggregate('analytics.ogc_summary_daily', '2021-05-01', '2026-05-14')")
    op.execute("CALL refresh_continuous_aggregate('analytics.ogc_summary_monthly', '2021-05-01', '2026-05-14')")

    op.execute("""
        CREATE VIEW analytics.ogc_summary AS
            SELECT 'hour' as period,
                   bucket_hourly as bucket,
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
                    referrer,
                    nb_req,
                    response_time_median,
                    response_time_min,
                    response_time_max
                FROM analytics.ogc_summary_hourly
            UNION
            SELECT 'day' as period,
                   bucket_daily as bucket,
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
                    referrer,
                    nb_req,
                    response_time_median,
                    response_time_min,
                    response_time_max
                FROM analytics.ogc_summary_daily
            UNION
            SELECT 'month' as period,
                   bucket_monthly as bucket,
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
                    referrer,
                    nb_req,
                    response_time_median,
                    response_time_min,
                    response_time_max
                 FROM analytics.ogc_summary_monthly
    """)

    # DataAPI continuous aggregates (from 102_analytics_datapi_views.sql)
    op.execute("""
        CREATE MATERIALIZED VIEW analytics.dataapi_summary_hourly
        WITH (timescaledb.continuous) AS
        SELECT time_bucket(INTERVAL '1 h', ts, 'Europe/Paris') AS bucket_hourly,
            user_name,
            org_name,
            request_method,
            status_code,
            request_details ->> 'layers' AS layers,
            request_details ->> 'request'            AS request,
            request_details ->> 'is_download'       AS is_download,
            request_details ->> 'download_format'   AS download_format,
            request_details ->> 'full_download'     AS full_download,
            request_details ->> 'user_agent_family' AS user_agent_family,
            count(id)                               AS nb_req,
            AVG(response_time)                      AS avg_time,
            percentile_agg(response_time::DOUBLE PRECISION) AS percentile_hourly
        FROM analytics.access_logs
        WHERE app_name = 'dataapi'
        GROUP BY bucket_hourly, user_name, org_name, request_method, status_code, request_details ->> 'layers',
            request_details ->> 'request' , request_details ->> 'is_download', request_details ->> 'download_format',
            request_details ->> 'full_download', request_details ->> 'user_agent_family'
    """)

    op.execute(
        "SELECT add_retention_policy('analytics.dataapi_summary_hourly', "
        "drop_after => INTERVAL '3 weeks', schedule_interval => INTERVAL '1 day')"
    )
    op.execute("""
        SELECT add_continuous_aggregate_policy('analytics.dataapi_summary_hourly',
          initial_start => '2025-11-11 00:00:05',
          start_offset => INTERVAL '7 days',
          end_offset => INTERVAL '0 hours',
          schedule_interval => INTERVAL '1 hour')
    """)
    op.execute(
        "ALTER MATERIALIZED VIEW analytics.dataapi_summary_hourly set (timescaledb.compress = true)"
    )
    op.execute(
        "SELECT add_compression_policy('analytics.dataapi_summary_hourly', compress_after=>'4 days'::interval)"
    )

    op.execute("""
        CREATE MATERIALIZED VIEW analytics.dataapi_summary_daily
        WITH (timescaledb.continuous) AS
        SELECT  time_bucket(INTERVAL '1 d', bucket_hourly, 'Europe/Paris') AS bucket_daily,
                user_name,
                org_name,
                request_method,
                status_code,
                layers,
                request,
                is_download,
                download_format,
                full_download,
                user_agent_family,
                SUM(nb_req)                               AS nb_req,
                mean(rollup(percentile_hourly))   AS avg_time,
                rollup(percentile_hourly) as percentile_daily
        FROM analytics.dataapi_summary_hourly
        GROUP BY bucket_daily, user_name, org_name, request_method, status_code, layers, request, is_download,
                 download_format, full_download, user_agent_family
    """)

    op.execute(
        "SELECT add_retention_policy('analytics.dataapi_summary_daily', "
        "drop_after => INTERVAL '2 years', schedule_interval => INTERVAL '1 week')"
    )
    op.execute("""
        SELECT add_continuous_aggregate_policy('analytics.dataapi_summary_daily',
          initial_start => '2025-11-11 00:00:05',
          start_offset => INTERVAL '3 weeks',
          end_offset => INTERVAL '0 hours',
          schedule_interval => INTERVAL '1 d')
    """)
    op.execute(
        "ALTER MATERIALIZED VIEW analytics.dataapi_summary_daily set (timescaledb.compress = true)"
    )
    op.execute(
        "SELECT add_compression_policy('analytics.dataapi_summary_daily', compress_after=>'4 weeks'::interval)"
    )

    op.execute("""
        CREATE MATERIALIZED VIEW analytics.dataapi_summary_monthly
        WITH (timescaledb.continuous) AS
        SELECT  time_bucket(INTERVAL '1 month', bucket_daily, 'Europe/Paris') AS bucket_monthly,
                user_name,
                org_name,
                request_method,
                status_code,
                layers,
                request,
                is_download,
                download_format,
                full_download,
                user_agent_family,
                SUM(nb_req)                               AS nb_req,
                mean(rollup(percentile_daily))   AS avg_time,
                rollup(percentile_daily) as percentile_monthly
        FROM analytics.dataapi_summary_daily
        GROUP BY bucket_monthly, user_name, org_name, request_method, status_code, layers, request, is_download,
                 download_format, full_download, user_agent_family
    """)

    op.execute("""
        SELECT add_continuous_aggregate_policy('analytics.dataapi_summary_monthly',
          initial_start => '2025-11-11 00:00:05',
          start_offset => INTERVAL '6 months',
          end_offset => INTERVAL '0 hours',
          schedule_interval => INTERVAL '1 month')
    """)
    op.execute(
        "ALTER MATERIALIZED VIEW analytics.dataapi_summary_monthly set (timescaledb.compress = true)"
    )
    op.execute(
        "SELECT add_compression_policy('analytics.dataapi_summary_monthly', compress_after=>'7 months'::interval)"
    )

    op.execute("CALL refresh_continuous_aggregate('analytics.dataapi_summary_hourly', '2021-05-01', '2025-05-14')")
    op.execute("CALL refresh_continuous_aggregate('analytics.dataapi_summary_daily', '2021-05-01', '2025-05-14')")
    op.execute("CALL refresh_continuous_aggregate('analytics.dataapi_summary_monthly', '2021-05-01', '2025-05-14')")


def downgrade() -> None:
    # Drop in reverse dependency order
    op.execute("DROP VIEW IF EXISTS analytics.ogc_summary")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.dataapi_summary_monthly CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.dataapi_summary_daily CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.dataapi_summary_hourly CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.ogc_summary_monthly CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.ogc_summary_daily CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.ogc_summary_hourly CASCADE")
    op.execute("DROP TABLE IF EXISTS analytics.access_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS analytics.opentelemetry_buffer")
    op.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
