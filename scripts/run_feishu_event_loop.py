from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from pregnancy_copilot.adapters.feishu_cli import FeishuCliAdapter
from pregnancy_copilot.event_processor import process_event_stream
from pregnancy_copilot.runtime_config import build_response_provider_from_env, build_triage_advisor_from_env
from pregnancy_copilot.storage import PregnancyDataStore

try:
    from scripts.init_data_dir import initialize_data_dir
except ModuleNotFoundError:
    from init_data_dir import initialize_data_dir


def build_consume_command(max_events: int = 0, timeout: str = "0", profile: str | None = None) -> list[str]:
    command = lark_command(
        [
            "event",
            "consume",
            "im.message.receive_v1",
            "--as",
            "bot",
            "--quiet",
        ],
        profile=profile,
    )
    if max_events:
        command.extend(["--max-events", str(max_events)])
    if timeout != "0":
        command.extend(["--timeout", timeout])
    return command


def build_runtime_triage_advisor():
    return build_triage_advisor_from_env()


def build_runtime_response_provider():
    return build_response_provider_from_env()


def lark_command(args: list[str], profile: str | None = None) -> list[str]:
    if profile:
        return ["lark-cli", "--profile", profile, *args]
    return ["lark-cli", *args]


def ensure_data_root_initialized(data_root: str | Path) -> PregnancyDataStore:
    root = initialize_data_dir(Path(data_root))
    return PregnancyDataStore(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="./pregnancy-data")
    parser.add_argument("--max-events", type=int, default=0)
    parser.add_argument("--timeout", default="0")
    parser.add_argument("--profile", default=None, help="Optional lark-cli profile name, e.g. <lark-profile>.")
    args = parser.parse_args()

    store = ensure_data_root_initialized(Path(args.data_root))
    adapter = FeishuCliAdapter(profile=args.profile)
    command = build_consume_command(max_events=args.max_events, timeout=args.timeout, profile=args.profile)
    triage_advisor = build_runtime_triage_advisor()
    response_provider = build_runtime_response_provider()

    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as process:
        if process.stdout is None:
            raise RuntimeError("lark-cli event consume did not provide stdout")
        process_event_stream(
            process.stdout,
            store=store,
            adapter=adapter,
            triage_advisor=triage_advisor,
            response_provider=response_provider,
        )
        process.wait()


if __name__ == "__main__":
    main()
