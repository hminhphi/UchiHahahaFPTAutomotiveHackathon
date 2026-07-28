from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ("apps", "services", "packages", "ml", "infra", "tools", "research", "data", "artifacts")


def test_major_boundaries_have_readmes() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name / "README.md").is_file()]
    assert missing == []


def test_local_companion_and_generated_roots_are_ignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in (".superpowers/", "data/", "artifacts/", "research/papers/raw/", "research/third-party/"):
        assert entry in ignore
