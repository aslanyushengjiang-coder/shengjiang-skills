# 资料与画像

先读用户提供的简历并列出现有事实。优先确认：毕业年月/适用招聘届别、实习或正式岗、
目标方向、可接受城市；只有影响筛选时再问专业学历、到岗时间等。
“秋招”是招聘季，不直接证明一定符合某一届；“2027届”和“2027年毕业”仍应与岗位具体毕业时间窗核对。
用户未定方向时，依据真实课程、项目、实习提出2–3个方向，解释依据和缺口，不擅自替用户决定。

使用 `assets/profile-template.json`，保留 `null` 或空数组代表未知。每个工作区仅存一位求职者。
字段：route、graduation_year、graduation_month、degree、major、cities、city_strict、job_keywords、timezone。
校招/实习/社招分别用 campus/internship/social，不能混为一个池。城市默认软偏好；只有用户明确排除其他城市，
才将city_strict设true。不自行填写期望薪资、照片、证件号码和工作许可。

事实库用 `facts` 数组：id、experience_id、text、source、confirmed。
每个经历独立experience_id；来自原简历可注明文件和段落，用户补充的注明本轮确认。
confirmed只表示来源已核对，不能由AI为虚构内容打标。

导入命令见数据约定。未经用户同意，不对原简历做覆盖修改，不上传到外部简历网站。
