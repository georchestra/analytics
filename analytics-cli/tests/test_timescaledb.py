from contextlib import nullcontext
from unittest.mock import Mock

import pytest

from georchestra_analytics_cli import timescaledb


class _Config:
    def get_db_connection_string(self):
        return "postgresql://unused"

    def get_timescaledb_chunk_interval(self):
        return "1 day"

    def get_timescaledb_retention_drop_after(self):
        return "90 days"

    def get_timescaledb_retention_schedule_interval(self):
        return "12 hours"


def _mock_engine(monkeypatch, retention_job):
    connection = Mock()
    query_result = Mock()
    query_result.mappings.return_value.one_or_none.return_value = retention_job
    call_number = 0

    def execute(*args, **kwargs):
        nonlocal call_number
        call_number += 1
        return query_result if call_number == 3 else Mock()

    connection.execute.side_effect = execute
    engine = Mock()
    engine.begin.return_value = nullcontext(connection)
    monkeypatch.setattr(timescaledb, "create_engine", Mock(return_value=engine))
    return connection


@pytest.mark.parametrize(
    ("retention_job", "expected_action", "expected_calls"),
    [
        (None, "created", 4),
        ({"job_id": 1000, "matches": True}, "unchanged", 3),
        ({"job_id": 1000, "matches": False}, "updated", 5),
    ],
)
def test_sync_timescaledb_policies(
    monkeypatch, retention_job, expected_action, expected_calls
):
    connection = _mock_engine(monkeypatch, retention_job)

    result = timescaledb.sync_timescaledb_policies(_Config())

    assert result == timescaledb.PolicySyncResult("1 day", expected_action)
    assert connection.execute.call_count == expected_calls

    statements = [str(call.args[0]) for call in connection.execute.call_args_list]
    assert "pg_advisory_xact_lock" in statements[0]
    assert "set_chunk_time_interval" in statements[1]
    assert connection.execute.call_args_list[1].args[1] == {
        "chunk_interval": "1 day"
    }

    if expected_action == "updated":
        assert "remove_retention_policy" in statements[3]
    if expected_action != "unchanged":
        assert "add_retention_policy" in statements[-1]
        assert connection.execute.call_args_list[-1].args[1] == {
            "drop_after": "90 days",
            "schedule_interval": "12 hours",
        }
