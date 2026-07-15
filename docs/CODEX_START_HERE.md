# Codex Start Here

你是接手 Pregnancy Copilot Skill 的开发 Agent。当前版本目标是 v0.2.1 Public Alpha，不是重新搭建 v0.1 骨架。

## 阅读顺序

1. `README.md`
2. `SKILL.md`
3. `docs/PRD.md`
4. `docs/ARCHITECTURE.md`
5. `docs/DATA_SCHEMA.md`
6. `docs/SAFETY_RULES.md`
7. `docs/HOST_AGENT_RUNTIME.md`
8. `docs/MEMORY_SYSTEM.md`
9. `docs/MEMORY_MIGRATION.md`
10. `docs/TASKS.md`

`docs/V0_1_STATUS_AND_GAPS.md` 和旧版本 release notes 只是历史快照，不能作为当前行为规范。

## 当前产品边界

- 这是宿主 Agent 使用的 Skill，不是独立 App。
- 宿主 LLM 负责语义理解和最终回答；Skill 负责本地孕期记忆、事实来源、时间状态、身份隔离和安全底线。
- 所有有效的孕妇专属入口消息都获得最小孕期上下文。
- 只有医学相关内容才做风险判断和结构化医疗写入。
- 不绑定飞书、微信、特定模型或额外 LLM API。
- 不写入真实测试数据，不把未知医疗信息补成事实。

## 开始工作前

```bash
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/install_check.py \
  --data-root /tmp/pregnancy-copilot-install-check
```

修改必须保持原始记录可追溯、历史医疗值不丢失、升级前备份和发布包隐私扫描。新增行为先写失败测试，再做最小实现。
