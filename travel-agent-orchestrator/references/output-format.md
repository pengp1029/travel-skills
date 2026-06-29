# Output Format

## General Recommendation Contract

Every user-facing recommendation for a scenic POI, restaurant, shop, district, activity, route stop, or map point should preserve structured card fields when available:

- `name`
- `subtitle` or area/type summary
- `summary`
- `detail_url`
- `cover_image_url`
- `image_url`
- `dianping_url`
- `xhs_url` or `xhs_intro_url`
- `image_search_url`
- `amap_navigation_url`
- `source_note`
- `card`
- optional `feishu_card`

Do not invent detail or image URLs. If a real detail page or image URL is unavailable, use a search entry and say so in `source_note`.

## Feishu Card Output

This is the primary output path for Feishu channel recommendation responses. Do not use Markdown tables as the main recommendation format in Feishu.

When recommendation JSON is available, use the scripted renderer as the source of truth:

```bash
python3 ~/.openclaw/skills/travel-skill/scripts/render_feishu_card.py --input recommendation.json --mode card
python3 ~/.openclaw/skills/travel-skill/scripts/render_feishu_card.py --input recommendation.json --mode channel-data
python3 ~/.openclaw/skills/travel-skill/scripts/render_feishu_card.py --input recommendation.json --mode fallback-text
```

- `--mode card` returns a Feishu schema 2.0 card.
- `--mode channel-data` returns `{ "channelData": { "feishu": { "card": ... }}}` for native Feishu card delivery.
- `--mode fallback-text` returns plain non-table text with the same detail, source, image, and navigation links.

For Feishu channel output or when the user asks for a card, prefer non-Markdown interactive cards. Use component-style UI first:

- `plain_text`: titles, labels, short summaries, source notes.
- `img`: cover image only when a valid Feishu `img_key` is available.
- `button`: source and navigation actions.
- `action` or `column_set`: button groups.
- `hr`: separate content and actions.

Markdown is only a fallback for long lists or when the current renderer does not support a needed component. If direct image rendering is unavailable, use a `图片示例` button that opens `image_url` or `image_search_url`.

### Feishu Card: Single Recommendation With Image Key

```json
{
  "schema": "2.0",
  "config": {"width_mode": "fill"},
  "header": {
    "title": {"tag": "plain_text", "content": "{{name}}"},
    "template": "blue"
  },
  "body": {
    "elements": [
      {
        "tag": "img",
        "img_key": "{{cover_image_key}}",
        "alt": {"tag": "plain_text", "content": "{{image_alt}}"}
      },
      {"tag": "div", "text": {"tag": "plain_text", "content": "{{subtitle}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "推荐理由：{{summary}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "亮点：{{highlights_text}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "提醒：{{risk_notes_text}}"}},
      {"tag": "hr"},
      {
        "tag": "action",
        "actions": [
          {"tag": "button", "text": {"tag": "plain_text", "content": "看详情"}, "type": "primary", "behaviors": [{"type": "open_url", "default_url": "{{detail_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "大众点评"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{dianping_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "小红书"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{xhs_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "导航"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{amap_navigation_url}}"}]}
        ]
      },
      {"tag": "div", "text": {"tag": "plain_text", "content": "{{source_note}}"}}
    ]
  }
}
```

### Feishu Card: Single Recommendation Without Image Key

Use this when only an external image page or image search entry is available.

```json
{
  "schema": "2.0",
  "config": {"width_mode": "fill"},
  "header": {
    "title": {"tag": "plain_text", "content": "{{name}}"},
    "template": "blue"
  },
  "body": {
    "elements": [
      {"tag": "div", "text": {"tag": "plain_text", "content": "{{subtitle}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "推荐理由：{{summary}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "提醒：{{risk_notes_text}}"}},
      {"tag": "hr"},
      {
        "tag": "action",
        "actions": [
          {"tag": "button", "text": {"tag": "plain_text", "content": "图片示例"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{image_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "看详情"}, "type": "primary", "behaviors": [{"type": "open_url", "default_url": "{{detail_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "大众点评"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{dianping_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "小红书"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{xhs_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "导航"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{amap_navigation_url}}"}]}
        ]
      },
      {"tag": "div", "text": {"tag": "plain_text", "content": "{{source_note}}"}}
    ]
  }
}
```

### Feishu Card: Recommendation Overview

For multiple recommendations, avoid a long Markdown list when possible. Send one overview card plus separate cards for the top recommendations.

```json
{
  "schema": "2.0",
  "config": {"width_mode": "fill"},
  "header": {
    "title": {"tag": "plain_text", "content": "{{city}} 推荐方案"},
    "template": "green"
  },
  "body": {
    "elements": [
      {"tag": "div", "text": {"tag": "plain_text", "content": "结论：{{conclusion}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "推荐顺序：{{ranked_names_text}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "选择逻辑：{{decision_reason}}"}},
      {"tag": "hr"},
      {
        "tag": "action",
        "actions": [
          {"tag": "button", "text": {"tag": "plain_text", "content": "查看地图"}, "type": "primary", "behaviors": [{"type": "open_url", "default_url": "{{map_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "图片合集"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{image_collection_url}}"}]}
        ]
      },
      {"tag": "div", "text": {"tag": "plain_text", "content": "{{source_note}}"}}
    ]
  }
}
```

### Feishu Card: Restaurant or Local-Life Recommendation

```json
{
  "schema": "2.0",
  "config": {"width_mode": "fill"},
  "header": {
    "title": {"tag": "plain_text", "content": "{{name}}｜餐饮参考"},
    "template": "orange"
  },
  "body": {
    "elements": [
      {"tag": "div", "text": {"tag": "plain_text", "content": "{{area}}｜{{avg_price}}｜{{rating}} 分"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "推荐理由：{{summary}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "推荐菜：{{recommended_dishes_text}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "评论信号：{{comment_tags_text}}"}},
      {"tag": "hr"},
      {
        "tag": "action",
        "actions": [
          {"tag": "button", "text": {"tag": "plain_text", "content": "大众点评"}, "type": "primary", "behaviors": [{"type": "open_url", "default_url": "{{dianping_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "图片示例"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{image_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "小红书"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{xhs_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "导航"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{amap_navigation_url}}"}]}
        ]
      },
      {"tag": "div", "text": {"tag": "plain_text", "content": "{{source_note}}"}}
    ]
  }
}
```

### Feishu Card: Day-by-Day Route Summary

```json
{
  "schema": "2.0",
  "config": {"width_mode": "fill"},
  "header": {
    "title": {"tag": "plain_text", "content": "{{city}} {{days}} 日路线建议"},
    "template": "purple"
  },
  "body": {
    "elements": [
      {"tag": "div", "text": {"tag": "plain_text", "content": "先说结论：{{conclusion}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "Day 1：{{day1_summary}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "Day 2：{{day2_summary}}"}},
      {"tag": "div", "text": {"tag": "plain_text", "content": "删掉：{{removed_items_text}}"}},
      {"tag": "hr"},
      {
        "tag": "action",
        "actions": [
          {"tag": "button", "text": {"tag": "plain_text", "content": "生成地图"}, "type": "primary", "behaviors": [{"type": "callback", "value": {"action": "generate_trip_map", "plan_id": "{{plan_id}}"}}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "查看图片合集"}, "type": "default", "behaviors": [{"type": "open_url", "default_url": "{{image_collection_url}}"}]},
          {"tag": "button", "text": {"tag": "plain_text", "content": "调整行程"}, "type": "default", "behaviors": [{"type": "callback", "value": {"action": "edit_trip_plan", "plan_id": "{{plan_id}}"}}]}
        ]
      }
    ]
  }
}
```

For route cards, keep the route summary compact. Send separate single-recommendation cards for key POIs if each stop needs its own image, detail links, Dianping, Xiaohongshu, and navigation actions.

### Fallback Rules

- If `img` cannot be used because only an external URL is available, remove the image component and render a `图片示例` button.
- If `div`, `action`, or `column_set` is not supported by the active Feishu renderer, fall back to the plugin-supported `markdown`, `button`, and `hr` elements.
- If a button URL is missing, remove that button.
- If content exceeds card limits, send an overview card plus separate item cards, or hand off to a map page.

## Short Recommendation

Non-Feishu fallback only. In Feishu, use `render_feishu_card.py --mode card` or `--mode channel-data` for recommendation items. If native card delivery is unavailable, use `render_feishu_card.py --mode fallback-text`. Do not use Markdown tables.

```md
结论：...

推荐方案
1. 推荐卡片：POI 名称｜区域｜类型
   图片示例：cover_image_url 或 image_url
   详情链接：detail_url
   大众点评：dianping_url
   小红书：xhs_url 或 xhs_intro_url
   图片参考：image_search_url
   高德导航：amap_navigation_url
   注意：source_note / risk_note
2. 推荐卡片：...
3. 推荐卡片：...

为什么这样选
- 硬事实：...
- 软信号：...
- 风险：...
```

## Day-by-Day Plan

Non-Feishu fallback only. In Feishu, send an overview card plus separate item cards for key POIs.

```md
先说结论

每天怎么走
- Day 1：主区域 / 锚点 / 轻重节奏
  点位：名称 / 图片示例 / 详情 / 大众点评 / 小红书 / 高德导航
- Day 2：主区域 / 锚点 / 轻重节奏
  点位：名称 / 图片示例 / 详情 / 大众点评 / 小红书 / 高德导航

每天吃什么
- 午餐区域：主推 / 备选 / 为什么 / 大众点评 / 图片示例 / 高德导航
- 晚餐区域：主推 / 备选 / 为什么 / 大众点评 / 图片示例 / 高德导航

天气敏感点
提前订什么
删掉什么
为什么这样排
旅行记忆
- 历史复用：是否召回并复用了当前用户的历史 plan
- 已保存：新 plan 或修改后的 plan_id / version
- 偏好更新：本次明确沉淀的旅行偏好
```

## Train Result

```md
12306 当前余票快照（查询日期：YYYY-MM-DD）

推荐车次
1. Gxxx 出发 -> 到达，历时，关键席别余票/价格
2. ...

备注
- 最终以 12306 官方下单页为准。
- 我不能订票、候补、改签或支付。
```

## Decision Question

Use Re-ground / Simplify / Recommend / Options:

```md
行程规划，路线取舍

4 天放不下 12 个点，需要砍掉几个。建议砍远郊，因为来回耗时太高，节假日风险也更大。

选一个方向：
A. 按你说的砍远郊（推荐）
B. 保留远郊，砍市区点
C. 先看完整删点清单
```

## Map Handoff

Before generating a map, confirm the route is stable and the map-readiness inputs are settled:

```md
行程规划，方案确认

上面是完整路线。地图最好在天气、住宿/集合点、出行方式、食物安排、美景/体验点和节奏都基本定下来后再生成，这样不会刚做好就大改。

当前还需要确认：[列出 1-2 个最影响地图的点]

A. 没问题，按当前假设生成地图
B. 我先补充/调整这些点
C. 先只看文字方案，不生成地图
```

If the readiness gate already passes, keep it shorter:

```md
行程规划，方案确认

这版路线、餐食、交通和天气风险都比较稳了。确认后我会生成可手机打开的地图页面。

A. 没问题，生成地图
B. 我要调几个点
C. 重新换一个节奏
```
