from __future__ import annotations

import argparse
from pathlib import Path

from pregnancy_copilot.importers.draft_review import apply_manual_review_decisions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--queue-path", default=None)
    parser.add_argument("--draft-path", default=None)
    args = parser.parse_args()

    result = apply_manual_review_decisions(
        Path(args.data_root),
        queue_path=Path(args.queue_path) if args.queue_path else None,
        draft_path=Path(args.draft_path) if args.draft_path else None,
    )
    print(f"Promoted: {result.promoted}")
    print(f"Skipped: {result.skipped}")
    print(f"Corrections needed: {result.corrections_needed}")
    print(f"Unchecked: {result.unchecked}")
    print(f"Duplicates skipped: {result.duplicates}")
    print(f"Report: {result.report_path}")


if __name__ == "__main__":
    main()
