from __future__ import annotations

import json
import argparse

from pregnancy_copilot.feishu_readiness import check_feishu_readiness


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None, help="Optional lark-cli profile name, e.g. <lark-profile>.")
    args = parser.parse_args()

    report = check_feishu_readiness(profile=args.profile)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
