SYSTEM_PROMPT = """你是 Pregnancy Copilot Skill，一个孕妇优先的孕期 Q&A 与长期记忆助手。

定位：
- 提供类问诊式孕期 Q&A 支持
- 结合孕周、历史孕检、医生医嘱、最近日志回答
- 做红黄绿风险分级
- 帮助整理就医/产检问题
- 自动沉淀日志、医学状态和孕期回忆
- 不替代医生诊断、治疗或处方
"""

HUSBAND_SUMMARY_TEMPLATE = """请根据今天的孕期日志生成给伴侣的可选 summary 日报。

要求：
1. 仅在孕妇明确开启共享时使用。
2. 不同步孕妇标记为 private 的内容。
3. 不直接引用敏感原文。
4. 输出今日身体状态、今日情绪状态、今日她最需要的支持、伴侣可以做的 3 件事、明日提醒。
"""

BABY_DIARY_SAFETY_RULE = "宝宝日记是创意写作，不能承诺健康、暗示检查正常或替代医学判断。"


class PromptBuilder:
    def build_pregnancy_qa_prompt(self, context: str, user_message: str, risk_level: str) -> str:
        return "\n".join(
            [
                SYSTEM_PROMPT.strip(),
                "",
                "请根据以下上下文回答孕妇的问题。",
                "",
                "上下文：",
                context.strip(),
                "",
                "用户问题：",
                user_message.strip(),
                "",
                f"风险级别：{risk_level}",
                "",
                "回答要求：",
                "1. 先用一句话接住情绪。",
                "2. 结合当前孕周和已知背景，但不要编造上下文没有的事实。",
                "3. 说明红 / 黄 / 绿风险判断和原因。",
                "4. 给出现在可以做的 2-4 个行动。",
                "5. 明确什么情况需要联系医生或就医。",
                "6. 信息不足时列出需要补充的问题，不要猜测。",
                "7. 不替代医生诊断、治疗、处方或急诊判断。",
                "8. 不得编造报告数值、医生结论或检查结果。",
            ]
        )


class ResponseWriter:
    def write_triage_reply(self, triage) -> str:
        label = {"green": "绿色", "yellow": "黄色", "red": "红色"}[triage.risk_level]
        lines = [
            "我先帮你做一个初步分级记录。",
            "",
            f"风险分级：{label}",
            f"原因：{triage.reason}",
        ]
        if triage.must_include_medical_disclaimer:
            lines.append("说明：这不是诊断，也不替代医生判断。")
        if triage.risk_level == "red":
            lines.append("这类情况不建议继续只问 AI，请尽快联系产科医生、产科急诊或医院急诊。")
        elif triage.risk_level == "yellow":
            lines.append("建议记录细节，并尽快联系医生或作为下次产检重点询问。")
        else:
            lines.append("可先记录频率、持续时间、是否休息后缓解，并观察是否有升级变化。")
        if triage.doctor_question_candidates:
            lines.extend(["", "可记录给医生的问题："])
            lines.extend(f"- {question}" for question in triage.doctor_question_candidates)
        return "\n".join(lines)
