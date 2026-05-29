from pregnancy_copilot.intent_router import classify_intent


def test_classify_medical_symptom_requires_triage():
    result = classify_intent("今天有点出血，肚子也痛")

    assert result.intent == "medical_triage"
    assert result.handled_by_skill is True
    assert result.triage_required is True
    assert result.write_to_memory is True


def test_classify_normal_report_review_does_not_force_triage():
    result = classify_intent("这个 B 超报告数据是什么意思")

    assert result.intent == "report_review"
    assert result.triage_required is False


def test_classify_abnormal_report_review_requires_triage():
    result = classify_intent("B 超报告提示异常，需要复查")

    assert result.intent == "report_review"
    assert result.triage_required is True


def test_classify_pregnancy_log_writes_memory_without_triage():
    result = classify_intent("今天体重 65kg，早餐吃了鸡蛋和牛奶")

    assert result.intent == "pregnancy_log"
    assert result.handled_by_skill is True
    assert result.triage_required is False
    assert result.write_to_memory is True


def test_classify_mood_support_writes_memory_without_triage():
    result = classify_intent("今天心情不错，但晚上有点焦虑")

    assert result.intent == "mood_support"
    assert result.triage_required is False
    assert result.write_to_memory is True


def test_classify_general_chat_is_not_handled_by_skill():
    result = classify_intent("明天天气怎么样，顺便推荐一首歌")

    assert result.intent == "general_chat"
    assert result.handled_by_skill is False
    assert result.triage_required is False
    assert result.write_to_memory is False
