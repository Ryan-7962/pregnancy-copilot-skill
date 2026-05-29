from __future__ import annotations

import argparse
import json
from pathlib import Path

from pregnancy_copilot.profile_readiness import check_profile_readiness

try:
    from scripts.init_data_dir import initialize_data_dir
except ModuleNotFoundError:
    from init_data_dir import initialize_data_dir


def run_profile_readiness_check(data_root: str | Path, initialize: bool = False) -> dict:
    if initialize:
        initialize_data_dir(data_root)
    return check_profile_readiness(data_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether memory/profile.yaml is ready for real pregnancy use.")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--init", action="store_true", help="Initialize the data directory first if needed.")
    args = parser.parse_args()

    result = run_profile_readiness_check(args.data_root, initialize=args.init)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
