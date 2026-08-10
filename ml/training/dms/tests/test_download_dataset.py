import json

from fleetiq_training_dms.download_dataset import (
    archive_info,
    extract_urls,
    read_manifest,
    write_json_manifest,
)


def test_extract_urls_and_classify_archive() -> None:
    text = (
        "README https://example.test/readme.md\n"
        "https://datasets.vicomtech.org/x/dmd-dataset-drowsiness-gA-1.tar.gz?sig=1"
    )
    urls = extract_urls(text)
    assert archive_info(urls[1])[0] == "drowsiness"
    assert len(urls) == 2


def test_text_manifest_ignores_readme_and_writes_grouped_json(tmp_path) -> None:
    source = tmp_path / "links.txt"
    source.write_text(
        "https://example.test/README.md\n"
        "https://example.test/dmd-dataset-distraction-gA-1.tar.gz?sig=1\n",
        encoding="utf-8",
    )
    destination = tmp_path / "links.json"
    write_json_manifest(source, destination)
    assert read_manifest(destination) == [
        "https://example.test/dmd-dataset-distraction-gA-1.tar.gz?sig=1"
    ]
    assert json.loads(destination.read_text()) == {
        "drowsiness": [],
        "distraction": [
            "https://example.test/dmd-dataset-distraction-gA-1.tar.gz?sig=1"
        ],
    }
