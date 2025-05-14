from datetime import datetime, timezone, tzinfo

from georchestra_analytics_cli.access_logs.log_parsers.FakeLogGenerator import FakeLogGenerator
from georchestra_analytics_cli.config import Config


def test_fake_log_generator():
    fg = FakeLogGenerator(Config())
    dt = datetime(2025, 5, 12, 15, 17, tzinfo=timezone.utc)
    record = fg.parse(dt)
    assert record is not None
    assert datetime.fromisoformat(record["ts"]) == dt
    assert record["context_data"]["source_type"] == "fake_log_file"
    assert record["user_id"] in ["testadmin", "testuser", "testuser2", "testeditor", ]
    assert record["status_code"] in [200, 404, 501]
