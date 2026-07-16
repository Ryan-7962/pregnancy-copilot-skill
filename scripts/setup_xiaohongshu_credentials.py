#!/usr/bin/env python3
from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path

from pregnancy_copilot.external_content.credentials import (
    COOKIE_FILE_ENV,
    DEFAULT_COOKIE_PATH,
    validate_xhs_cookie_header,
    write_xhs_cookie_secret,
)


def run_setup(
    source_file: Path | None,
    output: Path,
    *,
    replace: bool,
    pregnancy_data_root: Path | None,
) -> dict:
    cookie_input = (
        source_file.expanduser().read_text(encoding="utf-8")
        if source_file is not None
        else getpass("Paste the Xiaohongshu Cookie or Netscape Cookie content (hidden): ")
    )
    path = write_xhs_cookie_secret(
        cookie_input,
        output,
        replace=replace,
        pregnancy_data_root=pregnancy_data_root,
    )
    status = validate_xhs_cookie_header(path.read_text(encoding="utf-8"))
    return {
        "path": path,
        "valid": status.valid,
        "missing_required_names": status.missing_required_names,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Store a Xiaohongshu Cookie outside pregnancy-data.")
    parser.add_argument("--output", type=Path, default=DEFAULT_COOKIE_PATH)
    parser.add_argument("--cookie-file", type=Path, help="Raw or Netscape Cookie file to import")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--pregnancy-data-root", type=Path)
    args = parser.parse_args()

    result = run_setup(
        args.cookie_file,
        args.output,
        replace=args.replace,
        pregnancy_data_root=args.pregnancy_data_root,
    )
    if not result["valid"]:
        print("Cookie saved, but required names are missing: " + ", ".join(result["missing_required_names"]))
        return 2
    print(f"Cookie saved with mode 0600: {result['path']}")
    print(f"Set {COOKIE_FILE_ENV} to this path in the Agent environment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
