# Roadmap

## v0.1：飞书优先的本地记忆 Q&A MVP

- 单飞书机器人多模式
- 本地 Markdown + JSONL
- 孕期 Q&A
- 红黄绿分级
- current_context
- 每日摘要
- 老公 summary 日报
- 爸爸日记
- 宝宝周记
- 备份与 schema_version

当前 v0.1 完成度与缺口见 `docs/V0_1_STATUS_AND_GAPS.md`。

## v0.2：历史导入与更强记忆

- Gemini markdown 导入
- NotebookLM 导入
- Obsidian 孕检笔记导入
- Obsidian Gemini 状态提炼层导入
- source_confidence / open_review_items 可信度记忆
- 用户可选 response_style / agent_soul
- medical_timeline 自动生成
- emotional_pattern 自动生成
- daily_metrics 高频日常指标索引
- doctor_questions 生命周期管理
- 产检前/检查后 SOP 基础 Markdown 生成
- SQLite 可选存储

## v0.3：产检计划与提醒

- [x] 回答优先、自适应且可跳过的新手引导
- [x] 每日对话归并与紧凑索引
- [x] 本地产检计划、改期历史和 D-N 提醒动作
- [x] 产检前 SOP、医生问题和检查后行动入口联动
- [ ] 有权威来源的地区/医院流程建议模板
- [ ] 更多宿主的现成 scheduler 配置样例
- [ ] 用药等高频提醒类型扩展

## v0.4：更多消息通道

- Telegram adapter
- Email adapter
- CLI adapter
- 微信/企业微信 adapter 探索

## v1.0：稳定开源 Skill

- 完整文档
- 示例数据
- 安全规则测试
- 迁移工具
- 多环境部署教程
- public demo profile
- privacy-first release checklist
