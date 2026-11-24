import pytest

from georchestra_analytics_cli.legacy_ogc import (
    GrainValidation,
    LegacyValidation,
    drop_legacy_ogc,
)


def test_validation_allows_store_only_preserved_history():
    result = LegacyValidation(
        queue_size=0,
        grains=(GrainValidation("monthly", 3, 4, 5, 6, 0, 1),),
    )

    assert result.safe


def test_validation_rejects_missing_legacy_rows_and_pending_queue():
    difference = LegacyValidation(
        queue_size=0,
        grains=(GrainValidation("hourly", 2, 2, 2, 2, 1, 1),),
    )
    queued = LegacyValidation(queue_size=1, grains=())

    assert not difference.safe
    assert not queued.safe


def test_drop_requires_exact_confirmation_before_connecting():
    with pytest.raises(ValueError, match="DROP_LEGACY_OGC_AGGREGATES"):
        drop_legacy_ogc(object(), "wrong")
