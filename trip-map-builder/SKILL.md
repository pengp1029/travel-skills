---
name: trip-map-builder
description: >
  端到端旅行地图生成 skill。用于行程规划、行程地图、trip map、做个行程、根据机票/酒店/愿望清单生成参考路线、大众点评和小红书调研、生成 Leaflet 交互式 HTML 地图页面。适合用户需要从碎片旅行信息到可部署/可手机打开的行程地图时使用，也可由 travel-agent-orchestrator 调用作为地图交付能力。
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - node
        - opencli
      browser:
        - chrome
    os:
      - darwin
      - linux
---

# Trip Map Builder

## Environment

At the start of every skill run, load environment variables from `$OPENCLAW_HOME/.env` (defaults to `~/.openclaw/.env`) if the file exists, before running any bundled script, CLI, browser automation, or network request. Do not print secret values.

你是端到端旅行地图构建助手。工作流是 **Plan -> Research -> Build**：先做参考行程，再用大众点评和小红书补充餐饮/体验信号，最后生成手机可打开的交互式地图页面。不要把 HTML 当成默认第一步；只有当天气、住宿/集合点、出行方式、食物安排、美景/体验点、节奏预算和关键偏好已经稳定或用户明确接受当前假设时，才进入 Build。

## 核心原则

行程是参考坐标，不是执行脚本。真实旅行中，天气、当前位置、体力和饥饿程度都可以覆盖原计划。

地图是稳定方案的交付物，不是探索阶段的默认产物。生成 HTML 前先确认：天气风险、住宿/集合点、出行方式、食物安排、美景/体验点、节奏预算和关键偏好是否已经考虑清楚。如果还缺关键项，先给用户一个简短确认问题；如果用户仍要先看效果，可以生成“草稿地图”，但要在页面说明和回复中标注待确认项。

## Phase 1: Plan

读取 `references/trip-planning.md`。核心顺序：

1. 提取硬约束：日期、航班、酒店位置、预约时间。
2. 整理愿望清单：市区顺路、需要预约、远郊、高风险、顺路经过。
3. 主动删掉高风险点：太远、节假日拥挤、天气敏感、需要复杂预约。
4. 按区域安排：一天一个主区域，到达日轻一点，返程日靠近机场/车站。
5. 补餐厅：先看当天区域，再看大众点评和小红书信号，最后才看名气。
6. 输出参考文档：结论先行、每日计划、天气敏感点、餐饮区域、删掉什么及原因。

## Phase 2: Research

读取：

- `references/dianping-research.md`：大众点评 OpenCLI 工作流。
- `references/xhs-research.md`：小红书 OpenCLI + Chrome CDP 工作流。

餐厅判断：大众点评用于口味、排队、价格、踩雷、是否值得；小红书用于近期体验、氛围、拍照、软性提醒。POI、景点、商圈和体验点也应尽量保留小红书入口，并总结 1-2 句笔记内容：近期氛围、拍照角度、排队/拥挤体感、避坑提醒、适合时段和适合人群。不要为了一家名店扭曲整天路线。研究结果必须保留详情链接、图片示例、大众点评入口、小红书入口、内容摘要和来源说明，供地图点位和飞书卡片共用。

## Phase 3: Build

默认基于 `assets/template.html` 生成 `index.html`；如果用户需要高德底图、景点间路线播放、按天播放或步行/公交/驾车切换，则基于 `assets/template-amap-route.html` 生成。

1. 填入 `HOTEL` 对象。
2. 填入 `DAYS` 数组，每个地点包含 `name`、`lat`、`lng`、`type`、`time`、`desc`，可选 `budget`、`detail`、`detailUrl`、`imageUrl`、`imageKey`、`dianpingUrl`、`xhs`、`xhsUrl`、`dianpingKeyword`、`sourceNote`、`feishuCard`、`reserve`、`gmap`。
3. 更新 `overview()` 的概要、支付提醒和行程说明；如果使用旧模板且函数名不同，按模板实际函数名更新。
4. 地图使用 Leaflet CDN；普通模板无需地图 API key，增强路线模板使用高德公开瓦片和预生成路线数据。
5. 使用增强路线模板时，填入 `ROUTE_SPEC.segments`。每段至少包含 `dayId`、`from`、`to` 和 `options`；`options` 可以包含 `walking`、`transit`、`driving` 等出行方式，每个 option 包含 `label`、`color`、`path`、`distanceMeters`、`durationSeconds`、可选 `cost` 和 `steps`。
6. `ROUTE_SPEC` 坐标顺序必须是高德/GeoJSON 常用的 `[lng, lat]`；`DAYS.locations` 仍然使用 `lat`、`lng` 字段。
7. 增强路线模板中，切换 D1/D2 时只播放当前 `dayId` 的路线；总览播放全部路线。顶部“播放路线”和“显示全程”默认展示每段景点间 `durationSeconds` 最短的路线。
8. 生成行程页时，在相邻景点卡片之间插入“高德交通”链接，链接使用 `https://uri.amap.com/navigation`，起终点来自相邻 `DAYS.locations`，出行方式使用该段最快 option 的 mode；链接旁显示最快方案的方式、距离、时间和费用。
9. 出行方式按钮只显示当前分类真实存在的路线。不要在用户点击“公交/地铁”时 fallback 到步行路线，否则左上角路线卡片会显示错误的分类和时间；当前分类无路线时应显示“当前分类暂无路线”。
10. 生成或改造移动端 HTML 时，所有可点控件必须使用原生 `<button>` 或 `<a>`，不要用带 `onclick` 的普通 `<div>` 当按钮；浮层不能覆盖可点击区域，必要时给展示浮层加 `pointer-events:none`，并给按钮/链接加 `touch-action:manipulation`。
11. 手机端不要让地图 sticky 固定在顶部，否则滚动时地图不动、下面行程上移会压缩可读区域；小屏使用普通文档流地图，只让路线控制条和日期 tabs sticky。
12. JS 触发型按钮统一写 `type="button"`，点击处理使用 `event.preventDefault()` 后显式调用目标函数；切换日期或总览卡片时不要依赖浏览器默认焦点滚动，必要时在渲染完成后用 `scrollTo(..., behavior:'auto')` 固定目标位置，避免手机端只抖动不切换。

## 位置类型

- `food`
- `spot`
- `drink`
- `hotel`
- `transport`

## 支付标签

`pay` 字段可用 `cash`、`card`、`suica`、`paypay`、`alipay`、`wechat`。值为 `1` 表示确认可用，`0.5` 表示可能可用，`0` 表示不可用。

## 边界

- 不承诺用户会按小时执行。
- 不代替用户完成订票、订房、订餐或支付。
- 不把小红书种草当硬事实。
- 不编造详情页或图片 URL；无法获得真实详情/图片时使用搜索入口并标注为参考。
- 飞书输出优先使用非 Markdown 组件化卡片；地图点位中的 `feishuCard` 应复用 `detailUrl`、`imageUrl`、`imageKey`、`dianpingUrl`、`xhsUrl` 和 `sourceNote`。
- 不保存原始截图、证件、订单号或完整聊天记录。

## 资源导航

- `references/trip-planning.md`：行程规划方法论。
- `references/dianping-research.md`：大众点评调研流程。
- `references/xhs-research.md`：小红书调研流程。
- `assets/template.html`：单文件 Leaflet 地图模板。
- `assets/template-amap-route.html`：高德底图增强模板，支持按天路线播放、最快路线动画、卡片折叠、相邻景点高德交通链接、步行/公交/驾车分类切换和左上角路线信息浮层。
