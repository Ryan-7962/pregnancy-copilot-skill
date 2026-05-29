from __future__ import annotations

import argparse
import json
from pathlib import Path

from pregnancy_copilot.source_confidence import import_obsidian_gemini_state
from pregnancy_copilot.storage import PregnancyDataStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Import refined Obsidian Gemini state cards without reading raw chats.")
    parser.add_argument("source_dir", help="Obsidian Gemini folder that contains 状态提炼/.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    args = parser.parse_args()

    result = import_obsidian_gemini_state(Path(args.source_dir), PregnancyDataStore(args.data_root))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
