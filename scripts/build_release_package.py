from __future__ import annotations

import argparse
import shutil
from pathlib import Path

try:
    from scripts.release_check import find_release_blockers
except ModuleNotFoundError:
    from release_check import find_release_blockers


EXCLUDED_DIRS = {
    ".git",
    ".codex",
    ".pytest_cache",
    ".venv",
    "venv",
    "pregnancy-data",
    "docs/private",
    "docs/superpowers",
    "__pycache__",
}
EXCLUDED_NAMES = {".DS_Store", ".env", ".env.local", ".releaseignore.local", "PRIVATE_NOTES.md"}
EXCLUDED_PATHS = {"docs/JIMMY_BLACKBOX_TEST_REPORT.md", "docs/HOST_CHANNEL_BLACKBOX_TEST_REPORT.md"}
EXCLUDED_SUFFIXES = {".zip", ".pyc", ".key", ".pem", ".diff"}


def build_release_package(source_root: str | Path, target_root: str | Path) -> list[str]:
    source_root = Path(source_root)
    target_root = Path(target_root)
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True)
    excluded_dirs = EXCLUDED_DIRS | load_local_release_ignores(source_root)

    copied: list[str] = []
    for path in source_root.rglob("*"):
        rel = path.relative_to(source_root).as_posix()
        if should_exclude(path, rel, excluded_dirs=excluded_dirs):
            continue
        target = target_root / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(rel)

    blockers = find_release_blockers(target_root)
    if blockers:
        joined = "\n".join(f"- {blocker}" for blocker in blockers)
        raise RuntimeError(f"Release package contains blockers:\n{joined}")
    return sorted(copied)


def load_local_release_ignores(source_root: Path) -> set[str]:
    path = source_root / ".releaseignore.local"
    if not path.exists():
        return set()
    entries = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip().rstrip("/")
        if not value or value.startswith("#"):
            continue
        entries.add(value)
    return entries


def should_exclude(path: Path, rel: str, excluded_dirs: set[str] | None = None) -> bool:
    excluded_dirs = excluded_dirs or EXCLUDED_DIRS
    if any(rel == dirname or rel.startswith(f"{dirname}/") for dirname in excluded_dirs):
        return True
    if rel in EXCLUDED_PATHS:
        return True
    if any(part in excluded_dirs for part in Path(rel).parts):
        return True
    if path.is_dir() and path.name in excluded_dirs:
        return True
    if path.name in EXCLUDED_NAMES:
        return True
    if path.name.startswith("._"):
        return True
    return path.is_file() and path.suffix in EXCLUDED_SUFFIXES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=".")
    parser.add_argument("--target", default="/tmp/pregnancy-copilot-skill-release")
    args = parser.parse_args()

    copied = build_release_package(args.source, args.target)
    print(f"Release package: {Path(args.target).resolve()}")
    print(f"Files copied: {len(copied)}")


if __name__ == "__main__":
    main()
