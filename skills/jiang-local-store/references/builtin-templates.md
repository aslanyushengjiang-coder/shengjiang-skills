# 直接填字段的三种内置模板

Skill里已经放好SVG模板、填字段工具和实际演示实例。菜单、价格与活动文字走确定性文字层；菜品图片作为独立层嵌入，不让图片模型重画。新背景或菜品编辑是否调用Image2/API，仍由当前运行路由决定，这个填充器本身不调用任何服务。

## 先选哪一张

| 模板 | 适用任务 | 尺寸 | 已做好的结构 |
| --- | --- | --- | --- |
| [T01 上方留白海报](../assets/templates/top-space-poster.svg) | 活动说明、开业、新品；规则较多时另附规则页 | 1122×1402 | 复用S07背景＋原菜品照片卡；上方是店名、两行标题、优惠与四行规则，菜品层在下方 |
| [T02 确定性菜品照片卡](../assets/templates/dish-photo-card.svg) | 菜品介绍、菜单单品卡、数字菜单素材 | 1122×1402 | 大幅原照片完整显示；下方是菜名、规格、价格，菜品不裁掉或重绘 |
| [T03 精准节日换版](../assets/templates/festival-locked.svg) | 已确定设计的日期与背景颜色换版 | 1080×1350 | 复用节日SVG夹具的图层ID；菜品、标题、价格、Logo/店名和二维码受保护 |

完整引用清单在 [catalog.json](../assets/templates/catalog.json)。T01和T02复用已有[S07确定性合成](../assets/demo/campaign-composite.svg)，T03来自[节日换版夹具](../evals/fixtures/demo-national-day-poster.svg)。它们是通用SVG模板，不冒称归藏Social Card；完整小红书笔记仍按 `social-notes.md` 走对应排版路线。

用户提供的[番茄牛腩参考图](../assets/style-references/tomato-beef-brand-reference.png)只用于风格，`source_role=style-only`。随附实例是 `demo-fixture`，不是本期西餐成品。不能继承其中的菜品、品牌、价格或活动；先完成本期item_id映射与事实确认。

## 填字段，不手改整张海报

只需要Python 3标准库。命令在本Skill目录运行，图片路径相对于输入JSON文件。先复制相应 `*.input.json` 到本次项目或临时目录，再把来源文件、菜品、品牌色和精确文案替换成此次资料。

```sh
python3 scripts/fill_builtin_template.py render \
  --template top-space-poster \
  --data assets/templates/examples/top-space-poster.input.json \
  --output ./store-poster-demo.svg
```

另外两种把 `--template` 换成 `dish-photo-card` 或 `festival-locked`，`--data` 换成同名输入文件即可。每次输出SVG和同名 `.manifest.json`；已有输出不会被覆盖。

| 字段 | 怎么填 |
| --- | --- |
| `facts_source` | 事实表、菜单或已确认活动的来源说明；工具记录来源，但不替代事实核验 |
| `source_role` | 本SKU来源图只用 `authoritative-dish`；演示夹具用 `demo-fixture`；`style-only` 不得作为菜品源图 |
| `truth_status` | `fictional_demo`、`real_store_unverified` 或 `real_store_confirmed`；仍不代表已批准发布 |
| `truth_disclosure` | 图片中显示的真实性说明；虚构示例必须写出“虚构演示” |
| `dish_image` | 本SKU原图的本地PNG/JPEG路径；不接受网址或把风格参考当菜品 |
| `background_image` | T01专用的无菜品背景；本期已有合适背景可直接复用 |
| `brand_ink` 等颜色 | 已确定的 `#RRGGBB` 品牌颜色；实例颜色不自动成为本期品牌色 |
| 标题、菜名、价格、规则字段 | 从来源逐字填写。可选字段没有事实就删去或留空，不补猜测；必需字段缺失会阻塞 |
| `logo_image`、`qr_image` | T03可选的本地PNG/JPEG。未提供时不生成假Logo或二维码；店名文字不能算Logo完成 |

T01标题每行最多14字，四行规则每行最多34字。T02菜名最多16字。超出模板字数会报错，不会缩成小字或偷偷截掉规则；应缩短已有文案、换版式或另附规则页。图片采用 `meet/contain`，保留完整画面；不同长宽比可能留白，实际观感必须看导出图后判断。

## 只改春节日期与背景

先用T03填好一张源文件，再执行受限换版：

```sh
python3 scripts/fill_builtin_template.py revise-festival \
  --source assets/templates/examples/festival-locked.svg \
  --changes assets/templates/examples/festival-spring.changes.json \
  --output ./store-festival-spring.svg
```

`--changes` 只允许 `date`、`background_color`、`decoration_color`、`footer_color` 四项。修改价格、标题、Logo或二维码会被拒绝。工具逐层比较保护对象，并把相同比对结果写入manifest。图案重设计不在此命令范围内；需要换灯笼、装饰或构图时先建立单独Change Set，不能借改日期重做主体。

## 可以直接查看的实例

| 实例 | 输入与源文件 |
| --- | --- |
| 上方留白活动海报 | [字段](../assets/templates/examples/top-space-poster.input.json) · [SVG](../assets/templates/examples/top-space-poster.svg) · [PNG预览](../assets/templates/examples/previews/top-space-poster.png) · [状态](../assets/templates/examples/top-space-poster.manifest.json) |
| 菜品照片卡 | [字段](../assets/templates/examples/dish-photo-card.input.json) · [SVG](../assets/templates/examples/dish-photo-card.svg) · [PNG预览](../assets/templates/examples/previews/dish-photo-card.png) · [状态](../assets/templates/examples/dish-photo-card.manifest.json) |
| 节日原版 | [字段](../assets/templates/examples/festival-locked.input.json) · [SVG](../assets/templates/examples/festival-locked.svg) · [PNG预览](../assets/templates/examples/previews/festival-locked.png) |
| 春节日期换版 | [允许修改项](../assets/templates/examples/festival-spring.changes.json) · [SVG](../assets/templates/examples/festival-spring.svg) · [PNG预览](../assets/templates/examples/previews/festival-spring.png) · [保护层检查](../assets/templates/examples/festival-spring.manifest.json) |

以上全部是虚构回归样例，不能当作真实开业、团购活动或本期西餐菜单使用。T03示例没有真实二维码，也不提供可核销入口。

## 验证与交付状态

包内提供[12项离线回归测试](../evals/test_builtin_templates.py)：

    python3 evals/test_builtin_templates.py

测试覆盖三种模板填充、原图字节嵌入、文件移动后独立使用、精确文字与XML转义、缺事实/图片、超长文字、虚构标识、风格参考误用、来源角色、节日保护层及禁止改价。测试是否通过以本机实际运行结果为准。

包含4张完整PNG预览：T01/T02为1122×1402，T03两张为1080×1350。PNG是演示实例，不代表宿主已安装渲染器。新的填充输出仍须重新导出和看图，不能继承预览的验收状态。

T01规则在手机窄屏下偏小，真实移动端使用应另附规则页；不能直接记为手机可读性通过。全部示例是虚构资料，未获真实门店或印厂确认。印刷还需核对尺寸、出血、色彩与分辨率。

manifest分别记录源文件完成、导出、视觉检查、用户批准和发布。缺渲染器时只交付SVG；访问策略阻塞时不绕过限制。不把AI菜品图或风格参考升级为真实门店事实。
