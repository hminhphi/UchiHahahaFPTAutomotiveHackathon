"""Download user-authorized external driver-behavior datasets."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.dataset.download_dmd import download, extract


DATASETS = {
    "dmd": ("https://dmd.vicomtech.org/", "Accept academic/non-commercial terms, then copy a direct RGB archive URL."),
    "uta-rldd": ("https://sites.google.com/view/utarldd/home", "Use the official Google Drive folder to obtain a direct archive URL."),
    "yawdd": ("https://doi.org/10.21227/e1qm-hb90", "Sign in to IEEE DataPort and copy the authorized archive URL."),
    "nthu-ddd": ("https://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/", "Request access under the NTHU dataset license agreement."),
    "auc": ("https://heshameraqi.github.io/distraction_detection", "Accept the AUC dataset license and copy the authorized archive URL."),
}


def parse_dataset_urls(values: list[str]) -> dict[str, str]:
    urls = {}
    for value in values:
        key, separator, url = value.partition("=")
        if not separator or not url:
            raise ValueError("URLs must use dataset=https://official-archive form")
        if key not in DATASETS:
            raise ValueError(f"Unknown dataset: {key}")
        urls[key] = url
    return urls


def print_catalog() -> None:
    for key, (landing_page, access_note) in DATASETS.items():
        print(f"{key}: {landing_page}\n  {access_note}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download user-authorized driver-behavior dataset archives")
    parser.add_argument("--list", action="store_true", help="Show supported datasets and official access pages")
    parser.add_argument("--dataset", choices=("all", *DATASETS), default="all")
    parser.add_argument("--url", action="append", default=[], metavar="DATASET=URL")
    parser.add_argument("--output", type=Path, default=Path("data/external"))
    args = parser.parse_args()

    if args.list:
        print_catalog()
        return

    try:
        urls = parse_dataset_urls(args.url)
    except ValueError as error:
        parser.error(str(error))

    requested = tuple(DATASETS) if args.dataset == "all" else (args.dataset,)
    for key in requested:
        landing_page, access_note = DATASETS[key]
        if key not in urls:
            print(f"{key}: no direct URL supplied. {access_note}\n  Official page: {landing_page}")
            continue
        destination = args.output / key
        archive = download(urls[key], destination / "downloads")
        extract(archive, destination)
        print(f"Downloaded and extracted {key}: {archive} -> {destination}")


if __name__ == "__main__":
    main()
