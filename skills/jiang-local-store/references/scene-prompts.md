# 实体店固定场景 Prompt

先从 `lock-system.md` 建立锁，再把锁原样放到下面模板前面。所有模板首版状态：`pending-real-store`。图片执行先读 `runtime-routing.md`：新教学任务默认 `image2-api`，用户明确指定或已保存的Flova任务继续 `flova-production`，不静默回退、不改其他窗口。下列Prompt不代表对应接口或业务产物已经实跑。

通用前缀：

菜品、甜品、酒饮需要品牌摄影时，先读 [食品品牌图判断流程](food-art-direction.md)，从 [F01–F10风格库](food-style-prompts.md) 取一个模块填入 `Campaign Style Lock` 对应的视觉简报。S01–S12决定用途与信息结构，不预设所有食物都用圆弧背景。用途比例、真实品牌与保护区域优先；公共骨架中的精确文字锁仍由确定性排版执行。

```text
Use case: local store / <scene_id + 场景名>
Asset placement: <平台或真实位置>
Primary request: <这张图唯一要完成的任务>
Reference images: <Image 1 = 真实菜品/门头；Image 2 = Logo；...>
Task runtime profile: <image2-api 或已明确指定/保存的 flova-production>

<Facts Lock>
<Brand & Store Lock>
<Campaign Style Lock>
<Dish Identity Lock 或 Storefront / Space Lock>
<Offer Lock，如适用>
<Exact Copy Lock>
```

## S01 外卖菜品主图

```text
Primary request:
Turn the supplied real dish photo into one conversion-ready delivery-menu hero image. Preserve the dish exactly; improve only crop, background, lighting, steam and restrained supporting props.

Composition:
<1:1 或后台真实比例>. One dish only, fully visible, occupying 68–82% of the frame. Keep a clean thumbnail silhouette and believable camera angle. Use no text inside the generated image.

Food treatment:
Show realistic texture, temperature and moisture. Keep the exact portion, piece count, vessel, garnish and sauce. Do not add ingredients, enlarge the portion, duplicate the dish or replace the plate.

Variant plan:
Create separate assets, not a collage. V1 tests clean high-clarity product focus; V2 tests warmer appetite lighting; V3 tests a restrained real-table context. Assign a variant_id and hypothesis. Do not declare a winner without backend data.

Avoid:
floating ingredients, fake steam covering the food, altered plate, extra side dishes, unreadable text, price badge, delivery-platform logo, watermark.
```

## S02 菜单菜品卡

```text
Primary request:
Prepare one clean dish image area for a menu card using the authoritative dish photo. The generated layer contains the dish and background only; name, spec and price will be added later.

Composition:
Use <card ratio>. Keep the dish in the upper or left visual zone and reserve a deliberate copy-safe area. Match the store campaign palette and lighting.

Constraints:
Preserve dish identity. Do not render text, currency, badges, icons or QR codes. Do not redesign the food to fit the card.
```

## S03 门头招牌效果预览

```text
Primary request:
Create a storefront signage mockup on the supplied real storefront photo. Change only the approved signboard surface, logo placement, approved lighting and movable decoration.

Space preservation:
Preserve doors, windows, columns, wall openings, facade dimensions, neighboring storefront boundaries, street and fixed equipment. Do not widen the store, move structural elements or block exits.

Views:
Generate daylight and night-lighting variants separately. The sign wording itself may be represented by an empty sign panel or exact supplied logo asset; final Chinese store name is composited later if the model cannot preserve it exactly.

Text inspection:
For a generated concept storefront, inspect the entire frame—not only the main sign—for pseudo-text, labels and brand-like marks on neighboring windows, packages, equipment nameplates, air-conditioners and interior frames. Any pseudo-text is `revise-copy` and requires a targeted cleanup pass. For a real storefront edit, preserve authentic neighboring signage unless the user authorizes masking it.

Label:
Deliver as “门头效果预览，不是施工图或审批结果”.

Avoid:
changed architecture, invented floor, different neighboring shops, fake crowds, fake awards, construction dimensions, approval marks, random English, watermark.
```

## S04 墙面海报与上墙预览

```text
Primary request:
Create one poster background and one separate in-situ wall mockup using the supplied wall photograph. The poster background contains no exact campaign text.

Poster background:
Use the locked palette and one authoritative dish or product. Reserve a clear headline zone, offer zone and legal/rule zone. Keep the hierarchy readable from <观看距离>.

Wall mockup:
Place the approved final poster artwork onto the real wall with correct perspective, scale, lighting and shadow. Preserve wall fixtures, exits, switches and surrounding furniture.

Constraints:
All campaign copy, prices, dates, phone numbers and QR codes are added by deterministic layout before the wall mockup. Do not let the image model invent them.
```

## S05 纸质菜单

这类任务不让图片模型生成完整页面文字。图片模型只生成菜品图和少量装饰底图，最终菜单走 HTML/SVG 排版。

```text
Design brief:
Create a print-menu visual system for <成品尺寸、页数和装订方式>. Use the verified menu catalog and authoritative dish images. Establish category navigation, dish-card grid, featured-item hierarchy and a restrained brand background.

Exact layout rules:
Render dish names, specs, prices, add-ons, allergens and notes verbatim from the menu data. Keep one data row mapped to one menu item. Do not merge, rename or infer dishes. Reserve <出血> bleed and <安全区> safe margins.

Image request:
Generate only image backgrounds or dish crops without text. Final output must remain editable as HTML/SVG before print export.
```

## S06 数字菜单 / 外卖菜单

本场景负责菜单视觉与信息排版，不把菜单排序、满减组合、目标客单运营方案或后台文案的完整业务实现包含在内。

```text
Design brief:
Create a mobile-first digital menu using the verified categories and item data. Prioritize thumbnail recognition, category scanning, price clarity and featured-item visibility.

Layout:
Use one-column or two-column mobile cards according to the actual platform width. Dish images use S01/S02 outputs. Render names, specs, prices, sold-out status and add-ons through deterministic text.

Constraints:
Do not invent platform UI, sales numbers, review stars, discount labels or stock. Platform upload remains manual unless an authorized integration is available.
```

## S07 开业活动

```text
Primary request:
Create a grand-opening campaign key visual using the authoritative store, logo and featured dish references. Generate an energetic but brand-consistent background with deliberate copy-safe zones. Define one copy-safe region that no decoration may enter.

Composition:
One strong featured dish or storefront, one opening motif and generous space for exact headline, date, address, offer and CTA. Create platform-specific compositions separately.

Offer boundary:
Do not render or invent prices, dates, scarcity, giveaways, sales numbers or “lowest price” claims. Final offer text comes only from Offer Lock and is added later.

Dish preservation route:
If the real dish must stay exact, do not ask the image model to reposition or redraw the whole dish inside the poster. Generate a background-only asset with an empty photo/card or cutout zone, then place the authoritative dish photo as a deterministic image layer. A model-composited dish is concept-only until portion, piece count, vessel, garnish, color and texture are compared with the source.

Avoid:
generic red-gold overload unless it belongs to the brand, fake fireworks over food, fake crowd, fake review, random English, watermark.
```

## S08 团购套餐

```text
Primary request:
Create a group-buy package visual showing exactly the supplied dishes and verified package count. Use one composition that makes the included items easy to audit.

Inventory rule:
Every visible dish must map to one verified item_id and quantity. Do not replace dishes, add free items, enlarge portions or duplicate food. If a dish lacks a real reference image, use an honest placeholder and block final delivery.

Layout handoff:
Reserve exact zones for package name, original price, campaign price, validity, blackout dates, reservation, refund and applicable-store rules. All text is rendered deterministically.
```

## S09 节日精准换版

```text
Primary request:
Edit the supplied approved campaign artwork for <节日>. Apply only the Change Set. Preserve every Protected Region exactly.

Change Set:
- Replace only <背景装饰、节日色彩、日期等>

Protected Regions:
- Preserve the exact dish pixels, logo, price, QR code, layout grid, campaign terms and any region listed by the user.

Method:
If the image model cannot reliably protect these regions, generate a new background layer only and composite it behind the original protected pixels.

Reject if:
Any dish, price, logo, QR code, wording, position, size or package count changes.
```

## S10 新品上市

```text
Primary request:
Create one new-item launch visual from the authoritative new-dish photo. Make the dish immediately recognizable and connect it to the existing store campaign style.

Composition:
Use one hero dish, one restrained launch cue and one copy-safe area. Preserve the exact portion, plating and ingredients visible in the reference.

Text handoff:
Product name, launch date, price, availability and offer are added later from verified facts. Do not invent “limited”, “exclusive”, “sold out” or taste claims.
```

## S11 完整图文推广笔记

先读取 `social-notes.md`。由同一套门店资料选择 C端种草或 B端官方品牌/老板路线，交付主题、标题、正文、标签、有序图片与可编辑源文件。

已有图直接复用；新图按本任务profile走同级Image2/API适配器或已选Flova项目，不静默切换。排版用归藏 Social Card 的实际seed，允许餐饮场景微调；依赖缺失时标明待执行。不能把这里的业务简报当成图片模型生成整张带字海报的指令。

C端以口味、点单、适合谁为主，照片偏自然到店感；没有真实经历时写点单建议，不捏造顾客测评。B端以品牌、菜品和活动为主，视觉统一而克制；不自动变成B2B招商文案。

真实/AI/概念来源分开。完成HTML不等于导出；导出后实际检查手机可读性、菜品裁切、文字和规则，再报告验收状态。

## S12 门店网站视觉资产包

```text
Primary request:
Prepare a coherent visual asset pack for a responsive store website. Deliver separate desktop and mobile hero backgrounds, verified dish images, store-environment images and campaign modules.

Desktop:
Reserve 35–45% clean copy space and keep the store or featured dish on the opposite side.

Mobile:
Recompose vertically. Do not rely on automatic cropping of the desktop asset.

Text and site boundary:
Do not bake long copy, menu tables, address, phone, opening hours, map, form or CTA into the image. Those belong to HTML. This template produces website assets, not a deployed website.
```

## 使用纪律

1. 先匹配真实使用位置，再选模板。
2. 菜品、门头和空间按当轮授权先实际完成一张小样；doctor配置通过不能代替生成、下载和看图。全图查伪文字，真实菜品对照来源图查重绘。
3. 菜单、团购、海报和网站的精确文字永远后期排版。
4. 每次修改只改失败资产或图层，不重做整套。
5. 通过真实门店验收后，在本页为对应模板追加验证日期、样本类型、通过项和失败项；不要把概念图测试升级为真实门店验证。
