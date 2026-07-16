# yushengjiang-skills

余生姜在真实业务中持续使用、测试和迭代的 AI Skills。

这个仓库不收集“看起来很厉害”的提示词。每个 Skill 都必须来自重复发生的真实任务，有明确输入、执行边界、输出结果和验收方法。

## Skills

| Skill | 解决什么问题 | 状态 |
| --- | --- | --- |
| [`ysj-knowledge`](skills/ysj-knowledge/) | 把本地文件夹搭成 AI 能持续使用的知识库，并检查入口、索引、断链、版本与敏感文件风险 | v0.1.0 |

## 安装

把需要的 Skill 文件夹复制到当前 Agent 的 skills 目录：

```text
Codex 项目：      .agents/skills/ysj-knowledge/
Claude Code 项目：.claude/skills/ysj-knowledge/
```

长期逻辑只维护一份。需要同时支持多个 Agent 时，让其他入口指向同一份 `SKILL.md`，不要复制出多份长期维护版本。

## 使用

```text
/ysj-knowledge 帮我把这个文件夹搭成 AI 知识库。
/ysj-knowledge 检查一下这个知识库有没有断链、版本冲突或入口问题。
```

## 原则

- 先读现有资料，再决定结构。
- 先做最小可用版本，不预建一堆空目录。
- 导航负责指路，回答仍然回到原始文件。
- 自检默认只读；移动、覆盖、删除前必须让用户确认。
- 不把密钥、Cookie、浏览器数据或聊天数据库收进知识库。

## 作者

余生姜（GitHub: [@aslanyushengjiang-coder](https://github.com/aslanyushengjiang-coder)）

## License

[MIT](LICENSE)
