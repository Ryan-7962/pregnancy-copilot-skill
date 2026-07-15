# Memory Migration：版本升级与记忆保护

## 1. 核心原则

> Memory is sacred. 孕期数据对个人无价，任何升级都不能丢失原始数据。

## 2. 数据与代码分离

```text
pregnancy-copilot-skill/   # 代码和规则，可升级
pregnancy-data/            # 用户个人孕期数据，不随代码覆盖
```

## 3. Append-only Event Log

所有事件写入 JSONL，默认只追加，不覆盖。

如果需要更正，新增 correction event。

```json
{
  "schema_version": "0.1",
  "event_type": "correction",
  "target_event_id": "2026-05-01T21-30-00-feishu-001",
  "correction": "原记录中'无腹痛'应改为'轻微腹痛，休息后缓解'",
  "timestamp": "2026-05-02T09:00:00+08:00"
}
```

## 4. schema_version

每条事件必须带 `schema_version`。

```json
"schema_version": "0.1"
```

v0.2 或 v1.0 升级时通过迁移脚本转换。

## 5. 升级前备份

每次升级前必须创建备份：

```text
pregnancy-data/backups/2026-05-05-before-v0.2.zip
```

备份内容：

- inbox
- events
- memory
- reports
- daily_logs
- weekly_reviews
- husband_summaries
- baby_diaries
- doctor_questions
- feishu_docs

备份 ZIP 默认未加密。“保存在本地”不等于“只有孕妇可读”；请使用系统磁盘加密、文件权限和独立备份位置。同一天重复备份会生成新文件，不覆盖旧快照。

恢复验证：

```python
from pregnancy_copilot.backup import restore_upgrade_backup, verify_upgrade_backup

verify_upgrade_backup("pregnancy-data/backups/2026-07-15-before-v0.2.1.zip")
restore_upgrade_backup(
    "pregnancy-data/backups/2026-07-15-before-v0.2.1.zip",
    "/tmp/pregnancy-data-restored",
)
```

恢复目标必须为空目录，ZIP 内路径会先进行穿越校验。

## 5.1 v0.2.0 -> v0.2.1

```bash
PYTHONPATH=src .venv/bin/python scripts/upgrade_to_v021.py \
  --data-root ./pregnancy-data
```

该命令按以下顺序执行：

1. 创建升级前 ZIP。
2. 校验 ZIP 完整性与成员路径。
3. 仅当 profile 完整匹配未编辑的 v0.2.0 演示模板时，清空仿真孕周/医院/关注项。
4. 部分编辑的档案不自动删值，只列出待人工复核字段。
5. 从 append-only 观测重建 current medical state 和 current context。
6. 写入本地迁移报告。

## 6. 迁移脚本

建议目录：

```text
migrations/
├── 001_v0_1_to_v0_2.py
├── 002_v0_2_to_v1_0.py
└── README.md
```

迁移脚本必须：

1. 检测当前 schema_version
2. 备份数据
3. 读取旧事件
4. 转换为新 schema
5. 生成迁移报告
6. 不删除旧数据
7. 失败时回滚或提示人工确认

## 7. 摘要再生成机制

v0.1 必须允许从 events 重新生成：

- current_context.md
- long_term_summary.md
- medical_timeline.md
- weekly_reviews
- husband_summaries
- baby_diaries

这保证 v2 可以使用更好的摘要策略，而不丢 v1 数据。

## 8. 迁移报告模板

```markdown
# Migration Report

From: v0.1
To: v0.2
Date: 2026-05-05

## Summary

- Events read: 386
- Events migrated: 386
- Reports read: 7
- Daily logs read: 42
- Manual review required: 3

## Backup

pregnancy-data/backups/2026-05-05-before-v0.2.zip

## New Fields

- risk_level_confidence
- doctor_question_status
- sync_consent_status

## Warnings

- 3 historical events lacked gestational_age and require manual confirmation.
```

## 9. Gemini / NotebookLM / Obsidian 历史导入

历史导入也应视为迁移的一部分。

输入：

- Gemini markdown exports
- NotebookLM full export
- Obsidian pregnancy notes
- historical dad diaries

输出：

- inbox/raw_*
- events/*.jsonl
- reports/*.md
- memory/long_term_summary.md
- memory/medical_timeline.md
