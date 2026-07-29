# 第三方付费 API 路线

## 这条路线是什么

自动采集通过第三方服务 TikHub 完成，不是 Shengjiang Skills 自建或转售的接口。

- 官方文档：https://docs.tikhub.io/
- API 控制台与接口文档：https://api.tikhub.io/

用户需要自行确认当前支持的平台、接口、额度和价格。官方规则可能变化，不在 Skill 中写死单价或承诺长期免费额度。

## 配置

在当前终端会话设置自己的 Key：

```bash
export TIKHUB_API_KEY="替换成你自己的Key"
```

不要把 Key 发到聊天、写进脚本、提交到 Git，或连同 `.env` 一起分享。请求使用官方规定的 Bearer Token：

```text
Authorization: Bearer <your_token>
```

## 小样本验证

先从 TikHub 官方文档找到目标接口、方法和参数。使用随 Skill 提供的通用请求脚本预览：

```bash
python3 scripts/tikhub_request.py \
  --method GET \
  --path /目标接口路径 \
  --params '{"示例参数":"示例值"}' \
  --out raw/sample.json \
  --dry-run
```

确认路径和参数后去掉 `--dry-run`，只请求 1–3 条样本：

```bash
python3 scripts/tikhub_request.py \
  --method GET \
  --path /目标接口路径 \
  --params @request-params.json \
  --out raw/sample.json
```

样本通过标准：

- 响应与目标平台、账号或作品一致；
- 核心字段存在；
- 时间、数字和翻页字段含义明确；
- 不含错误码或权限提示；
- 单次数据量与成本可接受。

通过后再向用户报告计划批次数和范围，获得确认后执行批量采集。

## 常见错误

- `401`：Key 无效、已过期或请求头不正确；
- `402`：账户余额或额度不足；
- `429`：触发频率限制，应降低并发、延迟重试或缩小范围；
- 接口返回成功但无数据：检查目标链接、内容权限、地区、时间范围和翻页参数；
- 字段与文档不一致：保留原始响应，按当前响应更新映射，并在报告中记录采集日期。

不要为了“跑通”而猜接口、伪造响应，或循环重试产生额外费用。
