import yaml
from concurrent.futures import ThreadPoolExecutor

from pregnancy_copilot.data_init import initialize_data_dir
from pregnancy_copilot.pregnancy_time import calculate_gestational_age
from pregnancy_copilot.profile_onboarding import (
    apply_profile_onboarding_update,
    extract_profile_onboarding_update,
)
from pregnancy_copilot.profile_readiness import check_profile_readiness
from pregnancy_copilot.storage import PregnancyDataStore


def test_lmp_only_is_valid_progressive_onboarding_anchor(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    update = extract_profile_onboarding_update("建档信息：LMP 2026-05-01。", as_of="2026-07-24")

    assert update.is_profile_intake is True
    assert update.profile_updates["last_menstrual_period"] == "2026-05-01"
    apply_profile_onboarding_update(store, update, "evt-lmp", "inbox/raw_agent/messages.md")

    readiness = check_profile_readiness(tmp_path)
    assert readiness["status"] == "ready"
    assert "display_name" in readiness["optional_missing_fields"]
    assert calculate_gestational_age(store.load_profile(), as_of="2026-07-24") == "12w0d"


def test_full_natural_language_profile_extracts_supported_baseline_fields():
    update = extract_profile_onboarding_update(
        "建档信息：称呼：测试用户，1994年出生，身高160cm，孕前体重52kg，当前体重53.2kg。"
        "LMP 2026-05-01，EDD 2027-02-05，所在城市：上海，产检医院：测试妇幼。"
        "既往史：甲减；孕产史：初孕；过敏：青霉素；用药：叶酸0.4mg/日；"
        "医生医嘱：避免剧烈运动；当前关注：甲状腺复查；下次产检：2026-07-30。",
        as_of="2026-07-15",
    )

    updates = update.profile_updates
    assert update.is_profile_intake is True
    assert updates["display_name"] == "测试用户"
    assert updates["demographics"] == {
        "birth_year": 1994,
        "height_cm": 160.0,
        "pre_pregnancy_weight_kg": 52.0,
        "current_weight_kg": 53.2,
    }
    assert updates["last_menstrual_period"] == "2026-05-01"
    assert updates["due_date"] == "2027-02-05"
    assert updates["hospital"]["city"] == "上海"
    assert updates["hospital"]["name"] == "测试妇幼"
    assert updates["next_checkup"] == "2026-07-30"
    assert updates["medical_baseline"]["history"] == ["甲减"]
    assert updates["medical_baseline"]["obstetric_history"] == ["初孕"]
    assert updates["medical_baseline"]["allergies"] == ["青霉素"]
    assert updates["medical_baseline"]["medications"] == ["叶酸0.4mg/日"]
    assert updates["medical_baseline"]["doctor_orders"] == ["避免剧烈运动"]
    assert updates["current_focus"] == ["甲状腺复查"]


def test_progressive_profile_updates_merge_without_erasing_prior_fields(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    first = extract_profile_onboarding_update("建档：LMP 2026-05-01", as_of="2026-07-15")
    second = extract_profile_onboarding_update("我补充一下：身高160cm，当前体重53.2kg", as_of="2026-07-16")

    apply_profile_onboarding_update(store, first, "evt-1", "inbox/1.md")
    apply_profile_onboarding_update(store, second, "evt-2", "inbox/2.md")
    profile = yaml.safe_load((tmp_path / "memory" / "profile.yaml").read_text(encoding="utf-8"))

    assert profile["last_menstrual_period"] == "2026-05-01"
    assert profile["demographics"]["height_cm"] == 160.0
    assert profile["demographics"]["current_weight_kg"] == 53.2


def test_due_date_can_drive_dynamic_gestational_age_without_static_week():
    profile = {"due_date": "2027-02-05", "current_gestational_age": None}

    assert calculate_gestational_age(profile, as_of="2026-07-24") == "12w0d"


def test_concurrent_progressive_profile_updates_do_not_erase_each_other(tmp_path):
    initialize_data_dir(tmp_path)
    store = PregnancyDataStore(tmp_path)
    updates = [
        extract_profile_onboarding_update("我补充一下：身高160cm", as_of="2026-07-15"),
        extract_profile_onboarding_update("我补充一下：当前体重53.2kg", as_of="2026-07-15"),
    ]

    def apply(index: int) -> None:
        apply_profile_onboarding_update(store, updates[index], f"evt-{index}", f"inbox/{index}.md")

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(apply, range(2)))

    profile = store.load_profile()
    assert profile["demographics"]["height_cm"] == 160.0
    assert profile["demographics"]["current_weight_kg"] == 53.2
