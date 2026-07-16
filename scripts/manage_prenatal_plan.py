from __future__ import annotations

import argparse
import json
from pathlib import Path

from pregnancy_copilot.onboarding_state import advance_onboarding_state
from pregnancy_copilot.prenatal_plan import read_prenatal_plan, sync_profile_next_checkup, upsert_plan_item
from pregnancy_copilot.storage import PregnancyDataStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the local Pregnancy Copilot prenatal plan.")
    parser.add_argument("--data-root", default="./pregnancy-data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    add = subparsers.add_parser("add")
    add.add_argument("--json", required=True)
    subparsers.add_parser("sync-profile")
    enable = subparsers.add_parser("enable-reminders")
    enable.add_argument("--lead-days", type=int, default=1)
    subparsers.add_parser("disable-reminders")
    args = parser.parse_args()

    store = PregnancyDataStore(Path(args.data_root))
    if args.command == "list":
        result = read_prenatal_plan(store)
    elif args.command == "add":
        result = upsert_plan_item(store, json.loads(args.json))
    elif args.command == "sync-profile":
        result = sync_profile_next_checkup(store)
    else:
        enabled = args.command == "enable-reminders"
        lead_days = args.lead_days if enabled else 1
        result = advance_onboarding_state(
            store,
            preference_updates={"prenatal_reminders_enabled": enabled, "reminder_lead_days": lead_days},
            increment_interaction=False,
        )
        sync_profile_next_checkup(store)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
