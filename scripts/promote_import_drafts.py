from __future__ import annotations

import argparse
from pathlib import Path

from pregnancy_copilot.importers.draft_review import promote_import_drafts, review_import_drafts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--draft-path", default=None)
    parser.add_argument("--review-only", action="store_true")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    draft_path = Path(args.draft_path) if args.draft_path else data_root / "events" / "draft_import_events.jsonl"

    if args.review_only:
        review = review_import_drafts(draft_path)
        print(f"Total draft events: {review.total}")
        print(f"Auto promotable: {review.auto_promotable}")
        print(f"Manual review required: {review.manual_required}")
        return

    result = promote_import_drafts(data_root, draft_path=draft_path)
    print(f"Promoted: {result.promoted}")
    print(f"Skipped manual review: {result.skipped_manual}")
    print(f"Duplicates skipped: {result.duplicates}")
    print(f"Report: {result.report_path}")


if __name__ == "__main__":
    main()
