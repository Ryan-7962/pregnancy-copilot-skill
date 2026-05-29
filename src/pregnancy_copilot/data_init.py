from __future__ import annotations

from pathlib import Path


DATA_DIRS = [
    "inbox/raw_feishu_messages",
    "inbox/raw_gemini_exports",
    "inbox/raw_notebooklm_exports",
    "inbox/raw_obsidian_notes",
    "inbox/raw_dad_diary",
    "events",
    "memory",
    "reports",
    "daily_logs",
    "weekly_reviews",
    "husband_summaries",
    "baby_diaries",
    "doctor_questions",
    "feishu_docs",
    "exports",
    "backups",
]

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent.parent / "pregnancy-data-template"


def initialize_data_dir(target: str | Path) -> Path:
    root = Path(target)
    for directory in DATA_DIRS:
        (root / directory).mkdir(parents=True, exist_ok=True)

    memory_template_root = TEMPLATE_ROOT / "memory"
    if memory_template_root.exists():
        for template in memory_template_root.glob("*"):
            if template.is_file():
                destination = root / "memory" / template.name
                if not destination.exists():
                    destination.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    return root

