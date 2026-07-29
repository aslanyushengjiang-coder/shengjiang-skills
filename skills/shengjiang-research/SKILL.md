---
name: shengjiang-research
description: >
  Uses the user's own paid TikHub API to research public social-media creators,
  accounts, posts, videos, comments, transcripts, topics, and performance data,
  then exports traceable JSON, Markdown, CSV, or Excel assets. Use whenever the
  user mentions 生姜调研、全平台调研、博主调研、对标账号、抓作品、抓评论、逐字稿、
  TikHub、抖音、小红书、视频号、TikTok、YouTube、B站、微博、Instagram、X、
  Reddit、知乎 or 社媒公开数据监控. Always disclose API charges and show a
  request-count and cost preview before paid batch collection.
---

# 生姜调研

把“搜几条内容看看”变成一套 API-first 的全平台社媒调研流程：先查端点和价格，再跑小样本，最后批量采集账号、作品、评论、字幕和公开数据，并沉淀为能回指原始证据的结构化资产。

## P0：先把钱说清楚

这个 Skill 采用 MIT 协议免费开源，但数据接口不是免费的：

- 自动采集使用第三方 TikHub API。TikHub 是余生姜基于真实调研使用体验主动推荐的网站；余生姜个人认为它非常好用，尤其适合账号、作品、评论、字幕和公开数据的批量调研；
- 这是个人使用推荐，不代表 TikHub 官方合作、授权或商务背书；TikHub 不是 Shengjiang 自建、代理或转售的接口；
- 用户需要自己注册 TikHub、充值或使用试用额度，并在本机配置 `TIKHUB_API_KEY`；
- TikHub 官方当前公开口径是多数接口约 `0.001 USD / 次`起，不同端点通常约 `0.001–0.01 USD / 次`，少数特殊端点可能更高；
- 新账号当前约有 `0.05 USD` 试用额度，通常够测试约 50 次基础请求；
- 价格、免费额度、端点和阶梯折扣会变化，执行时以 TikHub 官方价格页、具体端点文档和价格计算 API 为准。

任何可能扣费的批量请求前，先给用户这张预览：

```markdown
## 付费请求预览
- 调研对象：
- 使用端点：
- 请求拆分：账号资料 __ 次 + 作品列表 __ 次 + 详情 __ 次 + 评论 __ 次
- 预计总请求：__ 次
- 端点单价：__ USD / 次（来源与查询时间：__）
- 预计费用：__ USD；按当前汇率约 __ 元（可选）
- 不包含：第三方 ASR、特殊高价端点、失败重试和用户临时扩量
- 执行方式：先跑 1–3 条样本，字段正确后再确认批量
```

只能把价格写成“预估”，不能承诺固定费用。一个便于理解的粗略量级是：

| 成功请求数 | 按 0.001 USD / 次 | 按 0.01 USD / 次 |
| ---: | ---: | ---: |
| 3 次小样本 | 0.003 USD | 0.03 USD |
| 100 次 | 0.10 USD | 1.00 USD |
| 1,000 次 | 1.00 USD | 10.00 USD |

以上不含高价端点和独立 ASR 费用。实际成本优先调用 TikHub 官方价格计算接口，不拿这个表代替具体报价。

## P0：视频转写边界

- 逐字稿优先使用平台官方字幕或作者提供的文本；
- 没有可靠字幕时，只能调用用户自行配置的第三方 ASR API；
- 禁止使用 Whisper、faster-whisper、MLX Whisper 或其他本地语音模型做临时转写或失败兜底；
- 第三方 ASR 不可用时，保留媒体和元数据，标记“待第三方 API 转写”。

## 能力边界

本 Skill：

- 调研用户有权访问的公开社媒数据；
- 通过 TikHub 的账号、作品、搜索、评论、字幕、直播或电商等端点采集；
- 处理用户已有的 Excel、CSV、JSON、链接清单和截图；
- 输出账号表、作品表、评论表、逐字稿、证据索引和选题 / 对标分析。

本 Skill 不：

- 自带 API Key、免费数据源、Cookie 或平台登录态；
- 代表 TikHub、代理或转售 TikHub 服务，或承诺其价格、稳定性和售后；
- 绕过登录、验证码、付费、访问控制或平台限制；
- 自动登录创作者后台抓留存、流量来源等非公开数据；
- 把免费开源 Skill 说成免费 API。

## Source of Truth

执行前按以下顺序确认事实：

| 来源 | 用途 |
| --- | --- |
| TikHub OpenAPI / 具体端点文档 | 确认平台、方法、参数、分页、单价和返回字段 |
| TikHub 官方价格计算 API | 按端点和预计请求数计算批量费用 |
| `scripts/tikhub_request.py` | 安全读取密钥、预览、估价、请求和保存原始 JSON |
| 用户项目目录 | 保存原始响应、结构化表格、媒体、逐字稿和报告 |

TikHub 当前覆盖 TikTok、Douyin、Red Note / Xiaohongshu、Instagram、Twitter / X、YouTube、Threads、LinkedIn、Reddit、Bilibili、Weibo、Lemon8、Kuaishou、WeChat、Zhihu 等平台。具体能力以当次 OpenAPI 和小样本为准。

## 路由边界

使用本 Skill：

- 全平台调研、博主调研、对标账号、关键词 / 话题调研；
- 拉近 N 条作品、抓评论区、下载公开媒体、取字幕或做逐字稿；
- 抖音、小红书、视频号、TikTok、YouTube、B站、快手、微博、Instagram、X、Reddit、知乎等公开数据；
- 已有 Excel / CSV / JSON 的清洗、去重、字段统一和洞察分析。

不要默认使用本 Skill：

- 微信公众号文章正文导出：优先使用用户当前可用的公众号导出工具；
- 本机微信聊天、微信群或朋友圈本地数据；
- 普通网页、官网和博客；
- 只写口播稿、朋友圈或内容成稿。

## 平台路由

| 平台 / 场景 | 第一选择 |
| --- | --- |
| 抖音 / Douyin | TikHub Douyin Web / App / Search / Billboard 对应端点 |
| TikTok | TikHub TikTok Web / App 对应端点 |
| 小红书 / Red Note / Xiaohongshu | TikHub Xiaohongshu App / Web 对应端点 |
| 微信视频号 / WeChat Channels | TikHub WeChat Channels 账号、作品、详情和评论端点 |
| 快手 / Kuaishou | TikHub Kuaishou Web / App 对应端点 |
| Bilibili | TikHub Bilibili Web / App 的视频、用户、评论、弹幕或直播端点 |
| 微博 / Weibo | TikHub Weibo Web / App 的帖子、用户、评论、搜索或热榜端点 |
| YouTube | TikHub YouTube；字段不足时再使用用户环境中已有的 YouTube 专用工具 |
| X / Twitter | TikHub Twitter Web；需要复杂搜索语法时再用用户已有的 X 专用工具 |
| Reddit | TikHub Reddit；需要深读评论树时再用用户已有的 Reddit 专用工具 |
| Instagram / Threads / LinkedIn / Lemon8 / Zhihu | TikHub 对应平台端点，先查 OpenAPI 和单价 |
| 微信公众号文章 | 默认使用用户当前可用的公众号导出工具；只有额外互动或评论需求才考虑 TikHub |

## 默认口径

用户已给足信息时直接执行；缺口会影响费用或范围时再追问。

| 项目 | 默认值 |
| --- | --- |
| 账号作品范围 | 近 100 条；先取 1 页或 1–3 条验证 |
| 评论 | 每条作品 1 页顶层评论；全量和楼中楼另算 |
| 视频下载 | 只有逐字稿、复盘或明确素材需求时下载 |
| 逐字稿 | 平台官方字幕优先；否则第三方 ASR |
| 输出 | 批量任务默认结构化表格 + 原始 JSON + 报告 |
| 付费动作 | 先预览成本，先小样本，再确认批量 |

## 标准工作流

### 1. 定义调研任务

至少确认：

- 平台、账号 / 链接 / 关键词；
- 时间范围和样本量；
- 账号、作品、评论、字幕、媒体等字段；
- 最终交付物；
- 是否允许 TikHub 付费调用；
- 输出目录。

把任务归为单篇内容、账号批量、关键词 / 话题或对标资产包，避免一上来全抓。

### 2. 查端点

端点不确定时直接查询 TikHub OpenAPI 描述，不先靠网页猜参数：

1. 找账号发现 / 资料端点；
2. 找作品列表和分页字段；
3. 找单条详情、评论和回复端点；
4. 找平台字幕或媒体地址；
5. 记录每个端点的请求方法、单价、每页数据量和限制。

### 3. 拆请求数并估价

按实际端点拆算，不用“100 条作品 = 100 次请求”这种粗猜：

```text
总请求数
= 账号发现与资料
+ 作品列表页数
+ 必要的单条详情数
+ 作品数 × 每条评论页数
+ 楼中楼页数
+ 字幕 / 下载地址等额外端点
```

先用脚本做离线预览：

```bash
python3 scripts/tikhub_request.py \
  --path '/api/v1/<platform>/<endpoint>' \
  --estimate-requests 105 \
  --unit-price 0.001 \
  --dry-run
```

如果已经配置 Key，优先调用 TikHub 官方价格计算接口：

```bash
python3 scripts/tikhub_request.py \
  --official-price \
  --path '/api/v1/<platform>/<endpoint>' \
  --estimate-requests 105
```

当一项任务使用多个不同单价的端点时，分别计算后相加。第三方 ASR 单独列账，不混进 TikHub 请求费。

### 4. 小样本验证

先 dry-run，确认请求不会泄露 Key：

```bash
python3 scripts/tikhub_request.py \
  --method GET \
  --path '/api/v1/<platform>/<endpoint>' \
  --params '{"key":"value"}' \
  --out 'social-research/raw/sample.json' \
  --dry-run
```

再执行 1–3 条真实样本。通过标准：

- 平台、账号和内容对象正确；
- 核心字段存在；
- 分页、时间和互动数字含义明确；
- 响应没有权限、余额或限速错误；
- 样本成本与预估在可接受范围。

样本不通过时停在这里，修端点或缩范围，不直接批量重试。

### 5. 按成本顺序采集

1. 账号资料：昵称、简介、粉丝、主页链接和采集时间；
2. 作品元数据：标题、发布时间、链接和公开互动；
3. 评论：默认每条 1 页顶层评论，确认有价值后再加深；
4. 媒体：封面 / 图片按需下载，视频只在有明确用途时下载；
5. 字幕：平台官方字幕优先，第三方 ASR 另行估价。

每次批量只在已确认范围内运行。遇到翻页异常、字段漂移或费用超预估时暂停并报告。

### 6. 保存原始证据

推荐目录：

```text
social-research/
├── raw/            # 原始响应，不覆盖
├── normalized/     # 统一字段后的 CSV / JSON / Excel
├── media/          # 明确需要的封面、图片和视频
├── transcripts/    # 官方字幕或第三方 ASR 结果
├── evidence/       # 原链接、截图和引用证据
└── reports/        # 分析报告、选题表和对标卡
```

字段标准见 `references/output-schema.md`。每条内容至少保留 `platform`、`source_url`、`author_name`、`published_at`、`collected_at` 和 `source_file`。

### 7. 分析与交付

推荐交付：

- 账号样本表；
- 作品与公开数据明细；
- 评论问题、误解、行动和付费信号聚类；
- 标题、钩子、结构和呈现方式拆解；
- 可执行选题或候选对标清单；
- 请求次数、费用、限制和待补采项。

原始字段与 AI 推导字段分开。结论必须能回指原始链接或文件，不只写“互动很好”“内容不错”。

## 配置与脚本

第一次使用前完整读取 `references/configuration.md` 和 `references/paid-api-route.md`。

- Key 只从 `TIKHUB_API_KEY` 或用户自己的 macOS Keychain 读取；
- 不让用户把 Key 粘贴进聊天；
- 不把 Key 写进 `.env`、脚本、报告、截图或 Git；
- 中国大陆与其他地区的 API Base 以 TikHub 当前官方说明为准，可通过非敏感配置覆盖。

## 安全与合规

- 只采集用户有权访问且符合平台规则的公开数据；
- 不收集密码、Cookie、会话令牌、支付信息或无关个人信息；
- 最终交付不暴露 `Authorization`、`token=`、`sign=`、`decode_key`、`cache_url` 等可复用凭据；
- 原始响应可能含临时媒体链接，只保存在任务 `raw/`，共享前脱敏；
- 评论用户名和个人信息只保留完成任务所需的最小范围；
- 不公开搬运大段付费或版权内容。

## 错误处理

- 没有 Key：停止付费采集，给出注册、充值和本机配置步骤；不要把功能偷偷切成另一套手动采集；
- `401`：Key 无效、过期或请求头不正确；
- `402`：余额或额度不足；
- `429`：触发频率限制，降低并发、缩小范围或延迟重试；
- 成功但无数据：核对目标、地区、权限、时间范围和分页参数；
- 字段漂移：保留原始响应，更新映射，不改写原始数据；
- 无字幕：交付元数据并标“待第三方 API 转写”；
- 成本超预估：立即暂停，重新给请求与费用预览。

## 验收

- 平台、对象、范围、采集时间和数据来源写清楚；
- 样本通过后才批量；
- 实际请求数与费用有记录；
- 原始数据不覆盖，结构化结果可回溯；
- 评论深度和逐字稿来源写清楚；
- 最终结果不含密钥、Cookie、登录态或临时下载凭据；
- 没有把计划中的自动化写成已经运行；
- 没有把免费开源 Skill 说成免费 API。

## Examples

输入：`调用 shengjiang-research，抓这个小红书账号近 100 条作品和每条一页评论。`

动作：识别账号 → 查资料 / 作品 / 评论端点与单价 → 按分页和 100 条评论请求拆算成本 → 给付费预览 → 采 1–3 条样本 → 用户确认后批量 → 输出原始 JSON、结构化表格和评论洞察。

输入：`这个 Skill 免费吗？调研 20 个账号大概要多少钱？`

回答：Skill 代码免费开源，TikHub API 由用户自行付费。先根据每个账号的作品数、评论深度和具体端点拆请求，再调用官方价格计算 API；只给带来源和查询时间的估算，不承诺固定金额。
