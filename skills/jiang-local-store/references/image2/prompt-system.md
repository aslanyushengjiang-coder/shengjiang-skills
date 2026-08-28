# Prompt 与一致性系统

每个任务先生成三层锁定，再组装单张 Prompt。三层锁定在同一套图中不得改写或摘要，避免商品和风格漂移。

## 1. Facts Lock

```text
Verified facts:
- Product: <商品名/型号>
- Audience: <目标用户>
- Verified parameters: <只列用户资料中的参数>
- Verified selling points: <只列可被资料支持的卖点>
- Package contents: <已知包装清单>
- Exact campaign facts: <价格/优惠/时间/售后>
- Unknown and forbidden to invent: <未知项>
```

评论、销量、限时、紧缺、认证、功效、保修年限和对比数据不得被自动补全。

## 2. Product Identity Lock

```text
Product Identity Lock:
Use the supplied product image as the authoritative subject reference.
Preserve the exact silhouette, proportions, materials, color, surface finish,
logo, label placement, controls, ports, vents, openings, seams, accessories,
and package count. Do not redesign, simplify, beautify, relabel, recolor,
mirror, add parts, remove parts, or turn it into another SKU.
```

根据真实商品再加 3–8 条可见特征，例如“前面双按键”、“顶部透明盖”、“右侧散热孔”。不从一张正面图臆测看不见的背面结构。

## 3. Campaign Style Lock

```text
Campaign Style Lock:
- Palette: <3–5 个色彩锚点>
- Background system: <统一背景类型>
- Lighting: <统一主光/辅光/冷暖>
- Typography mood: <字体气质，不指定未安装字体>
- Icon language: <线性/填充/立体>
- Layout density: <极简/中密度/大促>
- Image treatment: <写实棚拍/生活方式/编辑广告>
- Drift forbidden: no palette, lighting, typography, icon, or product changes
```

未给品牌风格时，使用品类默认：

- 小家电/数码：干净、冷静、技术感、充足留白。
- 美妆个护：洁净、柔光、精致材质、成分可视化。
- 食品饮料：温度感、真实食物质地、适度食欲感。
- 服饰鞋包：编辑棚拍、材质细节、真实人体比例。
- 家居母婴：温和自然光、可信、日常生活感。

## 4. 单张 Prompt 结构

使用下面结构，只保留对当前图有用的字段：

```text
Use case: ecommerce / <具体图型>
Asset placement: <平台 + 位置>
Primary request: <这张图的唯一主要任务>
Reference images: <Image 1 = authoritative product; Image 2 = logo; ...>

<Facts Lock>
<Product Identity Lock>
<Campaign Style Lock>

Scene/backdrop: <环境>
Subject and action: <商品怎么出现>
Composition: <主体位置、占比、镜头、留白>
Lighting and materials: <光线和质感>
Text verbatim: "<原样文字>"
Typography and placement: <文字层级与位置>
Constraints: <这张图必须保持什么>
Avoid: <明确不要的元素>
```

## 5. 文字策略

- 每屏默认只放 1 句标题 + 1 句支撑文字 + 必要参数。
- 必须原样渲染的文字使用引号包围，明确说“不得改写、翻译或增字”。
- 价格、优惠、型号、规格、日期和二维码旁文字优先后期叠加。
- 长参数表先生成无字底图，再用 HTML/SVG/图像编辑工具排版，不让模型自由填表。

## 6. 通用排除项

```text
Avoid: altered product geometry, invented controls or ports, changed logo,
fake certification marks, fake review stars, fabricated sales numbers,
unverified discounts, unreadable Chinese, random English filler, duplicate
products, floating accessories, warped hands, impossible reflections,
plastic-looking materials, excessive props, watermark, mockup labels.
```

根据图型删掉无关内容，不堆砌超长否定词。
