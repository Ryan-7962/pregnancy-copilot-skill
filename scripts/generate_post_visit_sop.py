from __future__ import annotations

import argparse
from pathlib import Path

from pregnancy_copilot.storage import PregnancyDataStore
from pregnancy_copilot.visit_sop import generate_post_visit_action_sop


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a post-visit action SOP from doctor notes.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--date", required=True, help="Visit date, YYYY-MM-DD.")
    parser.add_argument("--text", help="Doctor note text.")
    parser.add_argument("--input-file", help="Path to a UTF-8 text/markdown file containing doctor notes.")
    parser.add_argument("--source", default="doctor_note")
    args = parser.parse_args()

    if args.input_file:
        doctor_note = Path(args.input_file).read_text(encoding="utf-8")
    elif args.text:
        doctor_note = args.text
    else:
        raise SystemExit("Either --text or --input-file is required.")

    result = generate_post_visit_action_sop(
        PregnancyDataStore(Path(args.data_root)),
        visit_date=args.date,
        doctor_note=doctor_note,
        source=args.source,
    )
    print(result["note_path"])
    print(result["sop_path"])


if __name__ == "__main__":
    main()
