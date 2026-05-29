# Message Intents and Conditional Triage

v0.1.3 classifies each incoming message before deciding what to do.

The goal is to avoid medicalizing every pregnant-user chat message. Red/yellow/green triage is only shown when the message is about medical risk, symptoms, reports, medication, fetal movement, or similar pregnancy safety topics.

## Intent Table

| Intent | Handled by skill | Triage shown | Write memory | Examples |
| --- | --- | --- | --- | --- |
| `medical_triage` | yes | yes | yes | 出血, 宫缩, 腹痛, 胎动异常, 破水 |
| `medication` | yes | yes | yes | 用药, 剂量, 叶酸, 钙片, 抗生素 |
| `report_review` | yes | yes | yes | B 超, 检查报告, 胎心, 唐筛, 糖耐 |
| `pregnancy_log` | yes | no | yes | 体重, 血压, 血糖, 饮食, 运动, 睡眠 |
| `mood_support` | yes | no | yes | 心情, 焦虑, 紧张, 开心, 难过 |
| `diary` | yes | no | yes | 日记, 随笔, 想记录一下 |
| `general_chat` | no | no | no | 天气, 歌曲推荐, 普通闲聊 |

## Host Runtime Behavior

For `general_chat`, `process_host_message` returns:

```json
{
  "handled": false,
  "intent": "general_chat",
  "reply_text": "",
  "event": null
}
```

The host Agent should then answer with its normal conversation flow.

For handled pregnancy intents, the skill writes local memory and returns `reply_text`.

## Standalone Event Loop Behavior

The standalone Feishu event loop cannot hand a message back to a host Agent. It still processes handled pregnancy intents and keeps compatibility with existing smoke tests.

## Schema Compatibility

Events keep `risk_level` for v0.1 schema compatibility. Non-triage events set:

```json
{
  "triage_required": false,
  "risk_level": "not_applicable"
}
```

Consumers should check `triage_required` before showing a red/yellow/green label or counting risk distribution.
