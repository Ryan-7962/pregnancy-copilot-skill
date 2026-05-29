from __future__ import annotations

import argparse
from pathlib import Path

from pregnancy_copilot.importers.pipeline import run_gemini_import_pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    parser.add_argument("--data-root", default="./pregnancy-data")
    args = parser.parse_args()

    result = run_gemini_import_pipeline(Path(args.zip_path), Path(args.data_root))
    print(f"Draft events: {result.import_result.draft_events_path}")
    print(f"Promoted: {result.promotion_result.promoted}")
    print(f"Manual review queue: {result.queue_path}")
    print(f"Current context: {result.context_path}")
    print(f"Pipeline report: {result.pipeline_report_path}")


if __name__ == "__main__":
    main()
