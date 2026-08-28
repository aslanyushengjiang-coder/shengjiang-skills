# GPT Image 2 中转接入

当千问办公、Claude Code 或其他宿主不能明确调用 GPT Image 2 时，使用本页。目标是让所有宿主共用同一套模型配置，不在每个平台分别保存 Prompt 和密钥。

## 中转站必须满足

- 使用 HTTPS。
- 能把指定模型名真实映射到 GPT Image 2，而不是同名替代模型。
- 兼容 OpenAI Images API：生成使用 `POST /images/generations`，编辑使用 `POST /images/edits`，或允许配置等价路径。
- 生成结果返回 `data[].b64_json` 或可下载的 `data[].url`。
- 编辑接口接受 multipart 图片字段；默认字段名为 `image[]`，可配置。

只提供 `/chat/completions` 的中转站不属于即插即用。先取得其 API 文档，再为其增加独立适配器，不要猜接口。

## 共享配置

复制 `config/image2.env.example` 到下面这个仅本机可读的位置：

```text
~/.config/jiang-local-store/image2.env
```

将文件权限设为 `600`。不要把真实密钥写进 Skill、项目仓库、Prompt、日志或聊天。环境变量优先于配置文件，适合临时切换中转站。

最小配置只有三项：

```text
IMAGE2_API_KEY=<本机填写>
IMAGE2_BASE_URL=https://relay.example.com/v1
IMAGE2_MODEL=gpt-image-2
```

如果中转站使用模型别名，例如 `openai/gpt-image-2`，只修改 `IMAGE2_MODEL`。如果路径或鉴权不同，再启用示例文件中的高级配置。

## 跨平台调用

- Codex：本包的image2-api路线运行包内API适配器，不因宿主具有其他生图工具而静默换供应商。
- 千问办公：读取本 Skill 后，使用终端/脚本能力运行 API 调用器。
- Claude Code：从同一规范路径读取私有配置并运行 API 调用器。
- 其他 Agent：只要能执行本地脚本或发起 OpenAI Images 兼容 HTTP 请求，就复用同一配置；否则只交付 Prompt 包。

宿主只负责组织任务和 Prompt，模型调用统一由中转层完成。

## 验证顺序

1. 本地检查，不产生生图费用：

```bash
python scripts/image2_api.py doctor
```

2. 中转商确认模型列表查询免费且接口可用时，再检查模型：

```bash
python scripts/image2_api.py doctor --probe-models
```

`target_model_visible=false` 不一定代表模型不可用，有些中转站不会在模型列表公开图片模型。此时以中转站文档和一张真实小样为准。

3. 首次只生成一张测试图。确认扣费、图片尺寸、中文能力和响应格式后，再执行多图任务。
4. 再测试带真实商品参考图的编辑接口。生成可用但编辑失败时，不得宣称参考图编辑已经可用，因为商品一致性依赖编辑能力。

## 安全与业务边界

真实凭据只走可信 HTTPS；鉴权 API 的所有自动跳转均拒绝，必须直接配置最终端点。返回图片使用独立、无鉴权的 HTTPS 下载请求。

- 商品原图、Logo、Prompt、价格和未发布产品信息都会经过中转商服务器。使用前核对数据留存、训练使用、删除机制和服务地区。
- 不使用来源不明、价格异常或无法确认真实模型的中转站处理客户保密素材。
- 不把中转站宣传页中的“支持 GPT Image 2”当成验证结果。模型名、生成接口、编辑接口和实际出图需分别验证。
- 批量任务前先确认单价、计费单位、失败请求是否扣费和图片存储期限。

## 常见错误

| 现象 | 先检查 |
| --- | --- |
| 401/403 | Key、鉴权 Header、前缀、账户权限 |
| 404 | Base URL 是否已含 `/v1`、生成/编辑路径 |
| model not found | `IMAGE2_MODEL` 是否为中转站要求的别名 |
| 生成成功、编辑失败 | 中转站是否真的代理 `/images/edits`、图片字段名 |
| 返回成功但没有文件 | 响应是否为 `data[].b64_json` 或 `data[].url` |
| GUI 中找不到环境变量 | 使用权限为 `600` 的共享配置文件 |


## 本包位置

本页命令均在jiang-local-store目录运行。配置示例见[image2.env.example](../../config/image2.env.example)，脚本见[image2_api.py](../../scripts/image2_api.py)。不要求安装另一个Skill。

默认doctor只检查本地配置，不是鉴权、余额、模型身份或出图验收。真实费用与素材授权齐备后，先完成一张小样。Windows等平台的配置权限行为须在本机确认；环境变量方式不要求复制配置文件，不自动放宽权限。
