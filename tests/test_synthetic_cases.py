from pathlib import Path

from scripts.run_synthetic_case_acceptance import run_synthetic_case_acceptance


CASES_PATH = Path("examples/synthetic_cases/pregnancy_synthetic_cases.json")
PRIVATE_MARKERS = [
    "Gemini",
    "CONVERSATION" + "_LOG",
]


def test_synthetic_cases_are_public_safe_text_only():
    text = CASES_PATH.read_text(encoding="utf-8")

    assert "fully synthetic" in text
    for marker in PRIVATE_MARKERS:
        assert marker not in text


def test_synthetic_cases_cover_realistic_runtime_paths(tmp_path):
    result = run_synthetic_case_acceptance(data_root=tmp_path, cases_path=CASES_PATH)

    assert result["ok"] is True
    assert result["case_count"] == 9
    by_id = {item["id"]: item for item in result["results"]}
    assert by_id["symptom_green_abdominal_tightness_rest_relief"]["actual"]["risk_level"] == "green"
    assert by_id["symptom_red_bleeding_with_persistent_pain"]["actual"]["risk_level"] == "red"
    assert by_id["general_chat_pass_through"]["actual"]["host_action_type"] == "pass_through"
    assert (tmp_path / "events" / "events.jsonl").exists()
    assert (tmp_path / "memory" / "current_context.md").exists()
