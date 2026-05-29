from __future__ import annotations

import argparse
from pathlib import Path

from pregnancy_copilot.importers.markdown_notes import import_markdown_notes_to_drafts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir")
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--copy-to-reports", action="store_true")
    args = parser.parse_args()

    result = import_markdown_notes_to_drafts(
        source_dir=Path(args.source_dir),
        data_root=Path(args.data_root),
        source="obsidian_import",
        raw_subdir="raw_obsidian_notes",
        default_event_type="prenatal_report",
        copy_to_reports=args.copy_to_reports,
    )
    print(f"Draft events: {result.draft_events_path}")
    print(f"Import report: {result.report_path}")


if __name__ == "__main__":
    main()
