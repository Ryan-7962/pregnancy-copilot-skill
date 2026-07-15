# Memory System v0.2.1

Pregnancy Copilot 使用本地、可审计、可重建的文件记忆。无需云数据库或向量数据库。

## 1. 事实源与派生层

```text
raw inbox                 原始输入，追加保存
events.jsonl              结构化事件，追加保存
medical_observations.jsonl 医疗观测完整历史，追加保存
profile.yaml              用户确认或明确提供的基础档案
        |
        v
current_medical_state.yaml 当前值、历史值、候选项
current_context.md         宿主 LLM 的工作上下文
daily_metrics.*            高频数据近期趋势
generated artifacts        日志、周记、问诊清单和 SOP
```

raw、events 和 medical observations 是审计依据。`current_*`、索引和作品都是可重建派生物，不能替代原始事实源。

## 2. 原始输入

有效的孕妇入口消息保存在：

```text
inbox/raw_<channel>_messages/YYYY-MM-DD.md
```

优先使用通道原始 `message_id`/`event_id` 做幂等键。普通闲聊也可保留原文，但不因此生成医学事件或风险状态。

## 3. 结构化事件

`events/events.jsonl` 保存需要进入长期记忆的事件。每条记录包含事件 ID、时间、来源、原文引用、摘要、隐私级别以及适用时的风险信息。

修正通过追加新记录表达，不回写删除旧事件。重复投递相同事件 ID 只保存一次，并发追加受文件锁保护。

## 4. 医疗观测时间线

`events/medical_observations.jsonl` 保存所有结构化医疗值。每条观测至少记录：

- `metric_key`、值和单位；
- `measured_at` 与 `recorded_at`；
- `status` 和 `source_confidence`；
- `source_event_id`、`raw_source_path` 或明确的人工录入 provenance。

当前状态生成规则：

1. 只让日期有效且可信度足够的观测竞争 current。
2. 较新的有效观测成为 current；旧值进入 `previous_values`。
3. 无日期、低可信度或显式 superseded 的观测进入 `candidates`。
4. 候选不得覆盖 current。
5. 所有旧值继续保留，用于变化趋势和审计。
6. 不知道时保持 `unknown`，不能从上下文猜值。

支持 `unknown`、`confirmed`、`corrected`、`superseded` 等生命周期状态。

## 5. 档案与孕周

`memory/profile.yaml` 保存用户明确提供的档案。新模板不包含仿真医院、孕周或医学事实。

孕周优先根据 LMP 或 EDD 与当前日期动态计算。带记录日期的静态孕周只作为缺少时间锚点时的兼容回退，不能永久冒充当前孕周。

建档允许多轮补充。缺少字段会列为待补充，但只有 pregnancy time anchor 是常规回答准备度的核心字段；紧急问题始终优先处理。

## 6. 高频日常数据

体重、血压、心情、饮食、活动和睡眠从非私密正式事件生成：

```text
memory/daily_metrics.yaml
memory/daily_metrics.md
```

每个点保留日期和来源事件。体重提供 latest、previous 和 delta；其他类别保留近期摘要。缺失日期不补齐，原始事件仍是事实源。

## 7. 工作上下文

`memory/current_context.md` 聚合：

- 动态孕周和 profile readiness；
- 当前医学值、最近历史和待确认候选；
- 高频日常指标；
- 来源可信度与待核对事项；
- 最近正式事件和医生问题。

宿主 Agent 不需要每次扫描全部聊天历史。它读取这个最小上下文，再按需追溯 source path。

## 8. 身份隔离

单孕妇部署会把可信 channel/conversation/sender 绑定到唯一根目录。多孕妇部署必须由宿主可信配置提供 `pregnancy_id`，每个身份写入：

```text
pregnancy-data-root/identities/<pregnancy_id>/
```

未绑定入口不能认领已有身份；消息 payload 中自报的 `pregnancy_id` 不可信。

## 9. 原子性与恢复

- JSONL 追加和幂等检查在锁内完成。
- profile、current state、current context 和核心索引使用临时文件加原子替换。
- 升级前创建不覆盖旧快照的 ZIP，并校验成员完整性和路径安全。
- 恢复只允许写入空目录，拒绝绝对路径和 `..`。
- ZIP 默认未加密，部署者仍需使用文件权限和磁盘加密保护。

## 10. 隐私边界

本地 `pregnancy-data/` 是长期事实源，不代表消息从未经过其他系统。聊天通道、宿主模型、主机管理员、备份介质和操作系统权限都有各自隐私政策。

公开仓库、测试和发布包只能使用合成数据。Gemini 等历史导入内容在人工确认前只是线索，不能成为当前医疗事实。

## 11. 重建

```bash
PYTHONPATH=src .venv/bin/python scripts/rebuild_memory.py \
  --data-root ./pregnancy-data \
  --date 2026-07-15
```

该命令从事实源重建 current context、current medical state、医学时间线、情绪模式、日常指标和指定日期日志。
