from __future__ import annotations

import importlib.util
import argparse
import subprocess
import sys


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check roadface Python, CUDA and optional model dependencies."
    )
    parser.add_argument(
        "--probe-cuda",
        action="store_true",
        help="Call torch CUDA APIs. Default avoids CUDA initialization as much as possible.",
    )
    parser.add_argument(
        "--skip-torch",
        action="store_true",
        help="Only report package availability and nvidia-smi.",
    )
    return parser.parse_args()


def print_nvidia_smi() -> None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,driver_version", "--format=csv,noheader"],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        print("nvidia-smi: unavailable")
        return
    if result.returncode == 0 and result.stdout.strip():
        print(f"nvidia-smi: {result.stdout.strip()}")
    else:
        print("nvidia-smi: unavailable")


def main() -> None:
    args = parse_args()
    print(f"python: {sys.version.split()[0]}")
    print_nvidia_smi()
    if args.skip_torch:
        print("torch: skipped")
    elif module_available("torch"):
        try:
            import torch

            print(f"torch: {torch.__version__}")
            print(f"torch cuda build: {torch.version.cuda}")
            if args.probe_cuda:
                print(f"cuda available: {torch.cuda.is_available()}")
                print(f"cuda device count: {torch.cuda.device_count()}")
                if torch.cuda.is_available():
                    print(f"cuda device 0: {torch.cuda.get_device_name(0)}")
            else:
                print("cuda probe: skipped; rerun with --probe-cuda to initialize CUDA")
        except Exception as exc:
            print(f"torch import failed: {type(exc).__name__}: {exc}")
    else:
        print("torch: missing")
    if module_available("torchvision"):
        import torchvision

        print(f"torchvision: {torchvision.__version__}")
    else:
        print("torchvision: missing")
    for name in (
        "ultralytics",
        "transformers",
        "accelerate",
        "diffusers",
        "peft",
        "timm",
        "decord",
        "lmdb",
    ):
        print(f"{name}: {'ok' if module_available(name) else 'missing'}")


if __name__ == "__main__":
    main()
