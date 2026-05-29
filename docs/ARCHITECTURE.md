# Architecture：Pregnancy Copilot Skill v0.1

## 1. 总体架构

```text
Host Agent conversation or Feishu Bot
  ↓
Runtime connection
  ├── Host Agent Runtime (preferred in v0.1.2)
  ├── native host-Agent event routing
  ├── Hermes/OpenClaw supervised worker
  └── standalone event loop
  ↓
Message Router
  ↓
Mode Detector
  ├── Pregnancy Q&A Mode
  ├── Dad Diary Mode
  ├── Baby Diary Mode
  └── Couple Coordination Mode
  ↓
Memory Context Builder
  ↓
Safety Triage
  ↓
LLM Response Generator
  ↓
Event Writer / Artifact Writer
  ↓
Feishu Reply / Feishu Doc Sync
```

## 2. 核心模块

### 2.1 Message Adapter

默认实现：Feishu Adapter。

职责：

- 接收飞书消息
- 识别发送者和聊天类型
- 抽象为内部 MessageEvent
- 发送回复
- 可选写入飞书文档和多维表格

未来可替换为：

- WeChat
- Telegram
- WhatsApp
- Email
- CLI

### 2.2 Message Router

根据以下信息路由：

- sender_id
- chat_type
- command prefix
- message content
- user role

指令示例：

```text
#爸爸日记
#宝宝日记
#不同步
#可同步
#只同步建议
#产检问题
#今日总结
```

### 2.3 Memory Context Builder

每次回答时不要读取全部原文，而是按需构建上下文。

默认读取：

- `memory/profile.yaml`
- `memory/current_context.md`
- 最近 24-72 小时 daily_logs
- 本周 weekly_review
- safety rules

报告问题读取：

- `memory/medical_timeline.md`
- `reports/*.md`
- doctor_notes

情绪问题读取：

- `memory/emotional_pattern.md`
- 最近情绪事件
- 适合用户的安抚偏好

宝宝日记读取：

- 本周 weekly_review
- 老公日记
- 孕周发育科普
- 宝宝日记安全规则

### 2.4 Safety Triage

负责红黄绿风险分级。

输出：

```json
{
  "risk_level": "green|yellow|red|not_applicable",
  "reason": "...",
  "red_flags_detected": [],
  "must_include_medical_disclaimer": true,
  "must_recommend_doctor_contact": false
}
```

### 2.5 Memory Writer

写入：

- 原文：`inbox/`
- 结构化事件：`events/*.jsonl`
- 当前上下文：`memory/current_context.md`
- 每日摘要：`daily_logs/YYYY-MM-DD.md`
- 老公日报：`husband_summaries/YYYY-MM-DD.md`
- 宝宝日记：`baby_diaries/week-XX.md`

### 2.6 Artifact Generator

生成：

- 老公孕期日记
- 宝宝视角周记
- 每周宝宝来信
- 产检故事卡
- 产后回忆录章节草稿

### 2.7 Migration Manager

负责：

- schema_version 识别
- 升级前备份
- 事件流重放
- 摘要再生成
- 迁移报告

## 3. 飞书通道设计

v0.1.5 核心不要求先设计夫妻双角色系统。推荐形态是一个 Hermes/OpenClaw host Agent 管理孕妇常用聊天入口，调用同一个 Pregnancy Copilot Skill 和同一个 `pregnancy-data/`。

```text
孕妇聊天窗口或 pregnancy bot → Hermes/OpenClaw host Agent → Host Agent Runtime → pregnancy-data/
```

Feishu P2P bot chat 仍是已验证兼容路径，可以使用一个飞书机器人作为孕妇聊天入口。

```text
孕妇私聊机器人 → Pregnancy Q&A / log / medical-state mode
#宝宝日记 → Baby Diary Mode
```

同时，v0.1 支持通过 `lark-cli --profile` 选择不同飞书 app/profile，便于测试不同聊天通道或机器人。这里的 profile 只选择飞书应用身份；它不等于已经连接到 Hermes/OpenClaw。

```text
孕妇 → pregnancy bot/profile → active event loop or host-Agent router → pregnancy-data/
```

伴侣 summary、爸爸日记、夫妻群、双 bot 自动邀请、身份绑定和授权 UI 都不属于 v0.1 默认主路径。v0.1.5 先提供 host runtime API，让宿主 Agent 自己决定如何把窗口、bot、用户身份映射到 `sender_role` 和 `conversation_id`。

## 3.1 隐私与角色原则

孕妇本人是第一用户和数据所有者。伴侣、家人或技术配置者可以维护系统，但不默认拥有完整数据读取权。

默认共享级别应为不共享。`summary` 或 `full` 共享必须来自孕妇用户的明确选择。

## 4. 主数据源原则

本地 `pregnancy-data/` 是主数据源。

飞书文档和多维表格只是展示层/协作层。

```text
local events / memory
  ↓
generate markdown artifacts
  ↓
sync to Feishu docs / sheets
```

## 5. 模型策略

Skill 不绑定具体 LLM。默认使用宿主 Agent 自带模型。

建议任务路由：

```text
medical_safety_task → best available reasoning model
report_explanation_task → best available reasoning model
diary_rewrite_task → best available writing model
simple_logging_task → fast low-cost model
```

v0.1 可以只实现配置项，不实现复杂自动路由。

## 6. 数据流

### 6.1 Q&A 数据流

```text
User question
→ save raw message to inbox
→ classify question
→ build context
→ safety triage
→ generate answer
→ write event
→ update current_context
→ reply
```

### 6.2 Dad Diary 数据流

```text
#爸爸日记 raw text
→ save raw to inbox/raw_dad_diary
→ generate formatted diary
→ write diary_event
→ sync to Feishu doc
→ optional generate baby diary material
```

### 6.3 Baby Diary 数据流

```text
weekly summary + dad diary + pregnancy week info
→ generate baby POV diary
→ check no medical implication
→ save to baby_diaries
→ optional sync to Feishu doc
```
