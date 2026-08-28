# 实体店视觉输入合同

在开始生成前读取。先提取已有材料，只补会影响真实性、可用性或精确排版的缺项。

## 1. 门店档案

```yaml
store_id: 门店唯一编号
store_name: 门店全名
category: 餐饮/美业/零售/培训/其他
address: 对外地址
business_hours: 营业时间
audience: 主要顾客
public_scope: 哪些资料允许公开
brand:
  logo: Logo 文件路径
  colors: 品牌色
  typography_mood: 字体气质
  existing_assets: 历史物料路径
  forbidden_elements: 禁用元素
space_refs:
  storefront: 门头照片
  interior: 室内照片
  wall: 要上墙的位置照片与尺寸
```

Logo、门头、室内和真实产品图属于核心资产。缺少时不要用通用占位图冒充这家店。

## 2. 菜单档案

每个菜品至少一个稳定的 `item_id`：

```text
item_id | category | name | spec | price | add_ons | featured | stock_status | image_path | portion | tableware | garnish | verified_ingredients | taste | spicy_level | allergens
```

- 菜名、规格和价格必须来自用户资料。
- 两组照片属于同一菜系，不代表来自同一家店或同一SKU。跨资料包使用时，必须有明确的item_id映射；不得按相似菜名自动迁用价格、份量或活动。
- 将每张输入图标为 `authoritative-dish`、`store-logo`、`style-only` 或 `demo-fixture`。审美参考只迁移构图、色彩、材质和光线，不迁移其中的食物、品牌或经营事实。
- 原料、辣度和过敏原只有明确提供时才使用。
- `image_path` 缺失时，只能生成概念图、拍摄清单或占位，不标记为真实菜品图。
- 售罄和库存是时效信息，生成前需要当轮确认。

## 3. 活动档案

```yaml
campaign_id: 活动编号
type: 开业/团购/节日/新品/日常促销
goal: 拉新/提高客单/推新品/清理库存/复购
featured_items: 主推 item_id
target_aov: 目标客单价
package_items: 套餐内容与数量
original_price: 原价
campaign_price: 活动价
start_at: 开始时间
end_at: 结束时间
valid_hours: 可用时段
blackout_dates: 不可用日期
reservation: 是否预约
stacking: 是否可叠加
refund: 退款规则
stores: 适用门店
cta: 真实行动入口
```

任何未知项都写 `unknown`，不得自动补“限量”“最低价”“最后一天”等促销事实。

## 4. 单次设计任务

```yaml
scene_id: S01-S12
placement: 外卖首图/墙面/桌面菜单/小红书/官网等
size: 实际像素或印刷尺寸
quantity: 数量
format: PNG/JPG/SVG/HTML/PDF
exact_copy: 必须原样出现的文字
image_mode: generate-scene/edit-preserve-dish/edit-preserve-space/composite
layout_mode: none/program-text/html-svg/website-handoff
change_set: 只允许修改的内容
protected_regions: 禁止变化的对象或区域
```

食品品牌图补充：原图优点与问题、`change_goal`（轻修/明显品牌化/风格探索）、可选质量参考、`style_id`、逐图构图与选法理由。具体字段和模板见 [食品品牌图判断流程](food-art-direction.md)。不把参考风格的菜品带入本次商品；用户没有指定配色时才采用模板示例色。实际支持比例、提交比例与输出像素分别记录，不能把请求值当成实测值。

## 最小开工条件

| 任务 | 最小材料 |
| --- | --- |
| 菜品主图 | 真实菜品图、菜名、用途、比例 |
| 门头预览 | 正面门头照、Logo、招牌文字、允许修改范围 |
| 活动海报 | 活动完整规则、主推菜真实图、Logo、尺寸 |
| 菜单 | 结构化菜单、真实菜品图、尺寸、品牌资产 |
| 节日换版 | 原设计、Change Set、Protected Regions、准确日期 |
| 网站资产包 | 门店档案、菜单、环境图、联系方式、桌面与手机用途 |

缺最小材料时，只交付材料清单、Prompt 或诚实占位，不进入可投放成品状态。
