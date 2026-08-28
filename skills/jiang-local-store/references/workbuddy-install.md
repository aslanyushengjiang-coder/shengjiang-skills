# WorkBuddy接入与使用

## 安装一个Skill

下载并解压Jiang-local-store.zip，得到一个jiang-local-store目录。这个目录中只有一个SKILL.md，已包含菜品/门店规则、Image2脚本、接口说明、配置示例、SVG模板与演示素材；不需要另装电商Skill。

根据当前WorkBuddy版本实际提供的Skill导入或目录机制接入整个目录。不要只复制SKILL.md，也不要把一个指向作者电脑的桥接页当成安装包。导入后应实际确认宿主能读取references、scripts、assets和用户附件。本包未把某个未经验证的斜杠命令作为安装证明。

## 哪些能力在包内

| 能力 | 状态与依赖 |
| --- | --- |
| 门店事实、菜品身份、活动规则、12场景、10食品风格Prompt | 包内工作流与模板；不代表所有场景已实图验收 |
| 同步Image2 / 异步APIMart请求与本地预检 | 包内Python适配器；真实使用需自备所选供应商权限与费用授权 |
| 三种SVG模板、填字段、精确节日换版 | 包内离线工具；PNG/JPG导出另需宿主已有渲染器 |
| Flova | 用户明确选择时调用宿主已有官方能力；不随本包安装 |
| 归藏图文排版、浏览器导出、完整网站 | 需要宿主已安装并验证的相应能力；不随本包安装 |

Python 3.9或更新版本可运行包内脚本。PNG的图片校验使用标准库；JPEG/WebP实际解码需要宿主已有Pillow。缺依赖时明确报错，不自动安装、不自动放宽权限。

## 配置

同步接口先读[Image2配置](image2/relay-setup.md)，异步接口先读[APIMart配置](image2/apimart-setup.md)。示例只有占位值，不含Key。

默认私有配置位置：

    ~/.config/jiang-local-store/image2.env
    ~/.config/jiang-local-store/apimart.env

也可显式设置IMAGE2_CONFIG_FILE或APIMART_CONFIG_FILE。环境变量优先，不搜索作者的个人历史配置。不要把真实Key放进Skill、Git仓库、Prompt、聊天或日志。Unix配置文件须仅当前用户可读；其他平台先验证安全权限行为，可使用环境变量，不擅自放宽限制。

## 安装配置提示词

    请将jiang-local-store作为一个完整Skill接入当前WorkBuddy。
    实际确认能读取包内SKILL.md、references、scripts、assets和我的输入附件。
    本次新教学任务使用runtime_profile=image2-api，不改已有Flova任务。
    只使用我选择的供应商与本机私有配置。先运行--help与doctor。
    doctor只代表配置检查；未获费用与素材授权时，不发起生图。
    获得授权后仅做一张小样，完成下载、解码和菜品身份对照后再扩量。
    不上传、不发布、不充值，不把未执行步骤写成成功。

## 不扣费的输入预检

以下命令在jiang-local-store目录运行，使用随包虚构演示图，只检查本地输入，不创建远端任务：

    python3 scripts/image2_api.py generate --prompt-file assets/demo/image-edit-prompt.txt --size 1024x1536 --dry-run
    python3 scripts/image2_api.py edit --image assets/demo/dish-photo.png --prompt-file assets/demo/image-edit-prompt.txt --size 1024x1536 --dry-run
    python3 scripts/apimart_image.py generate --reference-image assets/demo/dish-photo.png --prompt-file assets/demo/image-edit-prompt.txt --size 4:5 --resolution 1k --dry-run

dry-run不需要Key，不发HTTP，不输出原Prompt、base64或Key。它仍会检查参数和图片数据。隔离测试时为子进程使用不存在的显式配置路径并移除实际API环境变量；不要修改用户全局配置。真实生成命令需要输出位置和当轮授权，见对应接口说明。

## 离线模板验证

    python3 scripts/fill_builtin_template.py render --template dish-photo-card --data assets/templates/examples/dish-photo-card.input.json --output ./demo-card-check.svg
    python3 evals/test_builtin_templates.py

输出位置由用户选择；已存在文件不会被覆盖。第一条使用虚构菜品，不是新门店成品。SVG中嵌入原图，移动文件后不依赖作者电脑。完成命令后仍须查看排版与手机效果；没有渲染器时只交付SVG，不声称已导出PNG。

## 可以直接使用的完整笔记提示词

    用我已提供的门店定位、菜单、卖点、活动和图片做两篇推广笔记：
    一篇C端自然种草，一篇B端官方品牌笔记，分别配齐标题、正文、标签、图片顺序与每页文字。
    不编造到店经历、评价、销量、价格和活动。已有图片直接复用。
    需要新图时按本任务已选profile与当轮授权执行，不切换供应商。
    指定归藏排版时先核实宿主已安装完整Skill及seed；缺失则报告，不冒称调用。
    导出实际图片并逐页检查后才计完成，不替我发布。

始终区分本地代码通过、真实供应商请求、WorkBuddy识别、视觉验收、用户批准与对外发布。外卖排序/满减运营、完整网站与上线不因本包有对应视觉素材而自动完成。
