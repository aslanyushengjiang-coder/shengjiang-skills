# 生姜爆款拆解 · shengjiang-viral-breakdown

拆解指定短视频或复盘自己的视频，输出观看价值诊断、开头与逐段推进、评论反馈、分镜、带时间戳的逐字稿，以及适合自身账号的方法。

## 安装

把这段话发给 WorkBuddy、Codex 或 Claude Code：

```text
请从 https://github.com/aslanyushengjiang-coder/shengjiang-skills 安装 skills/shengjiang-viral-breakdown，并读取 SKILL.md。需要通过视频链接采集素材时，同时安装同仓库的 shengjiang-research。完成后检查入口和参考文件是否能读取。
```

支持 Skills CLI 的环境也可以运行：

```bash
npx -y skills@latest add aslanyushengjiang-coder/shengjiang-skills --skill shengjiang-viral-breakdown -y
```

[下载独立 ZIP](https://github.com/aslanyushengjiang-coder/shengjiang-skills/releases/download/shengjiang-viral-breakdown-v1.0.0/shengjiang-viral-breakdown.zip)。手动安装时，将压缩包里的 `shengjiang-viral-breakdown` 文件夹放入宿主的 Skill 目录。

## 使用

```text
调用 shengjiang-viral-breakdown，拆解这条视频：[链接或本地文件]。分析观看价值、开头、逐段推进、评论和分镜，保留带时间戳的逐字稿，最后给出适合我账号的方法。
```

也可以提供已有文稿、字幕、截图或评论。材料不完整时，只交付有证据支持的部分；不会编造画面、评论或时间戳。

## 与自媒体调研配合

- `shengjiang-research` 负责搜索、作品详情、下载、评论和第三方语音转写。
- 本 Skill 负责深入分析指定作品。已有材料可以直接分析，不需要配置 API。
- 在线采集与转写可能产生第三方费用，按调研 Skill 先预览范围和费用，再根据授权执行。安装包不含密钥。
- 报告保存到自己的项目目录，不写入 Skill 安装目录。

## 方法来源与验证

方法参考润宇《如何拆解一条爆款短视频？》的公开文章和图示，来源及本地执行补充见 [来源说明](references/source-map.md)。本 Skill 不代表润宇官方产品，也不包含其内部提示词或课程 PDF。

[历史验收记录](evals/validation.md) 仅覆盖基于 PDF 的部分拆解；其余用例属于规则走查。发布打包检查不代表完整视频采集和分析已通过在线实测。复现历史评测需自行提供合法取得的原件。

本仓库编写的执行规则与模板采用 MIT 许可；引用作品及第三方材料权利归原作者。
