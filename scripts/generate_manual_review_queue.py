from __future__ import annotations

import argparse
from pathlib import Path

from pregnancy_copilot.importers.draft_review import generate_manual_review_queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--draft-path", default=None)
    args = parser.parse_args()

    data_root = Path(args.data_root)
    draft_path = Path(args.draft_path) if args.draft_path else None
    queue_path = generate_manual_review_queue(data_root, draft_path=draft_path)
    print(f"Manual review queue: {queue_path}")


if __name__ == "__main__":
    main()
