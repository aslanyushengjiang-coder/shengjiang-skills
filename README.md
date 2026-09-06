# Shengjiang Skills

余生姜在真实业务中持续使用、测试和迭代的开源 AI Skills。

各Skill按使用场景独立命名。这里不收集“看起来很厉害”的提示词；每个 Skill 都必须来自重复发生的真实任务，有明确输入、执行边界、输出结果和自动化验收。

## 系列目录

| Skill | 解决什么问题 | 状态 |
| --- | --- | --- |
| [`shengjiang-knowledge`](skills/shengjiang-knowledge/) | 搭建个人 / 团队 / 自媒体系统知识库，接入已有资料，持续检查健康状态 | v0.4.0 |
| [`shengjiang-research`](skills/shengjiang-research/) | 用用户自己的付费 TikHub API 调研全平台账号、作品、评论、字幕和公开数据，执行前先算请求与费用 | v0.7.1 |
| [`Jiang-local-store`](skills/jiang-local-store/) | 实体门店菜品、菜单、活动海报与图文笔记；内置模板、参考图和图片API脚本 | v0.1.1；真实门店待验收 |

## Jiang-local-store｜实体门店 Skill

[下载单个Skill包](https://github.com/aslanyushengjiang-coder/shengjiang-skills/releases/download/Jiang-local-store-v0.1.1/Jiang-local-store.zip) · [使用说明](skills/jiang-local-store/README.md)

一个Skill入口，内置Image 2同步/异步调用脚本、三种SVG模板、四张完整示例预览和番茄牛腩风格参考。不需要另装电商Skill；已有图片可以直接填图和精确文字。

图片服务由使用者自行选择、配置和付费，本包不含Key。真实门店素材仍需独立验收；不自动操作外卖后台、发布图文或上线网站。完整图文排版与网站实现还需要宿主提供相应能力。

## shengjiang-research

`shengjiang-research` 是从余生姜本地长期使用的全平台调研 Skill 开源出来的 API-first 版本。

它能处理：

- 抖音、小红书、视频号、TikTok、YouTube、B站、快手、微博、Instagram、X、Reddit、知乎等平台；
- 账号资料、作品列表、单条详情、评论、字幕、公开互动和关键词搜索；
- 单篇内容、账号批量、话题调研、评论洞察、逐字稿和结构化表格；
- 端点发现、请求数拆算、费用预估、1–3 条小样本验证、批量采集和脱敏交付。

### 先说清费用

Skill 代码采用 MIT 协议免费开源，但 TikHub 是第三方付费 API：

- TikHub 是余生姜基于真实调研使用体验主动推荐的第三方 API 网站；我个人认为它非常好用，尤其适合账号、作品、评论、字幕和公开数据的批量调研；
- 这是个人使用推荐，不代表 TikHub 官方合作、授权或商务背书；Shengjiang 不自建、不代理、不转售 TikHub，API 服务、收费、稳定性和售后由 TikHub 负责；
- 用户自行注册、充值并配置自己的 `TIKHUB_API_KEY`；
- TikHub 官方当前公开口径是多数接口从 `0.001 USD / 次`起，不同端点通常约 `0.001–0.01 USD / 次`，少数特殊端点更高；
- 新账号当前约有 `0.05 USD` 试用额度，通常可测试约 50 次基础请求；
- 每次批量调研前，Skill 会先拆请求数、查询具体端点价格、给出费用预估，只跑 1–3 条样本，确认后再批量；
- 价格、免费额度和端点会变化，以 [TikHub 价格页](https://tikhub.io/pricing)、[接入指南](https://tikhub.io/getting-started)和具体端点文档为准。

粗略量级：

| 成功请求数 | 按 0.001 USD / 次 | 按 0.01 USD / 次 |
| ---: | ---: | ---: |
| 3 次 | 0.003 USD | 0.03 USD |
| 100 次 | 0.10 USD | 1.00 USD |
| 1,000 次 | 1.00 USD | 10.00 USD |

实际费用还取决于作品列表每页条数、是否逐条抓详情、评论页数、特殊高价端点和第三方 ASR。Skill 不承诺固定价格。

### 安装

适用于支持 [Skills CLI](https://www.npmjs.com/package/skills) 的 Agent 项目：

```bash
npx -y skills@latest add aslanyushengjiang-coder/shengjiang-skills \
  --skill shengjiang-research \
  -y
```

安装后可以直接说：

```text
调用 shengjiang-research，抓这个小红书账号近 100 条作品和每条一页评论。
先查 TikHub 端点和价格，拆算请求数与预计费用，只跑 1–3 条样本。

调用 shengjiang-research，调研这 20 个抖音账号。
Skill 免费和 API 付费要分开说明，批量前先给我费用预览。

调用 shengjiang-research，处理这份已有的社媒 Excel。
保留原始文件，清洗去重后生成账号、作品、评论洞察和选题。
```

### 配置

默认把自己的 Key 保存在 Skill 内的 `scripts/.tikhub_api_key`，首次保存一次即可：

```bash
python3 .agents/skills/shengjiang-research/scripts/tikhub_request.py --configure-local-key
python3 .agents/skills/shengjiang-research/scripts/tikhub_request.py --check-config
```

以后每次运行都会重新读取文件，文件优先于环境变量；只要 Skill 目录保留，换会话或清空环境变量都不需要重填。也支持任意路径的 Key 文件、Skill 根目录 `config.json` 中的 `api_key`、环境变量和 macOS Keychain，不限制保存位置。用户已经提供 Key 时，Agent 直接代存，不反复要求配置环境或确认保存方式。

公开代码包不预置真实 Key。迁移自己的 Skill 时带上 Key 文件或包含它的个人完整包；整个云电脑磁盘重置、重装时覆盖或删除了该文件，仍需从自己的备份恢复。

更多配置、估价和请求说明见 [`references/configuration.md`](skills/shengjiang-research/references/configuration.md) 与 [`references/paid-api-route.md`](skills/shengjiang-research/references/paid-api-route.md)。

## shengjiang-knowledge

![shengjiang-knowledge：输入、约束、执行、输出、反馈与进化的 Harness 闭环](skills/shengjiang-knowledge/assets/shengjiang-knowledge-harness.png)

> 你的文件不是知识库。只有当 AI 能稳定读到用户画像、当前工作、业务规则和原始事实，执行后还能接受检查、记录纠正并升级经验，它才是一套能运行的知识库。

它提供搭建、自媒体模式、资料接入、健康检查、修复和自我纠错六个工作流。

安装：

```bash
npx -y skills@latest add aslanyushengjiang-coder/shengjiang-skills \
  --skill shengjiang-knowledge \
  -y
```

## 开源标准

- 来自真实、重复发生的工作；
- 付费或外部依赖提前说清；
- 默认先预览，写入或批量扣费前确认范围；
- 原始事实、外部观点、用户判断和 Agent 提炼明确分层；
- 有清晰边界、自动化测试和可验证结果；
- 不把第三方 API、免费额度或私有连接器说成自建能力。

## 作者

余生姜（GitHub: [@aslanyushengjiang-coder](https://github.com/aslanyushengjiang-coder)）

## License

[MIT](LICENSE)
