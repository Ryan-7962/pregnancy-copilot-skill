from __future__ import annotations

import argparse
from pathlib import Path
import re


PRIVATE_DIRS = {"docs/private", "pregnancy-data", ".codex"}
IGNORED_DIRS = {".pytest_cache", ".venv", "venv"}
GENERATED_DIR_NAMES = {"__pycache__", "build", "dist"}
PRIVATE_SUFFIXES = {".zip", ".key", ".pem"}
PRIVATE_NAMES = {
    ".DS_Store",
    ".env",
    ".env.local",
    ".releaseignore.local",
    "PRIVATE_NOTES.md",
    "xiaohongshu_cookie.txt",
    "xhs_cookie.txt",
}
PRIVATE_TEXT_MARKER_PARTS = {
    ("CONVERSATION", "_LOG"),
    ("PRIVATE_HISTORY", "_EXPORT"),
    ("file", "_v3_"),
    ("doc", "_26"),
    ("pi", "-rob"),
}
PRIVATE_TEXT_PATTERNS = [
    re.compile(r"/" + r"Users/[^/\s]+/"),
    re.compile(r"\b(?:ghp_|github_pat_|sk-|xox[baprs]-)[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bcli_[A-Za-z0-9]{12,}\b"),
]


def find_release_blockers(root: str | Path) -> list[str]:
    root = Path(root)
    blockers: list[str] = []
    scan_dir(root, root, blockers)
    return sorted(set(blockers))


def scan_dir(root: Path, directory: Path, blockers: list[str]) -> None:
    for path in directory.iterdir():
        rel = path.relative_to(root).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue
        if path.is_dir():
            if path.name in IGNORED_DIRS:
                continue
            if path.name in GENERATED_DIR_NAMES or path.name.endswith(".egg-info"):
                blockers.append(f"{rel}/")
                continue
            if rel in PRIVATE_DIRS:
                blockers.append(f"{rel}/")
                continue
            scan_dir(root, path, blockers)
            continue
        if path.name in PRIVATE_NAMES or path.suffix in PRIVATE_SUFFIXES:
            blockers.append(rel)
            continue
        if path.name.startswith("._"):
            blockers.append(rel)
            continue
        if contains_private_marker(path):
            blockers.append(f"{rel}: contains private marker")
        elif contains_private_pattern(path):
            blockers.append(f"{rel}: contains private pattern")


def contains_private_marker(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any("".join(parts) in text for parts in PRIVATE_TEXT_MARKER_PARTS)


def contains_private_pattern(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any(pattern.search(text) for pattern in PRIVATE_TEXT_PATTERNS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    blockers = find_release_blockers(args.root)
    if not blockers:
        print("Release check passed: no private/generated blockers found.")
        return

    print("Release blockers found:")
    for blocker in blockers:
        print(f"- {blocker}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
