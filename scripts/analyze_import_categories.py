from __future__ import annotations

import argparse
import json
from pathlib import Path

from pregnancy_copilot.importers.analysis import (
    analyze_import_drafts,
    write_import_category_report,
    write_review_lane_report,
    write_review_sample_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze draft import categories without exposing raw private text.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--draft-path", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--sample-output", default=None)
    parser.add_argument("--sample", action="store_true", help="Write a privacy-safe manual-review sample report.")
    parser.add_argument("--lanes", action="store_true", help="Write a privacy-safe manual-review lane report.")
    parser.add_argument("--per-bucket", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="Print JSON counts instead of a Markdown path.")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    draft_path = Path(args.draft_path) if args.draft_path else data_root / "events" / "draft_import_events.jsonl"
    if args.json:
        print(json.dumps(analyze_import_drafts(draft_path).to_dict(), ensure_ascii=False, indent=2))
        return

    if args.sample:
        output = (
            Path(args.sample_output)
            if args.sample_output
            else data_root / "exports" / "manual_review_sample_report.md"
        )
        report_path = write_review_sample_report(draft_path, output, per_bucket=args.per_bucket)
        print(f"Manual review sample report: {report_path}")
        return

    if args.lanes:
        output = (
            Path(args.output)
            if args.output
            else data_root / "exports" / "manual_review_lane_report.md"
        )
        report_path = write_review_lane_report(draft_path, output, examples_per_group=args.per_bucket)
        print(f"Manual review lane report: {report_path}")
        return

    output = Path(args.output) if args.output else data_root / "exports" / "import_category_report.md"
    report_path = write_import_category_report(draft_path, output)
    print(f"Import category report: {report_path}")


if __name__ == "__main__":
    main()
