from datetime import datetime, time, timezone

import click
import pytest

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
