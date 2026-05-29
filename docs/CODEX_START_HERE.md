# Codex Start Here

你是接手本项目的 Codex 开发代理。请按以下顺序阅读：

1. `README.md`
2. `docs/PRD.md`
3. `docs/DECISION_LOG.md`
4. `docs/ARCHITECTURE.md`
5. `docs/DATA_SCHEMA.md`
6. `docs/SAFETY_RULES.md`
7. `docs/MEMORY_MIGRATION.md`
8. `docs/MEMORY_SYSTEM.md`
9. `docs/FEISHU_ADAPTER.md`
10. `prompts/PROMPTS.md`
11. `docs/TASKS.md`
12. `docs/V0_1_STATUS_AND_GAPS.md`

## 当前目标

不要直接开发大而全系统。请先完成 v0.1 的最小可运行骨架。

## 第一轮开发建议

请先创建：

```text
scripts/init_data_dir.py
src/pregnancy_copilot/
  __init__.py
  config.py
  models.py
  storage.py
  triage.py
  context_builder.py
  prompts.py
  artifacts.py
  adapters/
    __init__.py
    base.py
    feishu_mock.py
tests/
  test_storage.py
  test_triage.py
  test_context_builder.py
```

## 设计限制

- 不要写死任何私有孕妇昵称或家庭称呼。
- 不要把真实数据放进 repo。
- 不要默认云端存储。
- 不要删除旧 events。
- 医学问题必须走安全分级。
- 宝宝日记不能做医学暗示。
