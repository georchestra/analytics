"""
Canonical OGC view definitions and safe recreation helper.

Use safe_recreate() in any migration that changes the OGC view definitions.
Do NOT import from revision files in versions/ — they are not stable modules.

When to use safe_recreate vs. other approaches:
  - View query changes (new column, different filter, changed bucketing) → safe_recreate()
  - Only policy changes (retention interval, schedule)                  → remove + add policy, no drop
  - New column on access_logs that views don't reference               → nothing, views stay valid
"""

OGC_HOURLY = """
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
"""

OGC_DAILY = """
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
"""

OGC_MONTHLY = """
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
"""

OGC_UNIFIED = """
    CREATE VIEW analytics.ogc_summary AS
        SELECT 'hour' as period,
               bucket_hourly as bucket,
                app_id, app_name, user_name, org_name, request_method, status_code, server_address,
                workspaces, layers, service, request, tiled, is_download, download_format,
                user_agent_family, referrer, nb_req, response_time_median, response_time_min, response_time_max
            FROM analytics.ogc_summary_hourly
        UNION
        SELECT 'day' as period,
               bucket_daily as bucket,
                app_id, app_name, user_name, org_name, request_method, status_code, server_address,
                workspaces, layers, service, request, tiled, is_download, download_format,
                user_agent_family, referrer, nb_req, response_time_median, response_time_min, response_time_max
            FROM analytics.ogc_summary_daily
        UNION
        SELECT 'month' as period,
               bucket_monthly as bucket,
                app_id, app_name, user_name, org_name, request_method, status_code, server_address,
                workspaces, layers, service, request, tiled, is_download, download_format,
                user_agent_family, referrer, nb_req, response_time_median, response_time_min, response_time_max
             FROM analytics.ogc_summary_monthly
"""


def create(op) -> None:
    """Create all OGC views and policies from scratch. Use in initial migrations only."""
    op.execute(OGC_HOURLY)
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

    op.execute(OGC_DAILY)
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

    op.execute(OGC_MONTHLY)
    op.execute("""
        SELECT add_continuous_aggregate_policy('analytics.ogc_summary_monthly',
          initial_start => '2025-11-11 00:00:05',
          start_offset => INTERVAL '6 months',
          end_offset => INTERVAL '0 hours',
          schedule_interval => INTERVAL '1 month')
    """)

    op.execute(OGC_UNIFIED)


def drop(op) -> None:
    """Drop all OGC views. CASCADE handles the hourly→daily→monthly dependency chain."""
    op.execute("DROP VIEW IF EXISTS analytics.ogc_summary")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.ogc_summary_monthly CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.ogc_summary_daily CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.ogc_summary_hourly CASCADE")


def safe_recreate(
    op,
    hourly_sql: str = OGC_HOURLY,
    daily_sql: str = OGC_DAILY,
    monthly_sql: str = OGC_MONTHLY,
    unified_sql: str = OGC_UNIFIED,
) -> None:
    """
    Safely drop, recreate, and refresh OGC views without losing historical data.

    The danger: if retention policies are still active when views are recreated,
    the TimescaleDB background job may prune freshly-refreshed buckets before the
    daily/monthly aggregates can be built from them. The fix is to remove retention
    first, refresh the full hierarchy bottom-up, then restore policies.

    Sequence:
      1. remove retention policies (nothing can be pruned during migration)
      2. drop all views (CASCADE)
      3. recreate with new definitions (no policies yet)
      4. refresh bottom-up: hourly → daily → monthly
      5. restore retention + continuous aggregate policies

    Call with custom SQL strings when the view definition is changing:
        safe_recreate(op, hourly_sql=MY_NEW_OGC_HOURLY, ...)
    Call with defaults to just cycle the views (e.g. after adding a column to access_logs):
        safe_recreate(op)
    """
    # Step 1 — remove retention so nothing is pruned during the migration window
    op.execute("SELECT remove_retention_policy('analytics.ogc_summary_hourly', if_exists => true)")
    op.execute("SELECT remove_retention_policy('analytics.ogc_summary_daily', if_exists => true)")

    # Step 2 — drop everything (CASCADE takes monthly with daily)
    op.execute("DROP VIEW IF EXISTS analytics.ogc_summary")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.ogc_summary_monthly CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.ogc_summary_daily CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS analytics.ogc_summary_hourly CASCADE")

    # Step 3 — recreate with provided (or default) definitions
    op.execute(hourly_sql)
    op.execute(daily_sql)
    op.execute(monthly_sql)
    op.execute(unified_sql)

    # Step 4 — refresh bottom-up while retention is disabled
    op.execute("CALL refresh_continuous_aggregate('analytics.ogc_summary_hourly', '2021-01-01', now()::text)")
    op.execute("CALL refresh_continuous_aggregate('analytics.ogc_summary_daily', '2021-01-01', now()::text)")
    op.execute("CALL refresh_continuous_aggregate('analytics.ogc_summary_monthly', '2021-01-01', now()::text)")

    # Step 5 — restore retention and refresh policies
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
        SELECT add_continuous_aggregate_policy('analytics.ogc_summary_monthly',
          initial_start => '2025-11-11 00:00:05',
          start_offset => INTERVAL '6 months',
          end_offset => INTERVAL '0 hours',
          schedule_interval => INTERVAL '1 month')
    """)
