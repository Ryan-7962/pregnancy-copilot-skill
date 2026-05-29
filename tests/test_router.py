from pregnancy_copilot.router import route_message


def test_route_message_detects_dad_diary_command():
    route = route_message("#爸爸日记 今天陪她去产检，她很紧张", sender_role="partner")

    assert route.mode == "dad_diary"
    assert route.command == "#爸爸日记"
    assert route.normalized_text == "今天陪她去产检，她很紧张"


def test_route_message_detects_privacy_commands():
    route = route_message("#只同步建议 今天有点私密内容", sender_role="pregnant_user")

    assert route.mode == "pregnancy_qa"
    assert route.privacy_override == "advice_only"
    assert route.normalized_text == "今天有点私密内容"


def test_route_message_defaults_partner_to_dad_mode_without_command():
    route = route_message("今天想记录一下陪诊感受", sender_role="partner")

    assert route.mode == "dad_mode"
    assert route.command is None
