"""Incremental, durable OGC aggregation for the persistent summary stores."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from georchestra_analytics_cli.config import Config

logger = logging.getLogger(__name__)

DIMENSIONS = """
    app_id, app_name, user_name, org_name, request_method, status_code,
    server_address, workspaces, layers, service, request, tiled, is_download,
    download_format, user_agent_family, referrer
"""


@dataclass(frozen=True)
class AggregationResult:
    processed_buckets: int


def enqueue_ogc_buckets(
    session: Session, records: list[dict], timezone_name: str
) -> None:
    """Queue distinct OGC hourly buckets in the caller's transaction."""
    timestamps = [
        record["ts"]
        for record in records
        if "ogc" in (record.get("request_details") or {}).get("tags", [])
    ]
    if not timestamps:
        return

    session.execute(
        text(
            """
            INSERT INTO analytics.ogc_aggregation_queue (bucket_hourly, queued_at)
            SELECT DISTINCT
                time_bucket(INTERVAL '1 hour', ts, :timezone),
                now()
            FROM unnest(CAST(:timestamps AS timestamptz[])) AS input(ts)
            ON CONFLICT (bucket_hourly) DO UPDATE
                SET queued_at = EXCLUDED.queued_at,
                    last_error = NULL
        """
        ),
        {"timestamps": timestamps, "timezone": timezone_name},
    )


def _recompute_hourly(
    connection: Connection, buckets: list[datetime], timezone_name: str
) -> None:
    connection.execute(
        text(
            """
            DELETE FROM analytics.ogc_summary_hourly_store
            WHERE bucket_hourly = ANY(CAST(:buckets AS timestamptz[]))
        """
        ),
        {"buckets": buckets},
    )
    connection.execute(
        text(
            f"""
            INSERT INTO analytics.ogc_summary_hourly_store (
                bucket_hourly, {DIMENSIONS}, nb_req,
                response_time_median, response_time_min, response_time_max
            )
            SELECT
                time_bucket(INTERVAL '1 hour', ts, :timezone) AS bucket_hourly,
                app_id, app_name, user_name, org_name, request_method, status_code,
                server_address,
                request_details ->> 'workspaces',
                request_details ->> 'layers',
                request_details ->> 'service',
                request_details ->> 'request',
                request_details ->> 'tiled',
                request_details ->> 'is_download',
                request_details ->> 'download_format',
                request_details ->> 'user_agent_family',
                request_details ->> 'referrer',
                count(id),
                percentile_cont(0.5) WITHIN GROUP (
                    ORDER BY response_time::double precision
                ),
                min(response_time::double precision),
                max(response_time::double precision)
            FROM analytics.access_logs
            WHERE ts >= (SELECT min(bucket) FROM unnest(CAST(:buckets AS timestamptz[])) AS q(bucket))
              AND ts < (SELECT max(bucket) + INTERVAL '1 hour' FROM unnest(CAST(:buckets AS timestamptz[])) AS q(bucket))
              AND time_bucket(INTERVAL '1 hour', ts, :timezone) = ANY(CAST(:buckets AS timestamptz[]))
              AND request_details -> 'tags' @> '["ogc"]'
            GROUP BY bucket_hourly, app_id, app_name, user_name, org_name,
                request_method, status_code, server_address,
                request_details ->> 'workspaces', request_details ->> 'layers',
                request_details ->> 'service', request_details ->> 'request',
                request_details ->> 'tiled', request_details ->> 'is_download',
                request_details ->> 'download_format',
                request_details ->> 'user_agent_family', request_details ->> 'referrer'
        """
        ),
        {"buckets": buckets, "timezone": timezone_name},
    )


def _recompute_rollup(
    connection: Connection,
    source_table: str,
    target_table: str,
    source_bucket: str,
    target_bucket: str,
    interval: str,
    buckets: list[datetime],
    timezone_name: str,
) -> list[datetime]:
    affected = list(
        connection.execute(
            text(
                f"""
                SELECT DISTINCT time_bucket(
                    INTERVAL '{interval}', bucket, :timezone
                ) AS bucket
                FROM unnest(CAST(:buckets AS timestamptz[])) AS input(bucket)
                ORDER BY bucket
            """
            ),
            {"buckets": buckets, "timezone": timezone_name},
        ).scalars()
    )
    connection.execute(
        text(
            f"""
            DELETE FROM analytics.{target_table}
            WHERE {target_bucket} = ANY(CAST(:buckets AS timestamptz[]))
        """
        ),
        {"buckets": affected},
    )
    connection.execute(
        text(
            f"""
            INSERT INTO analytics.{target_table} (
                {target_bucket}, {DIMENSIONS}, nb_req,
                response_time_median, response_time_min, response_time_max
            )
            SELECT
                time_bucket(INTERVAL '{interval}', {source_bucket}, :timezone) AS {target_bucket},
                {DIMENSIONS},
                sum(nb_req),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY response_time_median),
                min(response_time_min),
                max(response_time_max)
            FROM analytics.{source_table}
            WHERE time_bucket(INTERVAL '{interval}', {source_bucket}, :timezone) = ANY(CAST(:buckets AS timestamptz[]))
            GROUP BY {target_bucket}, {DIMENSIONS}
        """
        ),
        {"buckets": affected, "timezone": timezone_name},
    )
    return affected


def _record_failure(engine, buckets: list[datetime], error: Exception) -> None:
    message = str(error)[:4000]
    with engine.begin() as connection:
        if buckets:
            connection.execute(
                text(
                    """
                    UPDATE analytics.ogc_aggregation_queue
                    SET attempts = attempts + 1, last_error = :error
                    WHERE bucket_hourly = ANY(CAST(:buckets AS timestamptz[]))
                """
                ),
                {"buckets": buckets, "error": message},
            )
        connection.execute(
            text(
                """
                UPDATE analytics.ogc_aggregation_state
                SET last_error_at = now(), last_error = :error
                WHERE singleton
            """
            ),
            {"error": message},
        )


def aggregate_queued_ogc_buckets(
    config: Config, batch_size: int | None = None
) -> AggregationResult:
    """Recompute one bounded queue batch atomically and idempotently."""
    size = (
        batch_size
        if batch_size is not None
        else config.get_ogc_aggregation_batch_size()
    )
    if size <= 0:
        raise ValueError("OGC aggregation batch size must be greater than zero")

    engine = create_engine(config.get_db_connection_string())
    timezone_name = config.get_timezone()
    claimed: list[datetime] = []
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "SELECT pg_advisory_xact_lock(hashtext('georchestra.analytics.ogc_aggregation'))"
                )
            )
            claimed = list(
                connection.execute(
                    text(
                        """
                        SELECT bucket_hourly
                        FROM analytics.ogc_aggregation_queue
                        ORDER BY bucket_hourly
                        FOR UPDATE SKIP LOCKED
                        LIMIT :batch_size
                    """
                    ),
                    {"batch_size": size},
                ).scalars()
            )
            if not claimed:
                return AggregationResult(processed_buckets=0)

            _recompute_hourly(connection, claimed, timezone_name)
            daily = _recompute_rollup(
                connection,
                "ogc_summary_hourly_store",
                "ogc_summary_daily_store",
                "bucket_hourly",
                "bucket_daily",
                "1 day",
                claimed,
                timezone_name,
            )
            _recompute_rollup(
                connection,
                "ogc_summary_daily_store",
                "ogc_summary_monthly_store",
                "bucket_daily",
                "bucket_monthly",
                "1 month",
                daily,
                timezone_name,
            )
            connection.execute(
                text(
                    """
                    DELETE FROM analytics.ogc_aggregation_queue
                    WHERE bucket_hourly = ANY(CAST(:buckets AS timestamptz[]))
                """
                ),
                {"buckets": claimed},
            )
            connection.execute(
                text(
                    """
                    UPDATE analytics.ogc_aggregation_state
                    SET last_success_at = now(), last_error_at = NULL, last_error = NULL
                    WHERE singleton
                """
                ),
            )
    except Exception as error:
        logger.exception("OGC aggregation failed")
        try:
            _record_failure(engine, claimed, error)
        except Exception:
            logger.exception("Could not record OGC aggregation failure metadata")
        raise
    finally:
        engine.dispose()

    return AggregationResult(processed_buckets=len(claimed))
