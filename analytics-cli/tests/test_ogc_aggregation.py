from contextlib import nullcontext
from datetime import datetime, timezone
from unittest.mock import Mock

from georchestra_analytics_cli import ogc_aggregation


class _Config:
    def get_db_connection_string(self):
        return "postgresql://unused"

    def get_ogc_aggregation_batch_size(self):
        return 100

    def get_timezone(self):
        return "America/Argentina/Buenos_Aires"


def test_enqueue_ogc_buckets_uses_only_ogc_records():
    session = Mock()
    ogc_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    ogc_aggregation.enqueue_ogc_buckets(
        session,
        [
            {"ts": ogc_ts, "request_details": {"tags": ["ogc"]}},
            {
                "ts": datetime(2026, 1, 2, tzinfo=timezone.utc),
                "request_details": {"tags": ["other"]},
            },
        ],
        "America/Argentina/Buenos_Aires",
    )

    assert session.execute.call_count == 1
    assert session.execute.call_args.args[1] == {
        "timestamps": [ogc_ts],
        "timezone": "America/Argentina/Buenos_Aires",
    }
    assert "ON CONFLICT" in str(session.execute.call_args.args[0])


def test_enqueue_ogc_buckets_skips_non_ogc_records():
    session = Mock()

    ogc_aggregation.enqueue_ogc_buckets(
        session,
        [{"ts": datetime.now(timezone.utc), "request_details": None}],
        "UTC",
    )

    session.execute.assert_not_called()


def test_aggregate_empty_queue(monkeypatch):
    connection = Mock()
    empty_result = Mock()
    empty_result.scalars.return_value = []
    connection.execute.side_effect = [Mock(), empty_result]
    engine = Mock()
    engine.begin.return_value = nullcontext(connection)
    monkeypatch.setattr(ogc_aggregation, "create_engine", Mock(return_value=engine))

    result = ogc_aggregation.aggregate_queued_ogc_buckets(_Config())

    assert result == ogc_aggregation.AggregationResult(processed_buckets=0)


def test_aggregate_recomputes_all_grains(monkeypatch):
    bucket = datetime(2026, 1, 1, tzinfo=timezone.utc)
    daily_bucket = datetime(2025, 12, 31, 23, tzinfo=timezone.utc)
    connection = Mock()
    claimed_result = Mock()
    claimed_result.scalars.return_value = [bucket]
    connection.execute.side_effect = [Mock(), claimed_result, Mock(), Mock()]
    engine = Mock()
    engine.begin.return_value = nullcontext(connection)
    hourly = Mock()
    rollup = Mock(
        side_effect=[[daily_bucket], [datetime(2025, 11, 30, 23, tzinfo=timezone.utc)]]
    )
    monkeypatch.setattr(ogc_aggregation, "create_engine", Mock(return_value=engine))
    monkeypatch.setattr(ogc_aggregation, "_recompute_hourly", hourly)
    monkeypatch.setattr(ogc_aggregation, "_recompute_rollup", rollup)

    result = ogc_aggregation.aggregate_queued_ogc_buckets(_Config(), batch_size=5)

    assert result == ogc_aggregation.AggregationResult(processed_buckets=1)
    hourly.assert_called_once_with(
        connection, [bucket], "America/Argentina/Buenos_Aires"
    )
    assert rollup.call_count == 2
    assert rollup.call_args_list[1].args[-2] == [daily_bucket]
    assert rollup.call_args_list[1].args[-1] == "America/Argentina/Buenos_Aires"
    assert connection.execute.call_args_list[1].args[1] == {"batch_size": 5}
