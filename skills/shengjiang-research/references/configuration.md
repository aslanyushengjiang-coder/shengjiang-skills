# Key 保存与跨会话使用

默认把自己的 TikHub Key 保存在 Skill 内，保存一次，后续会话直接读取。公开代码包不预置真实 Key。

## 默认方式：保存在 Skill 内

在 Skill 目录运行：

```bash
python3 scripts/tikhub_request.py --configure-local-key
python3 scripts/tikhub_request.py --check-config
```

第一条命令接收输入，将 Key 保存到 `scripts/.tikhub_api_key`。这个文件是 UTF-8 纯文本，只放 Key 本身，不需要变量名、引号或 `Bearer` 前缀。也可以直接编辑该文件。用户已经提供 Key 时，Agent 直接代存并检查，不再要求用户输入一遍或改配环境变量。

每次运行都会重新读取文件，文件优先于环境变量；改完文件，下次运行立即生效。不会因为权限不是 `0600` 而拒读，也不强制修改已有目录权限。`--check-config` 只返回是否配置、来源和 API Base，不显示 Key。

## 自选位置与配置文件

不限制 Key 保存位置。临时指定任意文件：

```bash
python3 scripts/tikhub_request.py --key-file /path/to/my-tikhub-key --check-config
```

也可以把该位置作为保存目标：

```bash
python3 scripts/tikhub_request.py --key-file /path/to/my-tikhub-key --configure-local-key
```

未指定 `--config` 时，自动读取 Skill 根目录的 `config.json`；也可用 `--config /path/to/config.json` 选择其他 JSON。配置中可以直接保存 Key：

```json
{
  "api_key": "替换成你自己的 Key"
}
```

或者指定 Key 文件：

```json
{
  "local_key_file": "my-tikhub-key.txt"
}
```

配置中的相对路径按配置文件所在目录解析；`--key-file` 的相对路径按当前工作目录解析。自己的配置也可以放在 Skill 内并随目录一起复制。通用请求脚本和视频脚本都支持 `--config` 与 `--key-file`。

完整读取顺序：配置中的 `api_key` → `local_key_file` 指向的文件（默认 `scripts/.tikhub_api_key`）→ 旧 `.local/tikhub-api-key` → 环境变量 → macOS Keychain。显式指定 `--key-file` 时优先使用所选文件，忽略配置中的 `api_key`。

## 兼容已有配置

默认文件以外，继续支持旧的 `.local/tikhub-api-key`、`TIKHUB_API_KEY` 环境变量，以及用户自己的 macOS Keychain。已有可用配置不需要重填；默认方式仍是保存在 Skill 内，不要求使用环境变量。

macOS Keychain 默认使用服务名称 `tikhub-api`、账户名称 `tikhub`。明确不想读取钥匙串时，可以在当前命令设置 `TIKHUB_DISABLE_KEYCHAIN=1`。这些兼容方式不影响 Windows、Linux 或云电脑使用普通文件。

## 跨会话、迁移和更新

只要 Skill 目录保留，重启会话或清空环境变量都不影响已经保存的 Key。迁移到另一台电脑时，带上自己的 `scripts/.tikhub_api_key` 和所用的 `config.json`，或复制包含这些文件的个人完整 Skill 包。

更新 Skill 时保留自己的 Key 和配置文件，不用空模板覆盖。整个云电脑磁盘重置，或重新安装时删除、覆盖了这些文件，需要从自己的备份恢复；普通代码包不会自动找回已经被删除的个人文件。

## API Base

默认地址为 `https://api.tikhub.io`。如果 TikHub 官方对所在地区提供其他入口，在 `config.json` 中设置 `api_base`，或使用 `TIKHUB_API_BASE` 环境变量覆盖。其他可选配置见 `config.example.json`。

## 费用关系

- `shengjiang-research` 代码采用 MIT 协议免费开源；
- TikHub 是余生姜基于真实调研使用体验主动推荐的第三方 API 网站，余生姜个人认为它非常好用；
- 该推荐属于个人使用推荐，不代表 TikHub 官方合作、授权或商务背书；
- 社媒数据由第三方 TikHub API 提供，费用由用户直接向 TikHub 支付；
- Shengjiang 不自建、代理、转售或代充 TikHub API；服务、价格、稳定性和售后由 TikHub 负责；
- 批量任务仍需按当次端点、请求数和余额预览费用。

官方入口：[价格](https://tikhub.io/pricing)、[新手接入](https://tikhub.io/getting-started)、[API 文档](https://docs.tikhub.io/)、[API Explorer / OpenAPI](https://api.tikhub.io/)。
