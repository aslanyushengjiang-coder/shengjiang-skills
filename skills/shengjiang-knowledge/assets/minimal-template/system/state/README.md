# system/state

保存知识库巡检报告和当前系统状态。

健康检查默认生成：

- `YYYY-MM-DD-知识库健康检查.md`：人读报告；
- `latest-health.json`：Agent 启动时读取的最新状态。

初始化时 `latest-health.json` 的状态为 `unknown`；首次健康检查后会被真实结果替换。

报告只记录路径、风险和建议，不保存密钥或敏感内容。
