from unittest.mock import MagicMock, Mock

from alembic.config import Config as AlembicConfig
from click.testing import CliRunner

from georchestra_analytics_cli import __main__ as main
from georchestra_analytics_cli.legacy_ogc import (
    GrainValidation,
    LegacyValidation,
)
from georchestra_analytics_cli.timescaledb import PolicySyncResult


class _Config:
    def get_logging_config_as_dict(self):
        return None

    def get_db_connection_string(self):
        return "postgresql://test"


def _runner(monkeypatch):
    config = _Config()
    alembic_config = object()
    monkeypatch.setattr(main, "load_config_from", Mock(return_value=config))
    monkeypatch.setattr(main, "_get_alembic_config", Mock(return_value=alembic_config))
    return CliRunner(), alembic_config


def test_alembic_config_receives_loaded_cli_config(monkeypatch):
    config = _Config()
    monkeypatch.setattr(main, "conf", config)

    alembic_config = main._get_alembic_config()

    assert isinstance(alembic_config, AlembicConfig)
    assert alembic_config.attributes["app_config"] is config


def test_db_upgrade_defaults_to_head(monkeypatch):
    runner, config = _runner(monkeypatch)
    upgrade = Mock()
    monkeypatch.setattr(main.alembic_command, "upgrade", upgrade)

    result = runner.invoke(main.cli, ["db", "upgrade"])

    assert result.exit_code == 0, result.output
    upgrade.assert_called_once_with(config, "head")


def test_db_upgrade_accepts_explicit_revision(monkeypatch):
    runner, config = _runner(monkeypatch)
    upgrade = Mock()
    monkeypatch.setattr(main.alembic_command, "upgrade", upgrade)

    result = runner.invoke(main.cli, ["db", "upgrade", "--revision", "0001"])

    assert result.exit_code == 0, result.output
    upgrade.assert_called_once_with(config, "0001")


def test_db_stamp_defaults_to_baseline(monkeypatch):
    runner, config = _runner(monkeypatch)
    stamp = Mock()
    monkeypatch.setattr(main.alembic_command, "stamp", stamp)

    result = runner.invoke(main.cli, ["db", "stamp"])

    assert result.exit_code == 0, result.output
    stamp.assert_called_once_with(config, "0001")


def test_db_stamp_accepts_explicit_revision(monkeypatch):
    runner, config = _runner(monkeypatch)
    stamp = Mock()
    monkeypatch.setattr(main.alembic_command, "stamp", stamp)

    result = runner.invoke(main.cli, ["db", "stamp", "--revision", "base"])

    assert result.exit_code == 0, result.output
    stamp.assert_called_once_with(config, "base")


def test_db_bootstrap_existing_skips_an_already_versioned_database(monkeypatch):
    runner, _ = _runner(monkeypatch)
    connection = Mock()
    connection.scalar.return_value = "analytics.alembic_version"
    connection.execute.return_value.scalars.return_value.all.return_value = ["0002"]
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(main.sa, "create_engine", Mock(return_value=engine))
    stamp = Mock()
    monkeypatch.setattr(main.alembic_command, "stamp", stamp)

    result = runner.invoke(main.cli, ["db", "bootstrap-existing"])

    assert result.exit_code == 0, result.output
    assert "baseline stamp skipped: 0002" in result.output
    stamp.assert_not_called()
    engine.dispose.assert_called_once()


def test_db_bootstrap_existing_validates_and_stamps_unversioned_database(monkeypatch):
    runner, config = _runner(monkeypatch)
    connection = Mock()
    connection.scalar.side_effect = [None] + [relation for relation in range(6)]
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(main.sa, "create_engine", Mock(return_value=engine))
    stamp = Mock()
    monkeypatch.setattr(main.alembic_command, "stamp", stamp)

    result = runner.invoke(
        main.cli, ["db", "bootstrap-existing", "--revision", "0001"]
    )

    assert result.exit_code == 0, result.output
    stamp.assert_called_once_with(config, "0001")


def test_db_bootstrap_existing_refuses_an_incomplete_schema(monkeypatch):
    runner, _ = _runner(monkeypatch)
    connection = Mock()
    connection.scalar.side_effect = [None, None, 1, 1, 1, 1, 1]
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(main.sa, "create_engine", Mock(return_value=engine))
    stamp = Mock()
    monkeypatch.setattr(main.alembic_command, "stamp", stamp)

    result = runner.invoke(main.cli, ["db", "bootstrap-existing"])

    assert result.exit_code == 1
    assert "missing relations: analytics.opentelemetry_buffer" in result.output
    stamp.assert_not_called()


def test_db_check_baseline_is_read_only(monkeypatch):
    runner, _ = _runner(monkeypatch)
    connection = Mock()
    connection.scalar.side_effect = [None] + [relation for relation in range(6)]
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(main.sa, "create_engine", Mock(return_value=engine))
    stamp = Mock()
    monkeypatch.setattr(main.alembic_command, "stamp", stamp)

    result = runner.invoke(main.cli, ["db", "check-baseline"])

    assert result.exit_code == 0, result.output
    assert "matches baseline revision 0001" in result.output
    stamp.assert_not_called()


def test_db_current(monkeypatch):
    runner, config = _runner(monkeypatch)
    current = Mock()
    monkeypatch.setattr(main.alembic_command, "current", current)

    result = runner.invoke(main.cli, ["db", "current"])

    assert result.exit_code == 0, result.output
    current.assert_called_once_with(config, verbose=True)


def test_db_require_revision_accepts_expected_revision(monkeypatch):
    runner, _ = _runner(monkeypatch)
    monkeypatch.setattr(
        main, "_database_revision_status", Mock(return_value=(("0003",), ("0003",)))
    )

    result = runner.invoke(main.cli, ["db", "require-revision"])

    assert result.exit_code == 0, result.output
    assert "Database revision ready: 0003" in result.output


def test_db_require_revision_rejects_pending_migration(monkeypatch):
    runner, _ = _runner(monkeypatch)
    monkeypatch.setattr(
        main, "_database_revision_status", Mock(return_value=(("0002",), ("0003",)))
    )

    result = runner.invoke(main.cli, ["db", "require-revision"])

    assert result.exit_code == 1
    assert "database revision mismatch" in result.output


def test_db_downgrade_defaults_to_previous_revision(monkeypatch):
    runner, config = _runner(monkeypatch)
    downgrade = Mock()
    monkeypatch.setattr(main.alembic_command, "downgrade", downgrade)

    result = runner.invoke(main.cli, ["db", "downgrade"])

    assert result.exit_code == 0, result.output
    downgrade.assert_called_once_with(config, "-1")


def test_db_sync_policies(monkeypatch):
    runner, _ = _runner(monkeypatch)
    sync = Mock(
        return_value=PolicySyncResult(
            chunk_interval="7 days", retention_action="unchanged"
        )
    )
    monkeypatch.setattr(main, "sync_timescaledb_policies", sync)

    result = runner.invoke(main.cli, ["db", "sync-policies"])

    assert result.exit_code == 0, result.output
    sync.assert_called_once_with(main.conf)
    assert "chunk_interval=7 days, retention=unchanged" in result.output


def test_aggregate_ogc_drains_queue(monkeypatch):
    runner, _ = _runner(monkeypatch)
    drain = Mock(return_value=4)
    monkeypatch.setattr(main, "_drain_ogc_queue", drain)

    result = runner.invoke(main.cli, ["aggregate-ogc", "--batch-size", "2"])

    assert result.exit_code == 0, result.output
    drain.assert_called_once_with(batch_size=2)
    assert "processed_buckets=4" in result.output


def test_legacy_ogc_validate(monkeypatch):
    runner, _ = _runner(monkeypatch)
    validation = LegacyValidation(
        queue_size=0,
        grains=(
            GrainValidation("hourly", 2, 3, 4, 5, 0, 1),
            GrainValidation("daily", 1, 1, 4, 4, 0, 0),
            GrainValidation("monthly", 1, 1, 4, 4, 0, 0),
        ),
    )
    validate = Mock(return_value=validation)
    monkeypatch.setattr(main, "validate_legacy_ogc", validate)

    result = runner.invoke(main.cli, ["legacy-ogc", "validate"])

    assert result.exit_code == 0, result.output
    validate.assert_called_once_with(main.conf)
    assert "store_only_or_different=1" in result.output


def test_legacy_ogc_validate_fails_when_queue_is_not_empty(monkeypatch):
    runner, _ = _runner(monkeypatch)
    validation = LegacyValidation(queue_size=1, grains=())
    monkeypatch.setattr(main, "validate_legacy_ogc", Mock(return_value=validation))

    result = runner.invoke(main.cli, ["legacy-ogc", "validate"])

    assert result.exit_code == 1
    assert "not safe for cutover" in result.output


def test_legacy_ogc_lifecycle_commands(monkeypatch):
    runner, _ = _runner(monkeypatch)
    disable = Mock(return_value=5)
    enable = Mock(return_value=5)
    drop = Mock(return_value=3)
    monkeypatch.setattr(main, "disable_legacy_ogc", disable)
    monkeypatch.setattr(main, "enable_legacy_ogc", enable)
    monkeypatch.setattr(main, "drop_legacy_ogc", drop)

    disabled = runner.invoke(main.cli, ["legacy-ogc", "disable"])
    enabled = runner.invoke(main.cli, ["legacy-ogc", "enable"])
    dropped = runner.invoke(
        main.cli,
        [
            "legacy-ogc",
            "drop",
            "--confirm",
            "DROP_LEGACY_OGC_AGGREGATES",
        ],
    )

    assert disabled.exit_code == enabled.exit_code == dropped.exit_code == 0
    disable.assert_called_once_with(main.conf)
    enable.assert_called_once_with(main.conf)
    drop.assert_called_once_with(main.conf, "DROP_LEGACY_OGC_AGGREGATES")
