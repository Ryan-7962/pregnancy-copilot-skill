from pregnancy_copilot.host_runtime import HostMessageRequest, process_host_message
from pregnancy_copilot.medical_state import read_current_medical_state
from pregnancy_copilot.storage import PregnancyDataStore
from scripts.process_host_message import run_host_message
from tests.helpers import make_profile_ready


def test_process_host_message_initializes_data_root_and_returns_reply(tmp_path):
    result = process_host_message(
        HostMessageRequest(
            text="今天肚子有点紧，休息后好了，没有流血也没有流水",
            sender_id="pregnant-user-openclaw",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-07T13:40:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert result.risk_level == "profile_needs_review"
    assert result.mode == "onboarding"
    assert result.event_id.startswith("host-")
    assert "先完成孕期建档" in result.reply_text
    assert "最近一次产检" in result.reply_text
    assert "W20+0" not in result.reply_text
    assert result.context_package is not None
    assert "W20+0" not in result.context_package["context_markdown"]
    assert (tmp_path / "memory" / "profile.yaml").exists()
    assert not (tmp_path / "events" / "events.jsonl").exists()
    assert (tmp_path / "inbox" / "raw_hermes_messages" / "2026-05-07.md").exists()
    assert result.event is None
    assert result.host_action["type"] == "collect_profile"


def test_process_host_message_accepts_profile_onboarding_intake(tmp_path):
    result = process_host_message(
        HostMessageRequest(
            text=(
                "【虚拟测试建档信息】这是一份用于测试 Pregnancy Copilot Skill 的虚拟 W12 档案，不是真实孕妇资料。\n"
                "孕妇基础信息：测试孕妇A，1994年出生，身高 160cm，孕前体重 52.0kg，当前体重 53.2kg，所在城市：上海。\n"
                "孕期锚点：当前孕周 12w3d；LMP 2026-03-02；EDD 2026-12-07。\n"
                "就诊信息：测试市妇幼保健院，产科门诊；下次产检约 2026-06-10。\n"
                "最近一次产检/报告：2026-05-26，孕 12w1d，NT 1.4mm，CRL 56mm，胎心 158 bpm，单胎，胎盘后壁，羊水未见异常；"
                "医生口头反馈：NT 低风险，按时复查。\n"
                "长期关注项：无阴道出血、无流液、无严重腹痛；无已知药物过敏；目前服用叶酸 0.4mg/日。\n"
                "偏好：简体中文，回答清晰克制，医学问题需要明确风险边界；默认不向家人同步。"
            ),
            sender_id="pregnant-user-openclaw",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-28T21:40:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert result.intent == "profile_onboarding"
    assert result.risk_level == "not_applicable"
    assert "建档信息已保存" in result.reply_text
    assert "当前孕期档案已可用于后续问答" in result.reply_text
    profile = (tmp_path / "memory" / "profile.yaml").read_text(encoding="utf-8")
    assert "测试孕妇A Pregnancy Profile" in profile
    assert "current_gestational_age: 12w3d" in profile
    assert "due_date: '2026-12-07'" in profile
    assert "name: 测试市妇幼保健院" in profile
    assert (tmp_path / "events" / "events.jsonl").exists()
    observations = (tmp_path / "events" / "medical_observations.jsonl").read_text(encoding="utf-8")
    assert '"metric_key": "nt"' in observations
    assert '"metric_key": "fetal_heart_rate"' in observations


def test_process_host_message_refreshes_report_observations_after_profile_ready(tmp_path):
    process_host_message(
        HostMessageRequest(
            text=(
                "建档信息：孕妇基础信息：测试孕妇A，所在城市：上海。"
                "当前孕周 12w3d；EDD 2026-12-07。"
                "就诊信息：测试市妇幼保健院。"
                "最近一次产检/报告：2026-05-26，NT 1.4mm，CRL 56mm，胎心 158 bpm，胎盘后壁。"
            ),
            sender_id="pregnant-user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-28T21:40:00+08:00",
        ),
        data_root=tmp_path,
    )

    result = process_host_message(
        HostMessageRequest(
            text="新的产检报告：2026-06-01，孕 12w6d，NT 1.2mm，CRL 61mm，胎心 156 bpm，胎盘前壁。",
            sender_id="pregnant-user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-06-01T10:00:00+08:00",
        ),
        data_root=tmp_path,
    )

    state = read_current_medical_state(PregnancyDataStore(tmp_path))
    assert result.event["intent"] == "report_review"
    assert result.event["triage_required"] is False
    assert result.risk_level == "not_applicable"
    assert "已记录这次报告信息" in result.reply_text
    assert state["metrics"]["nt"]["current"]["value"] == "1.2"
    assert state["metrics"]["nt"]["previous_values"][0]["value"] == "1.4"
    assert state["metrics"]["crl"]["current"]["value"] == "61"
    assert state["metrics"]["placenta_position"]["current"]["value"] == "前壁"


def test_process_host_message_answers_after_profile_is_ready(tmp_path):
    process_host_message(
        HostMessageRequest(
            text="今天肚子有点紧，休息后好了，没有流血也没有流水",
            sender_id="pregnant-user-openclaw",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-07T13:40:00+08:00",
        ),
        data_root=tmp_path,
    )
    profile_path = tmp_path / "memory" / "profile.yaml"
    profile_text = profile_path.read_text(encoding="utf-8")
    profile_text = profile_text.replace('profile_name: "Example Pregnancy Profile"', 'profile_name: "Test Pregnancy Profile"')
    profile_text = profile_text.replace('display_name: "孕妇"', 'display_name: "测试用户"')
    profile_text = profile_text.replace('baby_nickname: "宝宝"', 'baby_nickname: "测试宝宝"')
    profile_text = profile_text.replace('current_gestational_age: "20w0d"', 'current_gestational_age: "23w1d"')
    profile_text = profile_text.replace('name: "示例医院"', 'name: "测试医院"')
    profile_path.write_text(profile_text, encoding="utf-8")

    result = process_host_message(
        HostMessageRequest(
            text="今天肚子有点紧，休息后好了，没有流血也没有流水",
            sender_id="pregnant-user-openclaw",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-07T13:41:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert result.risk_level == "green"
    assert result.mode == "pregnancy_qa"
    assert "绿色" in result.reply_text
    assert (tmp_path / "events" / "events.jsonl").exists()
    assert result.event["source"] == "hermes"
    assert result.event["chat_id"] == "pregnancy-window"


def test_host_runtime_supports_optional_partner_extension_in_one_memory(tmp_path):
    make_profile_ready(tmp_path)
    pregnant = process_host_message(
        HostMessageRequest(
            text="#只同步建议 今天有点焦虑，想要一些陪伴建议",
            sender_id="pregnant-user",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-07T13:41:00+08:00",
        ),
        data_root=tmp_path,
    )
    partner = process_host_message(
        HostMessageRequest(
            text="#爸爸日记 今天陪她散步，她状态好一些了。",
            sender_id="husband",
            sender_role="partner",
            conversation_id="husband-window",
            channel="hermes",
            timestamp="2026-05-07T13:42:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert pregnant.privacy_level == "advice_only"
    assert partner.mode == "dad_diary"
    assert "爸爸日记已记录" in partner.reply_text
    events = (tmp_path / "events" / "events.jsonl").read_text(encoding="utf-8")
    assert '"chat_id": "pregnancy-window"' in events
    assert '"chat_id": "husband-window"' in events
    context = (tmp_path / "memory" / "current_context.md").read_text(encoding="utf-8")
    assert "今天有点焦虑" in context
    assert "今天陪她散步" in context


def test_run_host_message_script_returns_json_ready_result(tmp_path):
    make_profile_ready(tmp_path)
    result = run_host_message(
        data_root=tmp_path,
        text="这个 B 超数据是什么意思",
        sender_id="pregnant-user",
        sender_role="pregnant_user",
        conversation_id="pregnancy-window",
        channel="hermes",
        timestamp="2026-05-07T13:43:00+08:00",
    )

    assert result["ok"] is True
    assert result["event_id"].startswith("host-")
    assert result["mode"] == "pregnancy_qa"
    assert result["intent"] == "report_review"
    assert result["risk_level"] == "not_applicable"
    assert "reply_text" in result


def test_host_runtime_returns_unhandled_for_general_chat_without_writing_memory(tmp_path):
    result = process_host_message(
        HostMessageRequest(
            text="明天天气怎么样，推荐一首歌",
            sender_id="pregnant-user",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-07T13:44:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert result.handled is False
    assert result.intent == "general_chat"
    assert result.reply_text == ""
    assert result.event is None
    assert not (tmp_path / "events" / "events.jsonl").exists()
    assert not (tmp_path / "inbox" / "raw_hermes_messages").exists()


def test_host_runtime_records_pregnancy_log_without_triage_reply(tmp_path):
    make_profile_ready(tmp_path)
    result = process_host_message(
        HostMessageRequest(
            text="今天体重 65kg，早餐吃了鸡蛋和牛奶",
            sender_id="pregnant-user",
            sender_role="pregnant_user",
            conversation_id="pregnancy-window",
            channel="hermes",
            timestamp="2026-05-07T13:45:00+08:00",
        ),
        data_root=tmp_path,
    )

    assert result.handled is True
    assert result.intent == "pregnancy_log"
    assert result.triage_required is False
    assert result.risk_level == "not_applicable"
    assert "风险分级" not in result.reply_text
    assert "已记录" in result.reply_text
    assert result.event["intent"] == "pregnancy_log"
    assert result.event["triage_required"] is False
    assert result.event["risk_level"] == "not_applicable"
