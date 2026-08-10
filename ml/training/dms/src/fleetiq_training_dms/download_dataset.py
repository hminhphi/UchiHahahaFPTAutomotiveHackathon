"""Download and extract the Vicomtech DMD DMS datasets."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tarfile
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "dmd"
ARCHIVE_PATTERN = re.compile(
    r"dmd-dataset-(drowsiness|distraction)-[^/]+\.tar(?:\.gz|\.tgz)$",
    re.IGNORECASE,
)
URL_PATTERN = re.compile(r'https?://[^\s<>"\']+')


def extract_urls(text: str) -> list[str]:
    """Extract unique HTTP(S) URLs from pasted email or README text."""
    urls = (match.rstrip(".,;)]}") for match in URL_PATTERN.findall(text))
    return list(dict.fromkeys(urls))


def archive_info(url: str) -> tuple[str, str]:
    """Return dataset group and archive filename for a Vicomtech URL."""
    name = Path(unquote(urlparse(url).path)).name
    match = ARCHIVE_PATTERN.fullmatch(name)
    if not match:
        raise ValueError(
            f"Unsupported archive URL: {url}\n"
            "Expected dmd-dataset-drowsiness-*.tar.gz or "
            "dmd-dataset-distraction-*.tar.gz"
        )
    return match.group(1).lower(), name


def is_archive_url(url: str) -> bool:
    try:
        archive_info(url)
    except ValueError:
        return False
    return True


def read_manifest(path: Path) -> list[str]:
    """Read archive URLs from pasted text or a generated JSON manifest."""
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            values = [url for group in payload.values() for url in group]
        elif isinstance(payload, list):
            values = payload
        else:
            raise ValueError("JSON manifest must be a list or an object of URL lists.")
        if not all(isinstance(url, str) for url in values):
            raise ValueError("JSON manifest URLs must be strings.")
        return values

    return [url for url in extract_urls(path.read_text(encoding="utf-8")) if is_archive_url(url)]


def write_json_manifest(source: Path, destination: Path) -> None:
    """Convert a forwarded Vicomtech text export into a grouped JSON manifest."""
    groups = {"drowsiness": [], "distraction": []}
    for url in read_manifest(source):
        group, _ = archive_info(url)
        groups[group].append(url)
    if not any(groups.values()):
        raise ValueError(f"No Vicomtech archive URLs found in {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(groups, indent=2) + "\n", encoding="utf-8")


def read_urls(manifest: Path | None, urls: list[str]) -> list[str]:
    """Read URLs from a pasted text file and/or repeated --url options."""
    values = list(urls)
    if manifest:
        values.extend(read_manifest(manifest))
    result = list(dict.fromkeys(values))
    if not result:
        raise ValueError("Provide --manifest or at least one --url.")
    for url in result:
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL must use HTTP(S): {url}")
        archive_info(url)
    return result


def download(url: str, destination: Path, force: bool = False) -> None:
    """Download one archive atomically, skipping an existing archive by default."""
    if destination.exists() and not force:
        print(f"[skip] {destination.name}")
        return

    partial = destination.with_suffix(destination.suffix + ".part")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "FleetIQ-DMS-Dataset-Downloader/1.0"})
    print(f"[download] {destination.name}")
    try:
        with urlopen(request, timeout=120) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)


def extract(archive: Path, destination: Path, force: bool = False) -> None:
    """Extract one archive using tarfile's safe data filter."""
    marker = destination / f".{archive.name}.extracted"
    if marker.exists() and not force:
        print(f"[skip] {archive.name} already extracted")
        return

    destination.mkdir(parents=True, exist_ok=True)
    print(f"[extract] {archive.name} -> {destination}")
    with tarfile.open(archive, "r:*") as bundle:
        bundle.extractall(destination, filter="data")
    marker.touch()


def download_and_extract(
    urls: list[str],
    output_root: Path,
    dataset: str = "all",
    force: bool = False,
    delete_archives: bool = False,
) -> None:
    """Download and extract selected Vicomtech archives."""
    for url in urls:
        group, filename = archive_info(url)
        if dataset != "all" and group != dataset:
            continue
        archive = output_root / ".archives" / group / filename
        marker = output_root / group / f".{filename}.extracted"
        if marker.exists() and not force:
            print(f"[skip] {filename} already extracted")
            if delete_archives:
                archive.unlink(missing_ok=True)
            continue
        download(url, archive, force=force)
        extract(archive, output_root / group, force=force)
        if delete_archives:
            archive.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download and extract Vicomtech DMD drowsiness/distraction archives."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Text or JSON file containing the signed archive URLs.",
    )
    parser.add_argument(
        "--convert-to-json",
        action="store_true",
        help="Convert a text manifest beside itself to .json, then download from that JSON.",
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        help="Archive URL; repeat for multiple archives.",
    )
    parser.add_argument(
        "--dataset",
        choices=("all", "drowsiness", "distraction"),
        default="all",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--force", action="store_true", help="Re-download and re-extract.")
    parser.add_argument(
        "--delete-archives",
        action="store_true",
        help="Delete each tar archive after successful extraction to save disk space.",
    )
    args = parser.parse_args(argv)

    try:
        if args.convert_to_json:
            if not args.manifest:
                parser.error("--convert-to-json requires --manifest")
            json_manifest = args.manifest.with_suffix(".json")
            write_json_manifest(args.manifest, json_manifest)
            print(f"[manifest] {json_manifest}")
            args.manifest = json_manifest
        urls = read_urls(args.manifest, args.url)
        download_and_extract(
            urls,
            args.output_root,
            args.dataset,
            args.force,
            args.delete_archives,
        )
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
