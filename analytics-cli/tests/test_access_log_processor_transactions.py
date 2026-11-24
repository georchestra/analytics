from datetime import datetime, timezone
from unittest.mock import Mock

from georchestra_analytics_cli.access_logs import AccessLogProcessor as processor_module


def _record():
    return {
        "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "id": "record-1",
        "message": "test",
        "app_id": "/geoserver/",
        "app_path": "/geoserver/",
        "app_name": "geoserver",
    }


def test_upsert_and_queue_share_caller_transaction(monkeypatch):
    session = Mock()
    enqueue = Mock()
    monkeypatch.setattr(processor_module, "enqueue_ogc_buckets", enqueue)
    processor = processor_module.AccessLogProcessor.__new__(
        processor_module.AccessLogProcessor
    )
    processor.config = Mock()
    processor.config.get_timezone.return_value = "UTC"
    records = [_record()]

    processor.upsert_log_records(session, records, commit=False)

    session.execute.assert_called_once()
    enqueue.assert_called_once_with(session, records, "UTC")
    session.commit.assert_not_called()


def test_upsert_commits_only_after_queue_succeeds(monkeypatch):
    session = Mock()
    enqueue = Mock(side_effect=RuntimeError("queue unavailable"))
    monkeypatch.setattr(processor_module, "enqueue_ogc_buckets", enqueue)
    processor = processor_module.AccessLogProcessor.__new__(
        processor_module.AccessLogProcessor
    )
    processor.config = Mock()
    processor.config.get_timezone.return_value = "UTC"

    try:
        processor.upsert_log_records(session, [_record()])
    except RuntimeError:
        pass
    else:
        raise AssertionError("queue failure was not propagated")

    session.commit.assert_not_called()
