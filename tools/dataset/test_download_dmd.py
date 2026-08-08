import pytest

from tools.dataset.download_dmd import safe_member_path, validate_url


def test_rejects_non_http_download_urls():
    with pytest.raises(ValueError, match="HTTP"):
        validate_url("file:///tmp/dmd.zip")


def test_rejects_archive_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        safe_member_path(tmp_path, "../../outside.txt")
