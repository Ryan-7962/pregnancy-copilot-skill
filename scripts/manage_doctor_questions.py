from __future__ import annotations

import argparse
from pathlib import Path

from pregnancy_copilot.doctor_questions import (
    read_doctor_questions,
    render_doctor_questions_markdown,
    update_question_status,
)
from pregnancy_copilot.storage import PregnancyDataStore


def main() -> None:
    parser = argparse.ArgumentParser(description="List or update pregnancy doctor questions.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--status", action="append", help="Filter by status. Can be repeated.")

    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("question_id")
    update_parser.add_argument("status", choices=["open", "asked", "answered", "archived"])
    update_parser.add_argument("--answer-summary")

    args = parser.parse_args()
    store = PregnancyDataStore(Path(args.data_root))

    if args.command == "list":
        records = read_doctor_questions(store, statuses=args.status)
        if not records:
            print("No doctor questions found.")
            return
        for record in records:
            print(f"{record['question_id']}\t{record['status']}\t{record['question']}")
        return

    updated = update_question_status(
        store,
        question_id=args.question_id,
        status=args.status,
        answer_summary=args.answer_summary,
    )
    path = render_doctor_questions_markdown(store)
    print(f"Updated {updated['question_id']} -> {updated['status']}")
    print(f"Rendered {path}")


if __name__ == "__main__":
    main()
