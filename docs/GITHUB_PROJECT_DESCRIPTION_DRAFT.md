# GitHub 项目说明草稿

这份草稿用于确认 GitHub 仓库简介、README 开头、公开介绍或第一版发布文案。内容已经去隐私化，不包含真实孕期数据、姓名、地点、账号、聊天原文或报告原文。

## 一句话简介

基于 LLM + Agent 的孕妇长期健康助手：围绕整个孕期持续互动，长期记住当前孕周、最新报告、历史症状、日常指标和家庭记录。

## GitHub About 建议

基于 LLM + Agent 的孕妇长期健康助手。支持长期孕期记忆、当前医学状态、日常日志、产检问题清单和宝宝周记素材。

## GitHub 首页项目介绍建议

Pregnancy Copilot Skill 是一个基于 LLM + Agent 的孕妇长期健康助手，面向有孕妇的家庭，而不只是面向开发者。

这个项目来自一个真实家庭的孕期 AI 使用经验。2026 年上半年，LLM、Agent 和 web coding 工具能力快速提升；项目作者也正好经历了老婆怀孕。在这个过程中，家庭开始大量使用 Gemini 和其他大模型来询问症状、理解检查报告、拆解医嘱、确认饮食和运动边界，并缓解很多“不知道要不要紧”的孕期焦虑。

这些真实使用证明，大模型已经能给孕期家庭带来实际帮助：它能 24 小时回应，能把复杂信息讲清楚，也能帮助家庭更理性地准备产检和医生沟通。但长期使用后也暴露出明显问题：普通聊天会失忆，旧报告和新报告容易混在一起，换模型或换聊天窗口会丢上下文，很多有价值的问答没有沉淀成结构化档案。

Pregnancy Copilot Skill 就是基于这些真实使用习惯整理出来的。它希望把“单次问答的大模型”变成一个更适合孕期长周期使用的 Agent Skill，并把这个经验分享给更多有孕妇的家庭。

它适合几类人：

- 程序员老公想送给老婆一个更懂她孕期状态的电子助手；
- 本身懂技术的孕妇想给自己配置一个长期可迁移的 Pregnancy Copilot；
- 已经在用 ChatGPT、Gemini、Claude、NotebookLM 或本地 Agent 的家庭，希望解决孕期上下文丢失和报告数据过期的问题；
- Agent 开发者希望接入一个本地优先的孕期健康记忆 skill。

它主要解决的问题：

- 孕期每天都有新问题、新症状、新报告和新焦虑，普通聊天机器人容易忘记上下文。
- 同一个医学指标会变化，AI 需要知道哪个是最新值，哪个只是历史记录。
- 产检报告、医生建议、体重、睡眠、心情、饮食、运动和用药记录太分散，需要结构化归档。
- 家庭希望 AI 24 小时待命，但不希望把敏感孕期数据默认交给云端长期保存。

它的特点：

- 长期孕期记忆：保存原文、事件、当前上下文、当前医学状态和日常指标。
- 本地数据持有：真实 `pregnancy-data/` 默认在用户本地，不随代码发布。
- 当前医学状态：新报告刷新当前值，旧报告保留为历史趋势。
- 条件式安全提示：只在症状、异常报告或需要医生确认时展示红 / 黄 / 绿提示。
- 产检问题清单：把近期疑问沉淀为下次问医生的问题。
- 家庭记录：生成日常日志、宝宝周记素材、可选伴侣 summary 和爸爸日记。
- 可替换通道：飞书/Lark 是当前最完整测试通道，微信、Telegram、Web UI 等可由宿主 Agent 适配。

未来希望补齐：

- 产检日历和检查提醒；
- 产检前问诊 SOP；
- 检查后下一阶段行动 SOP；
- 更强的 OCR/报告结构化；
- 更低门槛的非技术用户安装体验。

## 中文 README 开头草稿

Pregnancy Copilot Skill 是一个基于 LLM + Agent 的孕妇长期健康助手。

它面向有孕妇的家庭，让你的 AI 不只是“会回答一次孕期问题”，而是能围绕整个孕期持续互动，长期记住孕周、检查报告、症状变化、医嘱、日常记录和家庭偏好。适合程序员老公帮老婆搭一个孕期 AI 助手，也适合本身懂技术的孕妇给自己配置长期 Pregnancy Copilot。

孕期最难的不是偶尔查一个答案，而是每天都在面对新的不确定性：

- 今天肚子发紧要不要紧？
- 上周 B 超的异常，这周是不是已经恢复？
- 医生说的注意事项，下一次产检前还能不能想起来？
- 饮食、用药、运动、睡眠、情绪，哪些值得记录？
- 换一个 AI、换一个聊天窗口，之前半年的上下文是不是又没了？

Pregnancy Copilot Skill 想解决的是这个长期问题。

它把孕期对话、检查报告、日常症状、体重睡眠、医生建议和产检问题沉淀成一个本地可控的孕期记忆系统。宿主 Agent 仍然负责对话和推理，Skill 负责让它读到正确的上下文：当前孕周、最新医学数据、旧数据变化、需要复查的事项和历史记录。

它不是医生，也不是医疗器械。它的目标是帮助孕妇和家庭更理性、更结构化地面对孕期焦虑：该记录的记录，该复查的复查，该问医生的问医生，普通焦虑则用更完整的上下文来解释。

## 当前 v0.3.0 可以公开承诺的能力

- 初始化本地 `pregnancy-data/` 目录和基础档案模板。
- 保存原始聊天输入和结构化孕期事件。
- 生成给宿主 Agent 使用的当前上下文。
- 维护最新医学指标，同时保留旧值作为历史。
- 记录体重、睡眠、心情、饮食、运动等日常数据。
- 对症状和异常报告做条件式红 / 黄 / 绿安全提示。
- 普通闲聊可读取最小孕期上下文，但不强行显示风险分级或写入医疗状态。
- 生成产检问题清单、日常日志、宝宝周记素材和可选伴侣 summary。
- 支持 Host Runtime 给 Hermes/OpenClaw/Codex/Claude Code 等宿主 Agent 调用。
- 提供飞书/Lark CLI 测试通道和 runtime worker。
- 提供公开合成案例测试，不包含真实隐私数据。

## 当前不应公开承诺的能力

- 不是完整消费级 App。
- 不提供医疗诊断或处方。
- 不内置独立 LLM；默认使用宿主 Agent 的模型。
- 不承诺微信通道已经开箱即用；微信可以由 Hermes/OpenClaw 等宿主 Agent 接入后转给 Host Runtime。
- 不承诺自动 OCR 或完整报告解析。
- 不承诺无需技术配置的安装体验。

## 通道表达建议

飞书/Lark CLI 是已有测试适配器之一，但不是默认通道或产品边界。

更准确的表达是：

```text
孕妇常用聊天入口
  -> 宿主 Agent
  -> Pregnancy Copilot Skill
  -> 本地 pregnancy-data 记忆目录
```

如果宿主 Agent 支持微信入口，微信会更贴近日常孕妇使用习惯；但微信通道本身可能存在消息限制、稳定性和第三方接入约束。Skill 只要求宿主 Agent 把消息转成 Host Runtime 请求。

## English Description

Pregnancy Copilot Skill is a long-term pregnancy health assistant built on LLM + Agent workflows.

It is not a standalone app, a medical device, or a replacement for obstetric care. It runs inside a host Agent such as Hermes, OpenClaw, Codex, Claude Code, or a similar workflow. The host Agent provides the LLM and conversation interface; this skill provides durable pregnancy memory, current medical state, source history, daily metrics, safety prompts, and family-memory artifacts.

The core problem is not one-off pregnancy Q&A. The harder problem is long-running pregnancy context: medical values change, old report findings may be resolved, symptoms and daily notes are scattered, and switching models or chat channels can break continuity.

v0.3.0 can provide answer-first adaptive onboarding, local pregnancy memory, current-versus-historical medical observations with provenance, daily consolidation, a compact conversation index, a source-aware prenatal plan, and channel-neutral reminder actions. Daily jobs and delivery still require the host Agent or operating-system scheduler.

Feishu/Lark CLI is an available tested adapter, but it is not the product boundary. We welcome experiments and feedback for WeChat, Telegram, Slack, Discord, web UI, and host-Agent default chat channels.

## Suggested GitHub Topics

`agent-skill`, `pregnancy`, `local-first`, `llm-memory`, `health-data`, `personal-ai`, `hermes`, `openclaw`, `feishu`, `markdown`, `jsonl`
