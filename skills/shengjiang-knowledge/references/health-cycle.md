# 知识库健康循环

> 用户要求健康检查、日常维护、定期巡检，或知识库发生结构变化时读取。

## 三层检查

### 每次会话：启动自检

确认入口链路真实存在并按顺序加载：

1. `AGENT.md / AGENTS.md` 或 `CLAUDE.md`
2. `system/SOUL.md`
3. `system/USER.md`
4. `system/PROCEDURES.md`
5. `INDEX.md`
6. `_本周.md`

如果 `system/state/latest-health.json` 存在，读取其中的 `generated_at`、`status` 和 P0 / P1 统计。超过 7 天未检查时，只提醒一次，不中断当前任务。

### 每周：确定性健康检查

先只读运行：

```bash
python3 scripts/audit_knowledge_base.py --root "<知识库路径>" --format markdown
```

用户要求保存本次状态，或已在知识库规则中授权周期性记录时，加：

```bash
python3 scripts/audit_knowledge_base.py \
  --root "<知识库路径>" \
  --format markdown \
  --save-state
```

这会更新：

- `system/state/YYYY-MM-DD-知识库健康检查.md`
- `system/state/latest-health.json`

### 结构变化后：变更验收

发生以下变化后立即再跑一次：

- 修改入口、导航或程序规则；
- 搬迁主要目录；
- 批量接入资料；
- 指定新的事实源或当前版本；
- 新增 Agent / Skill 入口。

## 状态解释

| 状态 | 含义 | 默认动作 |
| --- | --- | --- |
| `healthy` | 未发现确定性的 P0 / P1 | 继续使用，保留报告 |
| `attention` | 存在 P1 维护风险 | 不阻塞工作，安排确认与修复 |
| `critical` | 存在 P0，可能读错事实或暴露敏感信息 | 先处理 P0，再继续依赖该知识库 |

脚本结果只是线索。模板示例、合法归档、嵌套项目和有意保留的历史版本可能误报；修复前继续读取相关原始文件。

## 日常维护动作

- 收件箱超过 30 天：提醒归位，不自动删除。
- `_本周.md` 超过 14 天：确认是否仍代表真实优先级。
- 用户纠正：追加 `MEMORY_LOG.md`。
- 结构、规则或事实源变化：追加 `log.md`。
- 同类纠正反复发生：提议升级 `PROCEDURES.md` 或 Skill。
- 经验文件被引用且长期未更新：提醒确认有效性。
