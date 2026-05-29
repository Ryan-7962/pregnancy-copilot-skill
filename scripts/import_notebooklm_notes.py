from __future__ import annotations

import argparse
from pathlib import Path

from pregnancy_copilot.importers.markdown_notes import import_markdown_notes_to_drafts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir")
    parser.add_argument("--data-root", default="./pregnancy-data")
    args = parser.parse_args()

    result = import_markdown_notes_to_drafts(
        source_dir=Path(args.source_dir),
        data_root=Path(args.data_root),
        source="notebooklm_import",
        raw_subdir="raw_notebooklm_exports",
        default_event_type="imported_note",
    )
    print(f"Draft events: {result.draft_events_path}")
    print(f"Import report: {result.report_path}")


if __name__ == "__main__":
    main()
