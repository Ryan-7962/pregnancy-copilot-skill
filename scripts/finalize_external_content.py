#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pregnancy_copilot.external_content.runtime import (
    ExternalContentFinalization,
    finalize_external_content,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize a locally captured external source audit.")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--input", type=Path, help="JSON input; stdin is used when omitted")
    args = parser.parse_args()
    text = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
    payload = json.loads(text)
    finalization = ExternalContentFinalization(**payload)
    event = finalize_external_content(args.data_root, finalization)
    print(json.dumps({"ok": True, "source_id": event["source_id"], "raw_path": event["raw_path"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
