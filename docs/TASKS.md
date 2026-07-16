# TASKS: Pregnancy Copilot Skill

## 已完成基础能力

- [x] 初始化本地 `pregnancy-data/`。
- [x] 保存 raw inbox 和 append-only events。
- [x] 生成 current context、daily log 和可选家庭作品。
- [x] 提供模型无关 Prompt、Host Runtime 和通道适配器接口。
- [x] 提供红黄绿安全底线、医生问题和产检前后 SOP。
- [x] 提供 Gemini、NotebookLM 和 Obsidian 草稿导入与人工复核通道。
- [x] 提供备份、迁移、安装检查和发布包扫描。

## v0.2.1 可靠性加固

- [x] 有效入口消息默认加载最小孕期上下文。
- [x] 普通闲聊不强制风险分级或医疗写入。
- [x] 宿主 LLM 负责医学语义，确定性规则只保留安全兜底。
- [x] 首次主动建档、第一消息建档回退和渐进式补录。
- [x] LMP/EDD 动态孕周和无仿真事实模板。
- [x] 医疗 current/history/candidates 和来源可信度规则。
- [x] 高频日常数据时间序列和近期趋势。
- [x] 单孕妇绑定与多孕妇身份目录隔离。
- [x] 消息/事件幂等、并发锁、核心派生状态原子写入。
- [x] 安全路径、升级前备份、完整性校验和恢复。
- [x] 路由、建档、医疗状态、身份、并发、路径和 LLM 降级对抗测试。

## v0.2.1 发布门禁

- [x] 本地全量测试通过。
- [x] 单用户、Host Runtime、通道和合成案例验收通过。
- [x] 干净发布目录通过隐私扫描。
- [x] ZIP 解压后使用外部虚拟环境重新安装并跑完整测试。
- [x] 最终 ZIP 不含缓存、私有目录、真实语料或本机路径。
- [x] GitHub main、`v0.2.1` tag 和 Public Alpha Release 发布。
- [x] 下载 GitHub 资产并验证 SHA256 与本地一致。

## v0.3.0 自适应陪伴与计划

- [x] 回答优先的渐进式 onboarding，不固定五轮。
- [x] 能力、边界、隐私、事实录入和记录控制微教程。
- [x] `跳过教程`、`继续教程` 和 `这条不记录`。
- [x] 每日对话归并与 `daily_conversation_index.yaml`。
- [x] 产检计划、改期历史和来源区分。
- [x] channel-neutral、幂等的检查前提醒动作。
- [x] v0.2.1 -> v0.3.0 备份优先迁移。
- [x] v0.3.0 功能已并入后续发布线。

## v0.4.0 外部内容审计

- [x] 小红书 URL 检测、域名/重定向限制和 SSR 结构化解析。
- [x] Cookie 终端私密配置、`0600` 权限和凭据隔离。
- [x] 小红书 CDN 图片受限下载与宿主视觉/OCR 接口。
- [x] 视频 `ask/always/never` 策略、ffmpeg 音频准备和可选 SiliconFlow ASR。
- [x] 外部来源 MD、append-only JSONL、版本去重与精简相关性索引。
- [x] prompt injection 边界和 `social_media_unverified` 医学事实隔离。
- [x] “这条不记录”、默认媒体清理、每日来源引用和自适应教程。
- [x] v0.3.0 -> v0.4.0 备份优先迁移。
- [x] v0.4.0 全量/对抗性测试、真实授权链路验收和隐私扫描。
- [x] v0.4.0 新信息图、干净发布包和 GitHub Release。

## 暂不扩展

- 独立 App、复杂 GUI 或云数据库。
- 默认微信、飞书或其他专属通道业务逻辑。
- 医生端、诊断、处方或把 OCR 自动提升为医学事实。
- 任意社交平台抓取、绕过登录或自动信任社交媒体医学结论。
- 自动伴侣共享和无需技术配置的消费级安装器。
