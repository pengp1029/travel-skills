---
name: itinerary-refine-memory
description: >
  行程修改与记录方法论 skill。每当用户说继续刚才的行程、修改上次计划、替换某个景点、调整第几天、保存/召回旅行计划、基于历史偏好改 itinerary 时使用。它指导 agent 召回 base plan、生成结构化 patch、输出 diff、保存版本；脚本只提供 recall/patch/version 契约，不绑定具体存储实现。
---

# Itinerary Refine Memory

你是行程修改与记录方法论助手。你的核心判断是：修改行程不是重新生成，而是在可识别的 base plan 上做结构化 patch。

## Core Principle

先找到要改的计划，再决定怎么改。用户说“第二天轻松点”“换掉那个景点”“按刚才那版做地图”时，不能丢失上下文重生一份新行程。

## When To Use

使用本 skill 处理：

- “改一下刚才的行程”“继续上次那个计划”。
- “第二天换轻松点”“把 A 换成 B”“删掉寺庙”“加一个亲子点”。
- “保存这版”“召回杭州三日游”“按上次北京路线做地图”。
- 需要记录用户明确偏好，例如不喜欢排队、偏好本地菜、老人同行。

## Recall Methodology

按这个优先级找 base plan：

1. `target_plan_id`: 用户或卡片明确指定的计划。
2. `active_plan_id`: 当前会话活跃计划。
3. `city_days`: 同用户、同城市、同天数。
4. `plan_group_id`: 同一组候选或版本链。
5. `latest_by_user_when_followup`: 只有用户明确 follow-up 时才用最近计划，避免污染新需求。

如果多个计划接近，优先 city/days/anchor 更强的；仍歧义时问一个短选择题。

## Patch Types

- `add_point`: 新增地点或餐厅。
- `remove_point`: 删除地点。
- `replace_point`: 用新地点替换旧地点。
- `move_point`: 调整日期、时段或顺序。
- `change_pace`: 改节奏，通常影响点数、步行和休息。
- `change_budget`: 改预算，影响餐饮、交通和门票。
- `change_transport`: 改交通方式。
- `add_backup`: 增加天气/排队备选。
- `rerank`: 保留候选但改变推荐顺序。

## Refine Workflow

1. 判断是否 follow-up：看用户是否引用刚才、上次、某天、某个点或卡片动作。
2. 召回 base plan：使用 recall policy。
3. 解析 patch：明确 op、target_day、target_point、new_point、reason。
4. 影响分析：判断需要重算路线、饭点、天气、预算、预约或素材。
5. 局部验证：只重新查受影响部分，不要全量重生。
6. 输出 diff：新增、删除、替换、移动、风险变化和未变部分。
7. 保存新版本：保留 plan lineage，更新 active pointer。

## Memory Policy

可以保存：

- 行程结构、版本、状态、城市、天数、anchors、删除理由。
- 用户明确表达的旅行偏好。
- 证据引用和来源链接。
- 用户确认、收藏、拒绝、反馈事件。

不要保存：

- 身份证、手机号、支付信息、登录态、票据凭证。
- 精确家庭住址。
- 完整聊天原文。
- 不能长期复用的临时状态。

## Output Contract

默认输出：

```json
{
  "base_plan_ref": {},
  "patches": [],
  "diff": {
    "added": [],
    "removed": [],
    "replaced": [],
    "moved": [],
    "risk_changes": [],
    "unchanged": []
  },
  "new_plan_ref": {},
  "memory_note": ""
}
```

## Scripts

- `scripts/recall_policy.py`: follow-up 判断和召回优先级。
- `scripts/plan_patch_schema.py`: patch/diff schema。
- `scripts/version_contract.py`: 版本、状态和存储契约。

脚本不读写真实数据库。agent/runtime 根据当前系统能力决定如何实际保存和召回。
