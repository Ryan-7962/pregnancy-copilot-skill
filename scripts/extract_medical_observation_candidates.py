from __future__ import annotations

import argparse
import json
from pathlib import Path

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.importers.medical_candidates import (
    extract_medical_observation_candidates,
    promote_medical_observation_candidates,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract or promote medical observation candidates from import drafts.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--draft-path", default=None)
    parser.add_argument("--candidates-path", default=None)
    parser.add_argument("--review-path", default=None)
    parser.add_argument("--promote-reviewed", action="store_true")
    args = parser.parse_args()

    initialize_data_dir(args.data_root)
    if args.promote_reviewed:
        result = promote_medical_observation_candidates(
            args.data_root,
            candidates_path=Path(args.candidates_path) if args.candidates_path else None,
        )
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2, default=str))
        return

    result = extract_medical_observation_candidates(
        args.data_root,
        draft_path=Path(args.draft_path) if args.draft_path else None,
        candidates_path=Path(args.candidates_path) if args.candidates_path else None,
        review_path=Path(args.review_path) if args.review_path else None,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
