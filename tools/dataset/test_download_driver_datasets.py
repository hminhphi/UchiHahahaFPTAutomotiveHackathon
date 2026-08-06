import pytest

from tools.dataset.download_driver_datasets import parse_dataset_urls


def test_parses_dataset_keyed_urls():
    assert parse_dataset_urls(["yawdd=https://example.test/yawdd.zip"]) == {
        "yawdd": "https://example.test/yawdd.zip"
    }


def test_rejects_unknown_dataset_key():
    with pytest.raises(ValueError, match="Unknown dataset"):
        parse_dataset_urls(["unknown=https://example.test/archive.zip"])
