# TASKS：Codex 开发任务清单

## 阶段 0：初始化项目

- [x] 创建基础目录结构
- [x] 确认 README / PRD / ARCHITECTURE / DATA_SCHEMA / SAFETY_RULES 已存在
- [x] 创建 `pregnancy-data/` 示例目录生成脚本
- [x] 创建 `.env.example`
- [x] 创建 `.gitignore`

验收：

```bash
python scripts/init_data_dir.py --target ./pregnancy-data
```

能生成完整目录。

## 阶段 1：本地记忆 MVP

- [x] 实现 inbox 原文保存
- [x] 实现 events.jsonl append-only 写入
- [x] 实现 profile.yaml 读取
- [x] 实现 current_context.md 生成
- [x] 实现 daily_log.md 生成
- [x] 实现 schema_version 字段检查

验收：

- 输入一条模拟飞书消息
- 生成 raw message
- 生成 event
- 更新 current_context
- 生成 daily log

## 阶段 2：安全分级 MVP

- [x] 实现红旗症状关键词/语义规则表
- [x] 实现 green/yellow/red triage
- [x] 实现医学声明策略
- [x] 实现缺失信息追问模板
- [x] 添加测试用例

测试用例：

```text
今天肚子有点紧，休息后好了
我流血了
宝宝今天动得明显少了
我头痛很厉害还眼花
这个 B 超数据是什么意思
```

## 阶段 3：Q&A Prompt Orchestration

- [x] 设计 MessageEvent 数据类
- [x] 设计 ContextBuilder
- [x] 设计 PromptBuilder
- [x] 设计 ResponseWriter
- [x] 预留 LLM provider 接口
- [x] 不绑定具体模型

## 阶段 4：飞书适配器草案

- [x] 定义 FeishuAdapter interface
- [x] 支持接收消息的内部格式
- [x] 支持发送回复的内部格式
- [x] 支持写入飞书文档的接口草案
- [x] 支持身份/模式路由

MVP 可以先用 mock adapter，不必立刻接真实飞书 API。

## 阶段 5：老公 summary 日报

- [x] 根据 daily_log 生成 husband_summary
- [x] 支持 privacy_level
- [x] 默认只同步 summary
- [x] private 内容不进入 summary
- [x] 支持 `#只同步建议`

## 阶段 6：爸爸日记与宝宝周记

- [x] 支持 `#爸爸日记` 原文保存
- [x] 生成整理版爸爸日记
- [x] 标题符合规范
- [x] 每周生成宝宝视角周记
- [x] 宝宝日记安全检查：禁止医学暗示

## 阶段 7：备份与迁移

- [x] 实现 backup command
- [x] 升级前打 zip
- [x] 实现 migration report 模板
- [x] 预留 migrations/ 目录
- [x] 能从 events 重新生成 current_context

## 阶段 8：历史导入器草案

- [x] 读取 Gemini markdown
- [x] 读取 NotebookLM markdown
- [x] 读取 Obsidian 孕检笔记
- [x] 提取 event draft
- [x] 标记需要人工确认的医学事实

## 不要在 v0.1 做

- [ ] 复杂 GUI
- [ ] 云数据库
- [ ] 多飞书机器人
- [ ] 微信适配
- [ ] 医生端
- [ ] 国际版产检流程
- [ ] 全自动 OCR
