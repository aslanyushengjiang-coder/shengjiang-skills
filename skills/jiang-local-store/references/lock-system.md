# 实体店六层锁

每个任务先建立锁，再组装场景 Prompt。同一套资产中不得摘要或改写锁定内容。

## 1. Facts Lock

```text
Verified facts:
- Store: <门店名称与品类>
- Address and hours: <已核实地址与营业时间>
- Menu facts: <只列已核实菜名、规格、价格>
- Campaign facts: <只列已核实套餐、价格、日期、使用条件>
- Public scope: <允许公开的信息>
- Unknown and forbidden to invent: <未知项>
```

## 2. Brand & Store Lock

```text
Brand & Store Lock:
Use the supplied logo, brand colors, typography mood and existing materials as authoritative references. Preserve the exact store name, logo geometry, brand colors and required wording. Do not invent a second logo, English brand name, certification, slogan or branch information.
```

## 3A. Dish Identity Lock

```text
Dish Identity Lock:
Use the supplied dish photograph as the authoritative food reference. Preserve the exact dish type, portion, piece count, plate or bowl, tableware, garnish, sauce color, ingredient appearance and plating structure. Do not add ingredients, enlarge the portion, duplicate food, replace the vessel, make the food look raw when it is cooked, or turn it into another dish. Change only the approved background, crop, lighting and supporting props.
```

为每道菜再补 3–8 条肉眼可见特征。不从照片猜口味、原料、克重或制作方法。提示词中的“保持一致”不是通过证据；成图必须和来源图逐项对照。若主体被重新绘制，即使仍像同一道菜，也不能标记通过。

## 3B. Storefront / Space Lock

```text
Storefront / Space Lock:
Use the supplied storefront or interior photograph as the authoritative space reference. Preserve the exact doors, windows, columns, wall openings, ceiling height, floor line, neighboring storefront boundaries, street relationship and fixed equipment. Change only the approved signboard, surface finish, lighting, poster or movable decoration. Do not alter the building structure, block exits, expand the lease boundary or imply construction approval.
```

门头输出统一标注：`效果预览，不是施工图或审批结果`。

## 4. Offer Lock

```text
Offer Lock:
- Package contents and quantities: <原样>
- Original and campaign prices: <原样>
- Start/end dates and valid hours: <原样>
- Blackout dates: <原样>
- Reservation, stacking and refund rules: <原样>
- Applicable stores and CTA: <原样>
- Forbidden: no invented scarcity, sales number, lowest-price claim, hidden condition or fake review.
```

## 5. Exact Copy Lock

```text
Exact Copy Lock:
The following strings must be rendered verbatim by a deterministic text layer, not by the image model: <菜名、价格、日期、电话、地址、规则、二维码旁文字>. Do not rewrite, translate, abbreviate, add punctuation or infer missing copy.
```

图片模型生成的底图默认不含这些文字。

## 6. Change Set + Protected Regions

精准编辑时必须写：

```text
Change Set:
- Change only: <允许修改的内容>

Protected Regions:
- Preserve exactly: <菜品、Logo、价格、二维码、门窗、版式等>

Reject if:
- Any protected object, text, size, position, color or count changes.
```

保护区域可以是语义对象，也可以是用户提供的像素坐标或蒙版。若执行层不能可靠保护，就改走确定性合成，不让模型重画整张图。真实菜品需要像素级或照片级保留时，优先生成背景层，再把来源菜品图作为独立图片层放入；不能用“看起来差不多”代替主体保护。
