# 知识库健康规则

## 检查频率

- 每次会话：确认启动入口和核心上下文已加载。
- 每周一次：运行确定性健康检查。
- 结构变化后：修改入口、搬迁目录或批量接入资料后立即复查。

## 执行命令

由 `shengjiang-knowledge` 调用自身的巡检脚本：

```bash
python3 "<shengjiang-knowledge 安装目录>/scripts/audit_knowledge_base.py" \
  --root "<知识库绝对路径>" \
  --format markdown \
  --save-state
```

脚本路径以 Skill 的真实安装目录为准，不要假定脚本位于知识库根目录。

## 状态处理

- `healthy`：继续使用。
- `attention`：存在维护风险，安排确认，不自动搬文件。
- `critical`：先处理 P0，再继续依赖该知识库。

修复前读取相关入口和原始资料，排除模板示例、合法归档和有意保留的历史版本。
