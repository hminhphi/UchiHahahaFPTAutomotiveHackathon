import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "apps",
    "services",
    "packages",
    "ml",
    "infra",
    "tools",
    "research",
    "data",
    "artifacts",
)


def test_major_boundaries_have_readmes() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name / "README.md").is_file()]
    assert missing == []


def test_local_companion_and_generated_roots_are_ignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in (
        ".superpowers/",
        "data/",
        "artifacts/",
        "research/papers/raw/",
        "research/third-party/",
    ):
        assert entry in ignore


def test_legacy_roots_are_removed() -> None:
    assert not (ROOT / "scripts").exists()
    assert not (ROOT / "notebooks").exists()
    assert not (ROOT / "paper").exists()
    assert not (ROOT / "third_party").exists()
    assert not (ROOT / "main.py").exists()


def test_tracked_code_has_no_legacy_imports() -> None:
    offenders = []
    legacy_module = "scripts" + ".roadface"
    legacy_import = "from " + "scripts"
    tracked = subprocess.check_output(
        ["git", "ls-files", "*.py"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for relative in tracked:
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if legacy_module in text or legacy_import in text:
            offenders.append(relative)
    assert offenders == []


def test_tracked_code_has_no_legacy_artifact_roots() -> None:
    legacy_roots = (
        "artifacts/" + "roadface",
        "artifacts/" + "model_cache",
    )
    offenders = []
    tracked = subprocess.check_output(
        ["git", "ls-files", "*.py"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for relative in tracked:
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if any(root in text.replace("\\", "/") for root in legacy_roots):
            offenders.append(relative)
    assert offenders == []
