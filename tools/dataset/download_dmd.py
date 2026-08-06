"""Download and safely extract user-authorized DMD archives."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tarfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


def validate_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("DMD downloads require an HTTP(S) URL")
    return url


def safe_member_path(destination: Path, member_name: str) -> Path:
    root = destination.resolve()
    target = (root / member_name).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Archive member would extract outside {root}: {member_name}")
    return target


def _archive_name(url: str) -> str:
    name = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
    if not name.lower().endswith((".zip", ".tar", ".tar.gz", ".tgz")):
        raise ValueError(f"Unsupported DMD archive format: {name or '<missing filename>'}")
    return name


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download(url: str, destination: Path, expected_sha256: str | None = None) -> Path:
    validate_url(url)
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / _archive_name(url)
    partial = output.with_suffix(output.suffix + ".part")
    start = partial.stat().st_size if partial.exists() else 0
    request = urllib.request.Request(url, headers={"Range": f"bytes={start}-"} if start else {})
    with urllib.request.urlopen(request) as response:
        resume = start > 0 and response.status == 206
        if not resume:
            start = 0
        mode = "ab" if resume else "wb"
        with partial.open(mode) as target:
            shutil.copyfileobj(response, target)
    partial.replace(output)
    if expected_sha256 and _digest(output).lower() != expected_sha256.lower():
        output.unlink()
        raise ValueError(f"SHA-256 mismatch for {output}")
    return output


def _extract_zip(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            target = safe_member_path(destination, member.filename)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as source_file, target.open("wb") as target_file:
                shutil.copyfileobj(source_file, target_file)


def _extract_tar(archive: Path, destination: Path) -> None:
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            target = safe_member_path(destination, member.name)
            if member.issym() or member.islnk():
                raise ValueError(f"Refusing archive link: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ValueError(f"Unsupported archive member: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = source.extractfile(member)
            if extracted is None:
                raise ValueError(f"Could not read archive member: {member.name}")
            with extracted, target.open("wb") as target_file:
                shutil.copyfileobj(extracted, target_file)


def extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive):
        _extract_zip(archive, destination)
    elif tarfile.is_tarfile(archive):
        _extract_tar(archive, destination)
    else:
        raise ValueError(f"Unsupported archive: {archive}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download user-authorized DMD archives")
    parser.add_argument("--url", action="append", required=True, help="Official DMD archive URL; repeat for multiple archives")
    parser.add_argument("--sha256", action="append", default=[], help="Optional SHA-256 per URL, in the same order")
    parser.add_argument("--output", type=Path, default=Path("data/DMD"))
    args = parser.parse_args()
    if args.sha256 and len(args.sha256) != len(args.url):
        parser.error("provide one --sha256 value for every --url value")
    for index, url in enumerate(args.url):
        archive = download(url, args.output / "downloads", args.sha256[index] if args.sha256 else None)
        extract(archive, args.output)
        print(f"Downloaded and extracted: {archive} -> {args.output}")


if __name__ == "__main__":
    main()
