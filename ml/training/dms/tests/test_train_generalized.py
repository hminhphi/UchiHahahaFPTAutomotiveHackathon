import pytest

from fleetiq_training_dms.train_generalized import parse_args


def test_training_cli_requires_manifest_and_validation_subject(monkeypatch):
    monkeypatch.setattr("sys.argv", ["fleetiq-train-dms-generalized"])
    with pytest.raises(SystemExit):
        parse_args()
