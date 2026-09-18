# 本地数据约定与命令

Python3.9+，基础功能只用标准库。令SKILL_DIR为本包目录，DATA_DIR为用户授权工作区下的独立数据目录。
这些示例由Agent解析占位符后执行；不是让小白复制未替换的命令。

```text
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> init
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> profile set --file <profile.json>
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> profile show
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> jobs import --file <岗位表.csv或xlsx>
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> jobs list
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> jobs screen --as-of 2026-09-17 --out <工作区>/筛选结果
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> resume register --manifest <导出目录>/manifest.json
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> resume list
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> applications set --job-id <JOB_ID> --stage draft_filled --resume-id <RESUME_ID> --evidence-kind draft --evidence 已代填并回读，未提交
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> applications set --job-id <JOB_ID> --stage submitted --evidence-kind user_report --evidence 用户明确报告本人已完成提交
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> applications list
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> tasks add --title 准备一面 --due 2026-09-20T10:00:00+08:00 --job-id <JOB_ID>
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> tasks done --id <TASK_ID>
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> daily --date 2026-09-20
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> training save --file <training-summary.json>
python <SKILL_DIR>/scripts/jobctl.py --data-dir <DATA_DIR> training list
```

状态文件 `state.sqlite3`，版本1。records存结构化对象；events存简短写入事件，不存完整原文/回答。
每次写入在backups中先备份。此schema不是原版job-copilot，不能直接读原版库或声称无损迁移。
本CLI输出JSON，错误到stderr并非零退出。写入失败不得继续报成功。

岗位标准列：company、title、city、route、graduation_year、deadline、url、jd、source_type、verification、verified_at、source_quote。
row provenance与raw保留原输入。导入source_type/verification不代表新核验；将来对外引用还要查看证据和时间。
示例日期只用演示，实际命令应使用真实当前日期和用户所在时区。

多工作表导入范围：`jobs import --file 表.xlsx --sheets 岗位总表`，默认读取全部可识别岗位表。
