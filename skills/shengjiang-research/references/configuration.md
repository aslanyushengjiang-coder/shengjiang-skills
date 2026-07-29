# 安全配置

这个 Skill 不包含真实 API Key。第一次使用付费采集前读取本文件。

## 费用关系

- `shengjiang-research` 代码采用 MIT 协议免费开源；
- 社媒数据由第三方 TikHub API 提供，费用由用户直接向 TikHub 支付；
- Shengjiang 不提供、转售或代充 TikHub API；
- 用户应在每次批量任务前查看 TikHub 当前价格和账户余额。

官方入口：

- 价格：https://tikhub.io/pricing
- 新手接入：https://tikhub.io/getting-started
- API 文档：https://docs.tikhub.io/
- API Explorer / OpenAPI：https://api.tikhub.io/

## 配置方式

优先在当前终端会话配置：

```bash
export TIKHUB_API_KEY="替换成你自己的 Key"
```

不要把 Key 发到聊天、写进 Skill、提交到 Git，或保存在共享 `.env` 文件里。

macOS 也可以使用“钥匙串访问”保存通用密码：

- 服务名称：`tikhub-api`
- 账户名称：`tikhub`
- 密码：用户自己的 TikHub API Key

Windows 和 Linux 使用用户级环境变量 `TIKHUB_API_KEY`。

配置后检查：

```bash
python3 scripts/tikhub_request.py --check-config
```

命令只返回是否配置、来源、变量名和 API Base，不显示 Key。

自动化测试或明确不想读取钥匙串时，可只在当前命令设置：

```bash
TIKHUB_DISABLE_KEYCHAIN=1 python3 scripts/tikhub_request.py --check-config
```

## API Base

默认地址是：

```text
https://api.tikhub.io
```

如果 TikHub 官方针对用户所在地区提供了不同入口，使用环境变量覆盖：

```bash
export TIKHUB_API_BASE="https://官方当前推荐的地址"
```

也可以复制 `config.example.json` 到个人目录后用 `--config` 指定。配置文件只能保存非敏感项。
