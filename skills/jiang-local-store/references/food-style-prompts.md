# 十种食品摄影风格模板

先按 [食品品牌图判断流程](food-art-direction.md) 选风格，再把公共骨架、一个风格模块和逐商品要求组合成完整 Prompt。这些是可直接填参数的文字模板，不是十套已经生成并验收的成图。模板状态统一为 `pending-generation`；真实门店验证另记。

## 快速选择

| ID | 风格 | 画面区别 | 适合的任务 |
| --- | --- | --- | --- |
| F01 | 圆弧色块品牌棚景 | 大弧面、两三种配色、纸或灰泥肌理 | 单品品牌海报、新品主视觉 |
| F02 | 纯色无缝棚拍 | 单色背景、干净轮廓、克制投影 | 连锁餐饮菜单、饮品、产品目录 |
| F03 | 暗调餐酒馆 | 深色空间、侧后光、保留暗部细节 | 烤制主菜、红酒、巧克力 |
| F04 | 自然日光餐桌 | 亚麻、浅木、柔和窗光、生活感 | 面包、早午餐、家常与轻餐 |
| F05 | 田园清新 | 浅绿、明亮空间、背景叶影 | 沙拉、蔬菜、果饮、轻食 |
| F06 | 俯拍编辑杂志 | 正交分区、平面秩序、疏密节奏 | 披萨、塔、扁平菜品；需要俯拍源图 |
| F07 | 法式甜品陈列 | 低饱和色、细腻纸面、小型展台 | 蛋糕、酥点、布丁、甜品新品 |
| F08 | 金属玻璃吧台 | 拉丝金属、清晰反射、冷暖分离 | 咖啡、气泡饮、鸡尾酒、精品饮品 |
| F09 | 新中式材质 | 木、矿物墙面、留白和斜向光 | 面、米饭、茶、小吃和中餐单品 |
| F10 | 复古直闪小馆 | 近距离、明确投影、漆面或细格餐桌 | 汉堡、三明治、薯条、休闲饮品 |

这是按视觉条件筛选的建议，不代表某类门店只能用某一种。所有风格都保留来源器皿；场景里出现的“陶瓷”“玻璃”是已有商品材质，不授权换碗换杯。每张只选一个主风格，示例色按真实品牌覆盖。

## 公共骨架：商品参考图编辑

下面占位项全部替换后再提交。`PRODUCT_REF` 与 `STYLE_REF` 是角色，不是固定附件编号。无风格参考时删除该行，使用所选模板，不虚构上传结果。

```text
Create ONE standalone, photorealistic food brand product image for {placement}.
Product ID: {item_id}. Requested canvas: {requested_ratio_or_pixels}.
PRODUCT_REF = {actual_attached_product_image}; this is the product identity reference.
STYLE_REF = {optional_actual_attached_style_image}; use it only for background structure, palette, light and spatial hierarchy. Do not transfer its food, vessels, ingredients, logos or wording.

{applicable_locks_verbatim_from_lock_system}
Visible identity details for this item: {visible_locks}.
Preserve these strengths of the source: {source_strengths}.
Approved changes only: {approved_changes}.

STYLE MODULE:
{one_F01_to_F10_module}

COMPOSITION:
{same_source_viewpoint_unless_another_view_is_authorized}; {subject_position}; {subject_scale_with_width_or_height_units}; {copy_safe_region_or_none}; {full_vessel_and_food_safety_margin}.
Apply {brand_palette_with_surface_assignments}. Match scene light and contact shadows to {source_light_direction_and_softness}.
Item-specific realism: {visible_material_details_and_preservation_checks}.
Keep food colors credible and distinct; preserve neutral highlights on white ceramics, genuine food texture and physically plausible glass and metal reflections.
Do not add food, enlarge portions, change vessel geometry, introduce unapproved edible props, or invent labels. Do not add steam or condensation unless explicitly permitted and compatible with the reference.
No generated text, logos, prices, badges, QR codes or watermarks. Preserve supplied authentic marks only as required by the locked source or later deterministic composition. No collage, fake luxury branding, neon food colors, plastic shine, blanket orange grading, halos or impossible shadows.
```

对于真实菜品，参考编辑不等于身份已保留；仍须按 [六层锁](lock-system.md) 看图核对。要求原始纹理和像素不变时用下面的背景层骨架。

## 公共骨架：只生成背景，原菜品后合成

```text
Create ONE empty photographic set for {placement}, canvas {requested_ratio_or_pixels}.
Generate the background and supporting surface ONLY. No food, dish, plate, bowl, cup, bottle, cutlery, text, logo, QR code or watermark anywhere.
{one_F01_to_F10_module_interpreted_as_empty_set_only}
Use {brand_palette_with_surface_assignments}. Match the camera perspective, light direction, softness and horizon to {source_photo_conditions}.
Leave {reserved_product_region} completely unobstructed for a separately composited original product photograph. Keep {copy_safe_region_or_none} quiet.
Materials should be tactile and believable. Do not draw a fake object-shaped shadow before the original object is composited; the final contact shadow will be fitted to the actual source silhouette.
```

使用此骨架时把模块中的“食物、盘、杯”转换成**未来合成对象的光线和位置要求**，不能让模型预生成主体。不能可靠匹配玻璃透光或抠图时，改用完整原照片卡，不用生成的近似食品补洞。

## F01 圆弧色块品牌棚景

- 适用：用户明确想要场景变化、品牌色和海报留白。
- 不适用：自然到店照片；不允许明显背景变化的任务。
- 配色候选：陶土橙／杏色／奶油白；钴蓝／黄油色；酒红／灰粉。只在没有既定品牌色时选一种组合，不全塞进一张。
- 构图：宽盘或碗放低位，高杯略偏侧；大曲线在背景，不沿食物轮廓描边。

```text
Build a tactile studio set from one broad asymmetric sweeping color plane and a second restrained complementary plane. Use matte colored paper or fine mineral plaster, with a believable meeting of the vertical backdrop and supporting surface. Let the large curve travel behind the product; keep it clear of the rim and silhouette. Leave an intentional quiet area instead of filling every gap with decoration. Use dimensional, soft-edged directional shadows matched to the source. The background colors carry the brand character while the food retains its own accurate reds, greens, browns and neutral highlights. Avoid concentric arch tunnels, floating pedestals, excessive ornaments and a uniform orange color cast.
```

## F02 纯色无缝棚拍

- 适用：强调产品识别度、系列统一、缩略图清晰；高杯和餐盘均可。
- 不适用：用户要求丰富生活场景时；透明或浅色商品与背景融在一起时需改色。
- 配色候选：深蓝、暖白、番茄红或墨绿中选一主色；依靠明暗而非多余装饰分层。
- 构图：保留完整轮廓与来源视角，空间紧凑或留白按用途确定。

```text
Use a single seamless matte brand-colored sweep with a subtle tonal transition between the background and floor. Create a deliberate separation between the product silhouette and the backdrop through matched illumination and a natural grounding shadow. Keep the set free of architectural curves, decorative slabs, loose ingredients and extra serving objects. Retain fine texture in the food and honest detail in the vessel; keep the background visually quieter than the product. Reflections should describe the existing object, never create a second one. Aim for precise, contemporary catalog photography with rich but controlled color, not a flat cutout on a digital fill.
```

## F03 暗调餐酒馆

- 适用：棕色烤制食物、红酒、深色甜品；原图本身有适合的方向光。
- 不适用：高调原片严格像素保护却又要求完全变暗；暗部已经无细节的来源。
- 配色候选：炭灰／酒红／少量暖木；禁止默认黑金、乱加烛火和酒瓶。
- 构图：同视角三分位布局；用亮暗关系突出主体，食物不沉入黑底。

```text
Create an intimate low-key restaurant campaign setting with a charcoal or deep wine-colored backdrop and a restrained dark wood or matte mineral surface. Shape the background with side light and controlled falloff compatible with the source illumination. Preserve readable shadow detail, the natural color of cooked surfaces and the transparent edges of existing glass. Use negative space and depth rather than additional bottles, candles, utensils or dramatic smoke. Keep the product brighter and more legible than its surroundings without artificial edge glow. Avoid crushed blacks, muddy brown food, fake gold accessories, oversized specular highlights and theatrical lighting that contradicts the source photograph.
```

## F04 自然日光餐桌

- 适用：早午餐、烘焙、面食与轻餐；品牌偏亲近自然。
- 不适用：把“明显变化”只做成几乎相同的米色桌面；未经许可增加一桌菜。
- 配色候选：亚麻白／燕麦色／浅木，加小面积品牌色；器皿不换成所谓手作陶瓷。
- 构图：保留原视角，背景只露少量餐桌信息；可用批准的素色餐巾，不补食物。

```text
Place the product within a believable daylight table setting using pale wood, softly textured linen and a quiet mineral wall. Keep the original vessel and camera angle. Match a broad window-like light source to the source photograph, with gentle transitions and a natural contact shadow. If approved, show only a small edge of unbranded linen away from the food. Preserve an effortless, inviting atmosphere with clear food texture and modest depth, rather than filling the table with styling props. Maintain neutral white balance and distinguish warm wood from the food's actual colors. Avoid yellow wash, rustic clutter, invented breakfast items and overly blurred food.
```

## F05 田园清新

- 适用：多色蔬菜、沙拉、果饮、轻食；用户希望清爽而鲜艳。
- 不适用：用花草暗示不存在的食材或产地；把绿色反光染到整盘菜上。
- 配色候选：鼠尾草绿／柠檬淡黄／瓷白；色彩由背景承担，菜品原色不漂移。
- 构图：空间明亮，叶影只落在背景；不增加果切、叶子或冰块。

```text
Create a fresh, airy set using pale botanical green and a restrained light citrus accent on matte surfaces. Suggest natural daylight through a soft leaf shadow on the empty background only; keep the product area clean and fully readable. Preserve the distinct existing colors and textures of vegetables or fruit, without adding leaves, flowers, citrus slices or additional produce. Keep whites neutral and glass transparent; prevent green spill from tinting the food. Use generous breathing room and realistic grounding. Avoid garden scenery that implies a specific farm, dew added to every surface, neon greens, excessive floral decoration and a generic wellness-advertising look.
```

## F06 俯拍编辑杂志

- 适用：来源就是俯拍，用户需要平面秩序、菜单专题或杂志感。
- 不适用：斜拍来源却要求主体不重绘；不把单品拼成虚构套餐。
- 配色候选：品牌主色／米白／墨色；仅使用平直矩形、细条纹或批准的织物边缘。
- 构图：一个完整盘或饼是视觉重心，不出现第二个商品；按画布边缘做网格。

```text
Design a true overhead editorial composition only from an overhead product reference. Use flat rectangular fields of matte paper or a restrained straight-edged table textile to organize the surrounding space. Place the unchanged product with purposeful asymmetry and a clear visual margin, balancing dense food detail against a quiet area. Keep shadow direction, scale and perspective consistent with the source. Allow a small approved non-food prop only if it supports the layout without implying another menu item. Use crisp planar geometry rather than curved arches or a fake three-dimensional stage. Do not invent an unseen top view, rearrange toppings, duplicate dishes or build a false meal assortment.
```

## F07 法式甜品陈列

- 适用：单件蛋糕、酥点、布丁、精致甜品；原图已有细腻层次。
- 不适用：把甜品改造成另一种形状；默认增加金箔、莓果、花瓣或糖粉。
- 配色候选：灰粉／奶油白，或浅灰蓝／可可色；不把所有甜品处理成苍白色。
- 构图：围绕原餐具陈列；小展台只有在视角和接触面能匹配时才使用。

```text
Build a refined patisserie display with finely textured pastel paper, a quiet plaster wall and, only when perspective permits, one low rectangular display surface beneath the original vessel. Use restrained tonal layering and soft directional light that reveals pastry layers, cream texture or chocolate reflections already present in the source. Keep delicate food colors accurate and give the product a clear visual center with ample negative space. The elegance should come from proportions, material detail and light, not added decoration. Do not add berries, gold leaf, flowers, powdered sugar, ribbons, branded boxes or new plates. Avoid milky haze, plastic frosting and highlights that erase surface detail.
```

## F08 金属玻璃吧台

- 适用：咖啡、透明杯饮料、鸡尾酒；有清晰的杯型和液面来源。
- 不适用：严格保留透明玻璃却没有可靠遮罩/合成条件；先退回完整照片卡。
- 配色候选：拉丝银／深蓝／一处暖色；金属冷色不改变饮料颜色。
- 构图：高杯竖向留足杯口、杯脚；反射对应同一杯，不生出另一杯。

```text
Use a precise contemporary bar set with a brushed stainless-steel supporting surface and a quiet colored background. Keep the surface reflection restrained, optically consistent and subordinate to the original drink. Let controlled highlights describe the existing glass rim, stem and liquid level without doubling edges or obscuring contents. Match the source light; separate cooler environmental reflections from the drink's accurate color. Reserve clean space beside the tall silhouette and keep the full vessel visible. Do not add ice, citrus, straws, foam, condensation, extra glasses or bottles. Avoid mirror-like duplicate products, liquid crossing the rim, melted glass geometry and neon nightclub lighting.
```

## F09 新中式材质

- 适用：中式面食、米饭、茶饮、小吃；也可用于材质相容的其他餐品。
- 不适用：把“中式”直接等同于灯笼、书法、龙纹和红金；擅自换餐具。
- 配色候选：深木／矿物灰白／朱砂小面积；按门店品牌调整，不默认喜庆促销。
- 构图：保留原碗盘和同视角，背景用材质与斜向光分层，不用圆弧棚景替代。

```text
Create a restrained contemporary Chinese dining setting through material and proportion: a quiet mineral wall, a carefully finished wood or matte stone surface, and one small brand-color accent. Preserve the original bowl, plate or cup exactly. Use measured negative space and a diagonal light transition compatible with the source, letting the food remain the most detailed and inviting element. Keep wood, ceramic and food visually distinct with accurate neutral highlights. Do not add calligraphy, lanterns, dragons, seals, chopsticks, tea sets or decorative ingredients unless specifically supplied and approved. Avoid stereotyped red-and-gold decoration, theatrical fog and rough textures that overwhelm the food.
```

## F10 复古直闪小馆

- 适用：休闲小馆、汉堡、三明治、饮品的活泼单品照；原片能匹配较硬光线。
- 不适用：柔光原图严格不重绘却要求硬闪；虚构真实顾客现场、手或人物。
- 配色候选：樱桃红／奶油白／深棕；可选低对比细格纹，不用抢眼大格抢主体。
- 构图：稍近但不截断商品；轻微不对称，保持完整盘杯和诚实份量。

```text
Create an energetic independent-diner product photograph using a restrained lacquered tabletop or fine, low-contrast checked surface with a plain background. Use a direct-flash character only when it matches the source lighting, with one believable compact cast shadow and crisp but controlled highlights. Keep the original food and vessel intact, appetizing and immediately recognizable. Allow a slightly off-center framing without cutting the product or exaggerating its size. Let the brand palette and confident framing provide the personality. Do not invent people, hands, receipts, logos, extra fries, drinks or evidence of a real customer visit. Avoid greasy blown highlights, distorted wide-angle food and artificially aged image damage.
```

## 填参示例：区别在判断，不在替换菜名

下面是提示词规划示例，未调用图片服务，也不是实际商品事实。

| 输入 | 选法与保留项 | 需要排除的做法 |
| --- | --- | --- |
| 原图是斜拍白碗面，用户喜欢番茄本色，要求品牌海报留白 | F01；保留碗、可见食物、原视角；两色纸面和低位构图形成变化；上方安静 | 不数出看不清的肉块，不把整幅风格图里的面移到别的商品 |
| 用户已确认饮料里有两片柠檬，要金属吧台风格 | F08；明确保留两片、同一杯型和液面；背景反射匹配原光线 | 不扩成“一或两片”，不多加冰、气泡或酒瓶；玻璃合成不可靠则保留照片卡 |
| 斜拍沙拉要原像素不变、自然清爽 | F05 同视角背景＋原图合成；叶影只在背景 | 不为了 F06 俯拍效果重绘沙拉，不加看似天然的菜叶或水珠 |
| 已批准品牌是深绿和米白，用户只说“大牌一点” | 先按用途与原图在 F02/F09 等相容方向中选一种；保留已批准颜色 | 不自动改成圆弧橙色，不凭“大牌”生成奢侈品牌 Logo |
