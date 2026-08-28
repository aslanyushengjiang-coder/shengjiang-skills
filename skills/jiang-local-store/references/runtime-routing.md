# 餐饮视觉运行路由

## 任务级选择

| runtime_profile | 使用条件 | 图片执行层 |
| --- | --- | --- |
| image2-api | 新教学任务默认，或用户明确选择Image2 API | 本包scripts/image2_api.py或scripts/apimart_image.py |
| flova-production | 用户明确选择Flova，或当前任务已有Flova项目且未要求迁移 | 宿主已安装的官方Flova能力 |

先读任务保存的选择，再读当轮指令。不能因安装或更新本包改变其他任务，不静默更换供应商。记录profile、供应商、参考图角色、费用授权与小样状态；不记录Key。已有合适图片直接排版，不为排版重复生图。

## 包内Image2引擎

先读[引擎说明](image2/overview.md)、[Prompt锁](image2/prompt-system.md)和所选接口说明。无需另装同级Skill。

| 协议 | 脚本 | 配置 |
| --- | --- | --- |
| OpenAI Images兼容同步接口 | [image2_api.py](../scripts/image2_api.py) | [同步配置](image2/relay-setup.md) |
| APIMart异步接口 | [apimart_image.py](../scripts/apimart_image.py) | [异步配置](image2/apimart-setup.md) |

两者协议不能混用。多个供应商配置同时可用而用户未选择时，不能自行决定花谁的钱。模型名只是请求参数，不能据此证明供应商真实底层模型。

doctor只做配置检查；dry-run只做本地请求构造检查，均不代表真实生成成功。取得当轮费用与素材授权后，只做一张实际小样，完成请求、下载、图片解码和菜品身份验收后再扩量。失败或依赖缺失时保留任务路线并报告阻塞，不静默换工具。

APIMart会返回task_id，但当前CLI没有resume或status子命令。超时、断网或提交状态不明时先保存task_id，由人工或另行验证的查询工具核对原任务；不能自动再次提交generate。

## 明确指定的Flova任务

Flova不是本包内置软件。只有宿主已安装并可访问官方Skill/CLI，且用户选择该路线，才按其官方流程工作。保留当前项目与未完成run，不额外启动视频、音频或重复生成。收费、上传和账户操作仍需当轮授权。一次Flova成功不能证明Image2 API成功。

## 完整图文笔记

先读[social-notes.md](social-notes.md)。本Skill组织选题、标题、正文、图片顺序、事实锁与C/B口吻；指定归藏排版时，需要宿主实际可用的Guizang Social Card与对应seed。上游来源：https://github.com/op7418/guizang-social-card-skill 。

本包不捆绑归藏Skill、浏览器或导出程序，也不把三个菜单/海报模板冒称归藏。依赖不足时明确交付内容稿与缺失项，不把未导出的HTML说成图片完成。访问策略阻止导出时停止，不绕过限制。

## 精确文字与网站

菜单、海报的确定性排版可直接使用[内置SVG模板](builtin-templates.md)，无需图片服务。价格、日期、规则、电话、地址、二维码均从用户事实填写，不让模型猜。

S12只提供网站视觉资产与内容规格。完整网站实现、上线、域名、表单、地图、支付或订位需要另行授权的网页能力。外卖菜单排序、满减组合和运营方案也不等同于图片生成；未实现的流程不能宣称已经包含。
