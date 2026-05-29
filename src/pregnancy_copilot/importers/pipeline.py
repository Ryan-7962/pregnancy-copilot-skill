from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pregnancy_copilot.context_builder import build_current_context
from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.importers.draft_review import (
    PromotionResult,
    generate_manual_review_queue,
    promote_import_drafts,
)
from pregnancy_copilot.importers.gemini_markdown import ImportResult, import_gemini_zip_to_drafts
from pregnancy_copilot.storage import PregnancyDataStore


@dataclass
class GeminiImportPipelineResult:
    import_result: ImportResult
    promotion_result: PromotionResult
    queue_path: Path
    context_path: Path
    pipeline_report_path: Path


def run_gemini_import_pipeline(zip_path: str | Path, data_root: str | Path) -> GeminiImportPipelineResult:
    root = Path(data_root)
    initialize_data_dir(root)
    import_result = import_gemini_zip_to_drafts(zip_path, root)
    promotion_result = promote_import_drafts(root, draft_path=import_result.draft_events_path)
    queue_path = generate_manual_review_queue(root, draft_path=import_result.draft_events_path)
    context_path = build_current_context(PregnancyDataStore(root))
    pipeline_report_path = root / "exports" / "gemini_import_pipeline_report.md"
    pipeline_report_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline_report_path.write_text(
        render_pipeline_report(import_result, promotion_result, queue_path, context_path),
        encoding="utf-8",
    )
    return GeminiImportPipelineResult(
        import_result=import_result,
        promotion_result=promotion_result,
        queue_path=queue_path,
        context_path=context_path,
        pipeline_report_path=pipeline_report_path,
    )


def render_pipeline_report(
    import_result: ImportResult,
    promotion_result: PromotionResult,
    queue_path: Path,
    context_path: Path,
) -> str:
    return "\n".join(
        [
            "# Gemini Import Pipeline Report",
            "",
            "## Results",
            "",
            f"- Sources read: {import_result.source_count}",
            f"- Turns extracted: {import_result.turn_count}",
            f"- Manual review required: {import_result.manual_review_count}",
            f"- Auto-promoted events: {promotion_result.promoted}",
            f"- Manual events skipped by auto-promotion: {promotion_result.skipped_manual}",
            f"- Duplicates skipped: {promotion_result.duplicates}",
            "",
            "## Outputs",
            "",
            f"- Draft events: {import_result.draft_events_path}",
            f"- Promotion report: {promotion_result.report_path}",
            f"- Manual review queue: {queue_path}",
            f"- Current context: {context_path}",
            "",
            "## Safety",
            "",
            "- Only green, non-medication, non-report draft events are promoted automatically.",
            "- Report, medication, yellow, and red events remain in the manual review queue.",
            "- Imported AI summaries are memory hints, not authoritative medical facts.",
        ]
    ) + "\n"
