# 投递进度与计划

状态：selected、draft_filled、ready_for_review、submitted、assessment、interview、offer、rejected、withdrawn。
其中前三项不计正式已投。submitted及真实招聘进展需user_report或receipt证据。
同公司多岗位按稳定job_id更新；不以公司名称模糊匹配第一条。误记用--correct和明确理由留痕，不静默回退。
没有收到通知，不推断被拒、进面或拿offer；“我准备去练面试”不改真实进度。

使用 `applications set` 存阶段、简历ID、证据类型与简短摘要。用户报告已在外部投递可注明未登记简历版本，
不能为了完善表格编造某个版本。receipt指实际查看的成功回执或官方通知；脚本本身不会自动读取邮箱。

任务用 `tasks add --title ... --due ...`，日期必须明确。面试钟点需带UTC offset，
例如2026-09-20T10:00:00+08:00；勿把招聘地和用户所在地的时区混淆。
只给日期可以存YYYY-MM-DD作为日级待办，不擅自补具体时间。相对“明天”先解析用户时区和当日日期。
任务完成用tasks done；日清单用daily --date。过期待办优先，其次已约定面试笔试，再安排可行投递。

本地待办没有推送能力。需要提醒时核查宿主定时工具，先确认通知渠道、时区和时间；
只在工具返回创建成功后说已开提醒。新建任务不会自行访问邮箱或Google Calendar。
