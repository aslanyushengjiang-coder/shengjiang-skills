---
name: jiang-hr
description: "Handles three evidence-backed HR workflows in one package: batch resume screening, recruiting funnel and report generation, and payroll reconciliation with anomaly checks. Use for 筛简历、候选人评分、招聘汇报、招聘漏斗、岗位进度、渠道对比、薪酬核算、绩效奖金 or 工资异常检查. Results support human review and never make automatic hiring or payroll decisions."
---

# Jiang HR

一套 Skill 处理招聘和薪酬中的三类常见任务。先根据用户提供的材料选择模式，只读取当前模式需要的参考文件。

## 模式选择

- 用户提供岗位 JD 和多份简历，或要求筛简历、候选人评分、二次筛选、横向对比：读取 [references/resume-screening.md](references/resume-screening.md)。
- 用户提供招聘平台导出、HR 台账或周报模板，或要求招聘漏斗、岗位进度、渠道对比、招聘周报：读取 [references/recruiting-report.md](references/recruiting-report.md)。
- 用户提供考勤、绩效、奖金规则或工资模板，或要求薪酬核算、绩效奖金、提成计算、工资异常检查：读取 [references/payroll-analysis.md](references/payroll-analysis.md)。
- 用户一次要求多个模式时，分开处理和交付；候选人资料与薪酬资料不要混在同一工作区或同一结果文件中。

## 共同规则

- 保留原始文件，在新文件或新工作表中生成结果。
- 每个判断、汇总和金额都保留原文、原字段或计算依据。
- 未提供的信息标记为“未提供”或“待确认”，不用常识或默认值补齐。
- 候选人筛选、招聘结论和薪酬结果必须由 HR 人工复核。
- 不自动联系、淘汰或录用候选人，不自动修改招聘系统，不自动发薪、报税或发送工资条。
- 候选人和员工数据属于敏感信息；只在用户授权的本地或受控环境中处理，对外分享前脱敏。

## 回复方式

- 在内部完成读取、核对和计算，对用户只呈现可直接使用的结论、结果表格、文件位置、异常项和待确认项。
- 不展示思考过程、分析步骤、计算推演、执行计划或逐步工作记录；计算依据放进结果文件的对应字段或公式中。
- 回复直接从结果开始，不先复述任务，不使用“已经完成”“已经做出来了”“我刚刚生成了”等过程性表述。
- 有异常时直接列出需要 HR 处理的事项；没有依据的内容仍标记“待确认”，不能为了直接给答案而补写数据。

## 交付要求

输出应当让用户看到“原始材料 → AI 处理 → 人工审核 → 可见交付”的完整链路。招聘汇报在用户未指定格式时默认交付带漏斗图的 Word；用户明确要求 Excel 时按 Excel 交付。薪酬分析未指定其他格式时，只交付 `薪酬核算.xlsx`，文件中只保留一个工作表 `薪酬汇总`，不生成 Word、PDF、HTML、图片、图表或其他文件。完成前检查文件数量、字段口径、公式错误、异常差额和待确认项。
