# Message Intents and Conditional Triage

v0.3.0 uses two layers: deterministic routing for explicit records/commands and host-LLM semantic classification for everything else in the configured pregnant-user entrypoint.

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
| `pregnancy_context` | yes | no | no | 饮食/出行问题或普通闲聊；由宿主 LLM 判断语义相关性 |

## Host Runtime Behavior

For unmatched messages, `process_host_message` returns a context-only result:

```json
{
  "handled": true,
  "intent": "pregnancy_context",
  "reply_text": "",
  "event": null,
  "risk_level": "not_applicable"
}
```

The host Agent reads `semantic_routing_contract`, decides medical relevance, and answers normally. If the message is ordinary chat, it must not add a risk label or medical-state event.

For handled pregnancy intents, the skill writes local memory and returns `reply_text`.

## Standalone Event Loop Behavior

The standalone Feishu event loop has no host semantic layer. It can use an explicitly configured optional LLM command; otherwise it only has the deterministic fallback and must not claim that a semantic assessment occurred.

## Schema Compatibility

Events keep `risk_level` for v0.1 schema compatibility. Non-triage events set:

```json
{
  "triage_required": false,
  "risk_level": "not_applicable"
}
```

Consumers should check `triage_required` before showing a red/yellow/green label or counting risk distribution.
