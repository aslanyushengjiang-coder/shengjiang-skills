# ysj-knowledge

把本地文件夹变成 AI 能持续使用的知识库，并对入口、导航、版本、断链和敏感文件做只读检查。

## 两个核心动作

### 搭建

```text
/ysj-knowledge 帮我把这个文件夹搭成知识库。
```

Skill 会先扫描现有结构、说明准备修改什么，得到确认后再创建入口、导航、记忆、规则和当前工作文件。

### 自检

```text
/ysj-knowledge 检查一下这个知识库。
```

Skill 会检查：

- Agent 入口是否完整；
- `AGENT.md / AGENTS.md` 是否一致；
- `INDEX.md` 和主要入口是否存在失效路径；
- 是否有多个“最终版 / 最新版”造成冲突；
- 收件箱是否长期积压；
- 是否混入密钥、Cookie 等敏感文件；
- 主要目录是否没有进入导航。

## 脚本

预览最小知识库初始化：

```bash
python3 scripts/init_knowledge_base.py --root /path/to/knowledge-base --name "我的知识库"
```

确认后执行：

```bash
python3 scripts/init_knowledge_base.py --root /path/to/knowledge-base --name "我的知识库" --apply
```

只读巡检：

```bash
python3 scripts/audit_knowledge_base.py --root /path/to/knowledge-base --format markdown
```

## 边界

- 初始化脚本不覆盖已有文件。
- 巡检脚本不读取密钥内容，也不会修改知识库。
- 脚本只负责确定性检查；目录职责、权威版本和业务判断仍需 Agent 读取原始文件后确认。
