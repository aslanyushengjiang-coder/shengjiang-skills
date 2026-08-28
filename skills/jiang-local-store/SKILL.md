---
name: jiang-local-store
description: >
  Prepares consistent local-store visuals, food brand photography and complete promotional notes. Use for 实体店生图、菜品图、食品品牌图、多风格食品摄影、门头、菜单、活动海报、餐饮小红书图文、C端种草笔记、B端品牌或老板笔记. Selects food styles from source photos and checks visible before/after improvements. Preserves dish identity, store facts, prices and offers. Uses task-level image2-api by default for teaching, preserves explicitly selected flova-production tasks, and routes note layout to Guizang Social Card. Does not provide construction drawings or automatically operate delivery platforms or deploy websites.
---

# Jiang-local-store

把同一家门店的定位、菜品卖点、活动规则和图片，转成菜品图、门头预览、菜单、活动视觉，以及标题、正文、图片顺序都配好的推广笔记。新教学任务默认 `runtime_profile=image2-api`；用户明确指定或已经保存为 Flova 的当前生产任务继续 `flova-production`。只在本次任务记录路由，不因教程默认值改变其他窗口或现有 Flova 项目。笔记排版走 `guizang-social-card-skill`；已有合适图片直接复用，不为排版重复生图。

## 必须遵守

1. 先读 `references/input-contract.md` 和 `references/lock-system.md`，把门店、菜品、空间、活动和原样文字分别锁定。
2. 真实菜品优先使用参考图编辑。实际对照发现菜品份量、块数、纹理、餐具或配菜漂移时，必须标记 `revise-dish`；需要严格保持菜品身份时，只让图片模型生成背景，再用原菜品照片做确定性照片卡、抠图或分层合成。没有真实菜品图时，只能交付概念图或拍摄清单，不能把纯生成图片当成真实外卖图。
3. 门头和室内只能交付效果预览，不能冒充施工图、尺寸图、结构图、消防图或审批通过方案。
4. 菜名、价格、日期、电话、地址、套餐数量、使用规则、二维码和过敏原不交给图片模型自由生成。先生成无字底图，再用 HTML、SVG 或确定性排版工具逐字叠加。
5. 只规划用户要求的资产。首次需要新图时，先记录本任务 `runtime_profile` 和图片供应商；`doctor` 通过只代表配置检查，不代表接口可出图。取得当轮费用与素材授权后，实际完成一张小样的请求、下载和身份验收，再扩展。只要求图文笔记时，不额外生成门头和海报。
6. A/B 版本只记录 `variant_id` 和测试假设。没有外卖后台真实数据时，不宣布哪个版本转化更高。
7. 图片 API、排版、网站、上传、印刷和施工是不同执行层。缺哪一层就明确交付到哪一步，不把 Prompt 包说成成图，不把网站资产包说成已上线网站。
8. API Key 只从本机私有配置或环境变量读取，不写入 Skill、项目、日志、提示词和聊天。
9. 食品品牌图先按 `references/food-art-direction.md` 看原图、选风格、写逐商品提示词，再看成图验收。圆弧只是十种风格之一；模板存在不代表该风格已经实跑，也不能承诺任意模型一次达到同样质量。

## 依赖与路由

| 任务 | 执行层 | 结果 |
| --- | --- | --- |
| 菜品、门店、活动场景生成与参考图编辑 | `image2-api` 复用包内Image2引擎；已指定 `flova-production` 时调用官方 `flova` | 图片或明确标记未执行的生成简报 |
| C端种草、B端品牌/老板图文笔记 | 本 Skill 负责内容与事实；`guizang-social-card-skill` 负责排版 | 标题、正文、有序图片、可编辑源文件和验收记录 |
| 菜名、价格、规则、电话、地址、二维码 | HTML / SVG / 确定性排版；已安装时可调用 `huashu-design` | 可核对的精确文字层 |
| 完整门店网站 | 网页能力；已安装时可调用 `huashu-design` 生成高保真页面 | 响应式 HTML 或网站交接包 |
| 网站上线、域名、表单、地图和后台 | 对应网站与部署能力 | 只有真实发布后才标记已上线 |

执行新图前读取 `references/runtime-routing.md`。`image2-api` 完整读取`references/image2/overview.md`、Prompt锁和对应API说明；`flova-production` 完整读取实际可访问的官方 `flova/SKILL.md`，沿用项目、上传、run和资源交付流程。做笔记前读取归藏 Social Card 的完整Skill和所选seed；依赖不可用时明确阻塞，不静默回退或另写一套模板冒称调用。Flova、归藏和建站能力都是宿主依赖，不因本包存在就算已安装。WorkBuddy接入见 `references/workbuddy-install.md`。

外卖菜单排序、满减组合、目标客单运营方案和完整网站实现需要相应业务或网页执行能力。S01/S06只覆盖菜品及菜单视觉，S12只覆盖网站资产；没有实际实现与验收时，不宣称本Skill已经包办这些流程。

## 工作流程

### 1. 整理输入

从用户已经提供的材料中提取，不重复询问。输入分四组：

- 门店档案：名称、品类、地址、营业时间、Logo、品牌色、门头和室内照片。
- 菜单档案：分类、菜名、规格、价格、加料、库存、真实菜品图、份量和摆盘说明。
- 活动档案：活动类型、主推菜、目标客单价、套餐内容、价格、日期、使用条件和适用门店。
- 单次任务：场景模板、用途、尺寸、必须原样出现的文字、允许修改和禁止修改的区域。

只有缺少会导致事实造假或主体漂移的材料时才停下来问。用户声称“已经提供”但当前任务没有可访问附件时，也必须停在 `blocked-missing-input`，不能按描述假定文件存在。完整字段见 `references/input-contract.md`。

### 2. 建立门店六层锁

按 `references/lock-system.md` 建立并原样复用：

1. `Facts Lock`
2. `Brand & Store Lock`
3. `Dish Identity Lock` 或 `Storefront / Space Lock`
4. `Offer Lock`
5. `Exact Copy Lock`
6. 精准编辑时的 `Change Set + Protected Regions`

同一套物料必须继续使用 `references/image2/prompt-system.md` 中的 `Campaign Style Lock`，避免每张图像不同门店。

### 3. 选择场景模板

从 `references/scene-prompts.md` 选择最小够用组合：

| ID | 场景 |
| --- | --- |
| `S01` | 外卖菜品主图 |
| `S02` | 菜单菜品卡 |
| `S03` | 门头招牌效果预览 |
| `S04` | 墙面海报与上墙预览 |
| `S05` | 纸质菜单 |
| `S06` | 数字菜单 / 外卖菜单 |
| `S07` | 开业活动 |
| `S08` | 团购套餐 |
| `S09` | 节日精准换版 |
| `S10` | 新品上市 |
| `S11` | 完整图文推广笔记：C端种草 / B端官方品牌或老板 |
| `S12` | 门店网站视觉资产包 |

所有模板首版状态均为 `pending-real-store`。只有真实授权门店完成输入、生成、排版和人工验收，才逐个升级验证状态。

选择 S11 时先读 `references/social-notes.md`。C端默认整桌打卡照与小店名标签；B端可按结构选择多种归藏排版，并在连续更新时保持账号风格。B端在这里指发布者是官方品牌或老板，不自动写成招商、代运营或卖课内容。连续更新复用同一套事实，换选题角度，不生成新的顾客经历、销量或活动。

### 3a. 复用已经做好的模板与参考图

需要菜单或海报成品排版时，先看 [内置模板说明](references/builtin-templates.md)，不要只返回提示词。包内有三种可填字段的SVG：T01上方留白活动海报、T02菜品照片卡、T03精准节日换版。使用 `scripts/fill_builtin_template.py` 填入本次的菜品原图与精确文字，再导出并看图检查；已有素材足够时，这一步不需要图片API。四个完整实例仅供演示，不能继承其中的品牌、价格和活动。纯食品摄影不强制套T模板；用户只要求Prompt或Skill时只做对应交付。

[番茄牛腩参考图](assets/style-references/tomato-beef-brand-reference.png)保留用户上传的原始字节，作为 `style-only` 参考。可借鉴奶油色与陶土橙、上方留白、下方菜品主体及暖光；不能把图中的面当作西餐SKU。品牌风格以本次输入为准，菜品按 `item_id` 匹配来源图。先读 [来源与用途](assets/style-references/README.md)，不要将风格参考填入 `dish_image`。

这三种模板用于菜单与海报，不冒称归藏Social Card，也不代替完整小红书笔记的内容和排版流程。

### 3b. 为食品品牌图选择摄影风格

涉及菜品、甜品、酒饮的品牌化或风格探索时，读取 [食品品牌图判断流程](references/food-art-direction.md) 和 [十种食品风格 Prompt](references/food-style-prompts.md)。先逐张看原图，记录优点、问题、可见身份和允许修改范围，再选一个 F01–F10 主风格；S 编号决定用途，F 编号决定摄影风格，T 编号仍是确定性排版模板，三者不互相替代。

每个商品留下简短选法依据、配色、构图和验收结果。用户要明显变化时，写清至少两项获准的场景或构图变化；用户只要轻修时不强制换背景。同一批保持品牌语言，不只替换菜名或把所有菜套成圆弧橙色。适配器若会扩写提示词，检查它没有改变商品数量、参考图角色和输出比例；不能读取扩写结果时如实记录。只要求模板或 Prompt 时不调用图片服务。

### 4. 建立资产清单

生成前建立 manifest：

```text
asset_id | scene_id | placement | goal | source_refs | exact_copy | ratio_or_size | runtime_profile | image_provider | image_mode | layout_mode | variant_id | status
```

一张图只承担一个主要任务。需要多比例时分别构图，不机械裁切。

食品品牌图在同一清单或逐图附页补充 `style_id`、`change_goal`、`visible_locks`、`selection_reason`、`requested_ratio`、`submitted_ratio`、`actual_pixels`、`expanded_prompt_check` 和 `visual_check`；字段说明见食品品牌图判断流程。实际文件尺寸必须读取，不能照抄任务描述。

### 5. 生成无字视觉

按 `references/runtime-routing.md` 执行本任务已经记录的路由。教学默认的 `image2-api` 调用包内同步Image2或异步APIMart适配器，不要求额外安装其他Skill；两者的协议、任务状态和验收分别记录。`flova-production` 只生成本次所需独立图片，沿用同一Flova项目和未完成run，不启动额外视频或重复提交。某一执行条件不可用时停在生成简报，不自动切换profile或供应商；已有图片仍可继续排版。

真实菜品、门头和空间用编辑模式；活动背景和纯氛围元素可用生成模式。若活动海报必须保留真实菜品的原始纹理和份量，先生成无菜品背景，再确定性合成原菜品层，不让模型重新摆放整碗菜。模型输出不得包含价格、电话、地址、日期、规则和二维码。

### 6. 叠加精确文字

对菜单、海报、团购和网站，用确定性排版层写入原样文字：

- 设计源文件优先为 HTML 或 SVG，方便逐字核对和后续改版。
- 印刷需求必须记录成品尺寸、出血、安全区、分辨率和颜色要求。
- 二维码只放用户提供的真实二维码图片；不能让模型画假二维码。
- 网站桌面端和手机端分别构图，不靠自动裁切。
- 图文笔记使用归藏 seed 的主题、字体角色和布局配方；可调整餐饮文字、图片占比和套餐信息行，但不得把自制模板冒称归藏原模板。

### 7. 验收与交付

逐张按 `references/qa-checklist.md` 验收，记录：

```text
pass | revise-dish | revise-space | revise-copy | revise-layout | revise-style | blocked-missing-input | blocked-missing-fact
```

只交付通过的资产。外卖后台上传、印刷、施工和网站发布保留人工确认。

## 示例触发

- “把这 8 道菜做成外卖主图，主推酸菜鱼，目标客单价 80 元。”
- “用这张门头照做日景和夜景两个招牌效果，门窗和隔壁店都不要动。”
- “把国庆海报换成春节版，只换装饰和日期，价格、菜品、Logo、二维码都不动。”
- “根据菜单表做一版纸质菜单和一版外卖菜单，所有价格必须逐字一致。”
- “这些菜的原图不错，做成品牌产品图，背景和构图变化明显，但别换菜、别全套圆弧。”

## 资源

- `references/input-contract.md`：门店、菜单、活动和单次任务的输入字段。
- `references/lock-system.md`：实体店六层锁。
- `references/scene-prompts.md`：12 个固定场景 Prompt。
- `references/food-art-direction.md`：逐图判断、风格选择、提示词组装、防改写与前后验收。
- `references/food-style-prompts.md`：10种食品摄影风格、适用边界、配色与可填参数的英文Prompt。
- `references/builtin-templates.md`：3种可填图、换字的SVG模板，4个完整实例与命令。
- `assets/style-references/`：用户提供的番茄牛腩风格参考原图、来源与用途边界。
- `scripts/fill_builtin_template.py`：离线填充模板、嵌入原图、受限节日换版与manifest。
- `references/runtime-routing.md`：图片 API、精确排版和网站执行路由。
- `references/social-notes.md`：C端与B端选题、口吻、配图、连续更新和完整交付规则。
- `references/workbuddy-install.md`：WorkBuddy 安装、私有配置和首次小样流程。
- `references/qa-checklist.md`：实体店视觉验收表。
- `assets/`：门店档案、菜单、活动和资产清单示例。
- `evals/evals.json`：门店视觉、精准换版、资料缺失、完整笔记、运行路由及食品风格判断的回归用例定义；定义存在不等于已经实跑。

- `references/image2/overview.md`：包内Image2/API引擎、配置、安全边界与本地预检。
- `assets/demo/`：供模板与测试使用的虚构示例图片，不是真实门店事实。
- `tests/test_image_adapters.py`：loopback协议测试，不调用真实供应商。
