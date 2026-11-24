from datetime import datetime, time, timezone
from unittest.mock import Mock

import click
import pytest

from georchestra_analytics_cli import __main__ as main
from georchestra_analytics_cli.__main__ import (
    _seconds_until_next_cron_run,
)


def test_seconds_until_next_cron_run_same_day():
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    delay = _seconds_until_next_cron_run("5 10 * * *", "UTC", now=now)
    assert delay == 300


def test_seconds_until_next_cron_run_next_day_on_equal_time():
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    delay = _seconds_until_next_cron_run("0 10 * * *", "UTC", now=now)
    assert delay == 24 * 3600


def test_seconds_until_next_cron_run_timezone_conversion():
    now = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
    delay = _seconds_until_next_cron_run("0 10 * * *", "Europe/Paris", now=now)
    assert delay == 3600


def test_seconds_until_next_cron_run_invalid_expression():
    now = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(click.BadParameter):
        _seconds_until_next_cron_run("invalid cron", "UTC", now=now)


class _CronConfig:
    def get_timezone(self):
        return "UTC"

    def is_metrics_enabled(self):
        return False


def test_buffer2db_cron_waits_and_recovers_after_failure(monkeypatch):
    process_buffer = Mock(side_effect=[RuntimeError("temporary failure"), None])
    processor_factory = Mock()
    processor_factory.return_value.process_buffer_table = process_buffer
    sleep = Mock(side_effect=[None, None, KeyboardInterrupt])
    drain = Mock()
    monkeypatch.setattr(main, "conf", _CronConfig())
    monkeypatch.setattr(main, "AccessLogProcessor", processor_factory)
    monkeypatch.setattr(main, "_seconds_until_next_cron_run", lambda *_: 60)
    monkeypatch.setattr(main.time, "sleep", sleep)
    monkeypatch.setattr(main, "_drain_ogc_queue", drain)

    main.buffer2db.callback("*/5 * * * *")

    assert sleep.call_count == 3
    assert process_buffer.call_count == 2
    drain.assert_called_once()


def test_buffer2db_one_shot_still_reports_failure(monkeypatch):
    processor_factory = Mock()
    processor_factory.return_value.process_buffer_table.side_effect = RuntimeError(
        "permanent failure"
    )
    monkeypatch.setattr(main, "conf", _CronConfig())
    monkeypatch.setattr(main, "AccessLogProcessor", processor_factory)

    with pytest.raises(RuntimeError, match="permanent failure"):
        main.buffer2db.callback(None)


def test_drain_ogc_queue_isolates_failed_batch(monkeypatch):
    aggregate = Mock(
        side_effect=[
            main.OgcAggregationBatchError("poison bucket"),
            Mock(processed_buckets=1),
            Mock(processed_buckets=0),
        ]
    )
    monkeypatch.setattr(main, "aggregate_queued_ogc_buckets", aggregate)
    monkeypatch.setattr(main, "conf", _CronConfig())

    assert main._drain_ogc_queue() == 1
    assert [call.kwargs["batch_size"] for call in aggregate.call_args_list] == [
        None,
        1,
        1,
    ]
