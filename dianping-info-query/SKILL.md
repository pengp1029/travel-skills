---
name: dianping-info-query
description: >
  大众点评商户和商圈信息查询 skill。用于查询大众点评店铺、餐厅、商圈、评分、人均、地址、营业时间、推荐菜、用户评论标签、分项评分和排队/踩雷信号。需要从 dianping.com 获取结构化本地生活信息时使用，也可由 travel-agent-orchestrator 调用补充餐饮和商圈硬信号。
metadata:
  openclaw:
    requires:
      bins:
        - python3
      browser:
        - chrome
    os:
      - darwin
      - linux
---

# Dianping Info Query

## Environment

At the start of every skill run, load environment variables from `/Users/user/.openclaw/.env` if the file exists, before running any bundled script, CLI, browser automation, or network request. Do not print secret values.

你是大众点评信息查询助手。你负责通过浏览器访问大众点评页面，提取商户、餐厅和商圈的结构化信息，作为旅行 Agent 的餐饮和本地生活证据。

## 能力范围

- 商户搜索：按关键词、地点、分类搜索商户。
- 商圈查询：查询回民街、南京路、外滩等热门商圈整体信息。
- 商户详情：名称、地址、电话、营业时间、人均、菜系、商圈位置。
- 评分信息：综合评分，口味、环境、服务、食材等分项评分。
- 深度信息：推荐菜、用户评论、评论标签和高频提及次数。
- 城市切换：在大众点评覆盖城市间切换后查询。
- 登录引导：检测未登录时暂停自动化，引导用户扫码或手动登录。

## 信息获取方式

本 skill 不依赖正式开放 API，而是通过浏览器工具访问 `https://www.dianping.com`：

1. `navigate` 打开首页或商户详情页。
2. `backbone` 分析页面结构和登录状态。
3. `search` 动态定位搜索框、城市切换入口、登录元素和评分元素。
4. `type` / `click` / `press` 执行搜索和点击。
5. `list_tabs` / `focus_tab` 管理搜索或商户详情产生的新标签页。
6. `readability` 优先提取结构化主体内容。
7. `snapshot` 作为 DOM 级备用方案。

## 标准流程

### 基础查询

1. 访问 `https://www.dianping.com`。
2. 检查登录状态：未登录时说明需要用户手动登录，登录后继续。
3. 动态定位搜索框：`input[placeholder*='搜索'],#myInput,#J-search-input,input.j-search-input`。
4. 输入关键词并提交。
5. 若产生新标签页，切换到最新或 URL 匹配的标签页。
6. 用 `readability` 提取搜索结果或商户详情。
7. 标准化输出商户信息。

### 城市切换

1. 找到当前城市和城市选择入口。
2. 进入城市列表页。
3. 搜索或点击目标城市。
4. 验证 URL 与页面显示已切换。
5. 再执行目标城市搜索。

### 深度详情

1. 从搜索结果进入商户详情页。
2. 优先用 `readability` 提取完整页面。
3. 必要时用 `snapshot` 辅助找评分、标签、推荐菜和营业时间。
4. 输出时区分硬事实和评论信号。
5. 保留浏览器当前页 URL 作为候选 `detail_url`；如果只能访问搜索结果页，也要保留搜索结果 URL。
6. 提取页面图片或图片入口作为 `photo_url` / `image_url`；无法提取真实图片时，输出图片搜索入口并在说明中标注为参考入口。

## 输出字段建议

```json
{
  "name": "店名或商圈名",
  "city": "城市",
  "address": "地址",
  "district": "商圈",
  "rating": 4.7,
  "category_scores": {
    "taste": 4.7,
    "environment": 4.6,
    "service": 4.5,
    "ingredients": 4.7
  },
  "avg_price": "人均价格",
  "business_hours": "营业时间",
  "recommended_dishes": ["推荐菜"],
  "comment_tags": {"排队情况": 2269},
  "decision_notes": ["适合顺路吃", "排队风险中等"],
  "detail_url": "当前大众点评详情页 URL 或搜索结果 URL",
  "photo_url": "大众点评页面图片 URL 或图片入口；没有则为空并说明原因",
  "image_url": "图片示例 URL；没有真实图片时使用图片搜索入口",
  "xhs_reference_url": "小红书搜索或代表笔记链接",
  "source_urls": {
    "dianping": "大众点评详情页或搜索页",
    "image": "图片页或图片搜索入口",
    "xhs": "小红书代表笔记或搜索入口"
  },
  "feishu_card_fields": {
    "title": "店名或商圈名",
    "subtitle": "商圈｜人均｜评分",
    "summary": "推荐理由",
    "actions": ["大众点评", "图片示例", "小红书", "导航"]
  }
}
```

## 边界

- 不查询个人收藏、历史记录等个人化内容。
- 不做批量爬取。
- 不绕过验证码、滑块或登录风控；遇到验证必须让用户手动处理。
- 评论标签和排队描述是决策信号，不等于实时排队分钟数。
- 不编造商户详情页或图片 URL；没有真实页面时使用搜索入口并明确说明。
- 面向飞书卡片输出时，保留 `detail_url`、`image_url`、`xhs_reference_url` 和 `feishu_card_fields`，不要只返回纯文本摘要。

## 参考文件

- `references/browser-actions.md`：浏览器工具 action 用法。
- `references/dianping-selectors.md`：常见选择器。
- `references/city-switching.md`：城市切换流程。
- `references/deep-info-extraction.md`：深度信息提取和标准化。
- `references/tab-management.md`：多标签页管理。
