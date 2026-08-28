# APIMart 异步图片接口接入

当本机已有 APIMart 配置，或 WorkBuddy 需要使用 APIMart 的异步 `gpt-image-2` 接口时读取。该接口会先返回 `task_id`，再从 `/v1/tasks/{task_id}` 查询结果，不能直接套用同步的 `image2_api.py`。

## 私有配置

复制 `config/apimart.env.example` 到：

```text
~/.config/jiang-local-store/apimart.env
```

将权限设为 `600`。真实密钥不得进入 Skill、项目、Prompt、日志、压缩包或聊天。

本包只读取上述默认配置位置或用户显式指定的位置，不搜索个人历史配置。环境变量优先于配置文件。需要指定其他文件时设置 `APIMART_CONFIG_FILE`。

## 不扣费检查

```bash
python3 scripts/apimart_image.py doctor
```

只有 `ready=true` 才进入下一步检查；它不代表真实接口出图成功。`doctor` 不联网、不提交任务，也不显示密钥。

## 生成与参考图编辑

文生图：

```bash
python3 scripts/apimart_image.py generate \
  --prompt-file prompt.txt \
  --size 4:5 \
  --resolution 1k \
  --output-dir images \
  --name poster-v1
```

参考图编辑：

```bash
python3 scripts/apimart_image.py generate \
  --reference-image dish.jpg \
  --prompt-file prompt.txt \
  --size 1:1 \
  --resolution 1k \
  --output-dir images \
  --name dish-v1
```

最多 16 张参考图，单张小于 20MB。每次只生成 1 张；实体店首次测试只跑 1K 小样，通过主体一致性后再升分辨率。

## 能力边界

真实凭据只走可信 HTTPS；鉴权 API 的所有自动跳转均拒绝，必须直接配置最终端点。返回图片使用独立、无鉴权的 HTTPS 下载请求。

- `pending` 是正常排队状态，和 `submitted`、`processing` 一样继续查询当前任务。失败、取消或未知状态会停止；持续排队仍受超时限制。已取得 `task_id` 后，不因本地轮询报错重新提交生图，应先核对同一任务。状态定义见[官方任务文档](https://docs.apimart.ai/en/api-reference/tasks/status)。
- `image_urls` 同时承担参考图生成与编辑，不等于像素级保护。真实商品、菜品和门店仍需逐张验收。
- 当前适配器没有实现蒙版字段；需要像素级保护时，优先分层合成或改用已验证支持蒙版的执行层。
- APIMart 官方文档示例会在完成结果中返回实际 `cost`，但费用随模型、输入和分辨率变化。批量前重新查定价并先做 1 张。
- 参考图、Logo、Prompt、价格和未发布产品资料会发送给 APIMart，使用前核对数据留存和隐私政策。

官方文档：https://docs.apimart.ai/cn/api-reference/images/gpt-image-2/generation

## 本包位置与任务中断

本页命令在jiang-local-store目录运行，脚本见[apimart_image.py](../../scripts/apimart_image.py)，配置示例见[apimart.env.example](../../config/apimart.env.example)。同目录的image2_api.py提供共享图片校验，不能删掉。

CLI目前没有resume或status子命令。提交结果不明确或等待超时时，先保存task_id，由人工或另行验证的查询工具核对原任务；不要默认重发generate造成重复扣费。本包不保证中断恢复、计费结果或供应商模型身份。
