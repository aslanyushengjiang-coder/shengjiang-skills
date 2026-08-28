# Jiang-local-store · 餐饮视觉 Skill

一个可下载的餐饮Skill：菜品主图、食品摄影风格、门头预览、菜单、海报、活动素材和推广笔记工作流，连同Image2接口脚本装在同一目录。

[下载Jiang-local-store.zip](https://github.com/aslanyushengjiang-coder/shengjiang-skills/releases/download/Jiang-local-store-v0.1.0/Jiang-local-store.zip) · [安装与配置](references/workbuddy-install.md) · [三种可填模板](references/builtin-templates.md)

## 包里有什么

| 内容 | 可用范围 |
| --- | --- |
| 12个餐饮视觉场景、10种食品摄影风格Prompt | 菜品身份、门店事实、价格活动与风格锁定；文字模板不等于每种风格已生成验收 |
| Image2同步与APIMart异步脚本 | 可本地预检；真实生图需自己的接口、Key、费用与素材授权 |
| 3种SVG模板、4份完整示例与PNG预览 | 填字、嵌入原图、受限节日换版；不靠模型生成价格和规则 |
| C端种草与B端品牌笔记工作流 | 内容、配图顺序与事实审核；指定归藏排版需宿主已有相应能力 |

解压后只有一个jiang-local-store目录、一个SKILL.md。Image2引擎已经在包内，不用再安装第二个Skill。安装方式以当前WorkBuddy版本实际提供的导入或目录机制为准；本包不声称已经在你的电脑安装或识别成功。

## 先做不扣费的小测试

在Skill目录运行：

    python3 scripts/image2_api.py edit --image assets/demo/dish-photo.png --prompt-file assets/demo/image-edit-prompt.txt --size 1024x1536 --dry-run
    python3 evals/test_builtin_templates.py

dry-run不调用真实服务；模板测试只写临时文件。配置示例在config，真实Key只能放私有配置或环境变量，不能提交到仓库。正式出图先核对供应商与费用，跑一张授权小样并看图，再扩量。

## 依赖与边界

Python 3.9或更新版本。PNG校验不需额外库；JPEG/WebP解码需宿主已有Pillow。PNG导出、浏览器、Flova、Guizang Social Card及建站能力不随此包安装；缺哪项就说明，不自动安装或静默换服务。

门头是预览，不是施工图。S12是网站素材，不是已上线网站。外卖排序、满减运营、表单、支付、订位和发布不由图片API自动完成。没有后台数据时不宣布哪张图转化更高。

图片均为虚构演示或风格参考，不能套成真实SKU或门店事实。AI图不能冒充真实顾客打卡、真实店面完工或活动效果。

## 目录

    SKILL.md                 唯一Skill入口
    references/              场景、事实锁、风格、接口与安装说明
    scripts/                 Image2/APIMart接口和SVG填充器
    config/                  无密钥的配置示例
    assets/templates/        SVG模板、可编辑字段、演示成品
    assets/demo/             明确虚构的测试素材
    assets/style-references/ 经授权随包提供的风格参考
    evals/                   行为用例定义与模板测试
    tests/                   本地loopback接口回归

自有代码与工作流文字按[MIT](LICENSE)提供；图片和第三方权利另见[NOTICE](NOTICE.md)。上游许可全文见[THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md)。来源与字节哈希见[PROVENANCE.json](PROVENANCE.json)。
