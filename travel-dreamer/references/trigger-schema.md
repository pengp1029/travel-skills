# Trigger Schema

`travel-dreamer` emits one JSON object. The payload is for agent-to-agent handoff and scheduler logs, not raw end-user copy.

## Required Fields

```json
{
  "ok": true,
  "user_id": "default",
  "city": "北京",
  "mode": "weekend",
  "trigger_type": "weekend_inspiration",
  "should_notify": true,
  "priority": "medium",
  "reason": "临近周末，用户偏好与外部信号匹配。",
  "confidence": "medium",
  "quiet_reason": null,
  "user_context": {
    "preferences": {},
    "preference_summary": ["展览", "二次元"],
    "avoid": ["排队太久"],
    "notification_preferences": {}
  },
  "signals": [
    {
      "type": "time",
      "title": "临近周末",
      "confidence": "hard",
      "source_note": "由日期和 mode 推断"
    }
  ],
  "recommendation_mix": {
    "preference_fit_count": 2,
    "exploration_count": 1,
    "exploration_rule": "偏好邻近探索，不随机跳跃"
  },
  "main_agent_task": "请基于该触发器生成飞书周末出行灵感卡片。",
  "suggested_buttons": ["想看看", "换个方向", "本周不出门", "降低打扰频率"],
  "created_at": "2026-06-29T00:00:00Z"
}
```

## Field Notes

- `mode`: requested operating mode, one of `weekend`, `holiday`, `interest_radar`, `daily`.
- `trigger_type`: user-facing reason category, such as `weekend_inspiration`, `holiday_planning_nudge`, `interest_activity_radar`, `daily_light_observation`, `quiet_observation`.
- `should_notify`: whether a Feishu/user-facing message should be generated now.
- `priority`: `low`, `medium`, or `high`. High should be rare and reserved for strong timing constraints.
- `confidence`: `low`, `medium`, or `high`, based on memory quality and signal quality.
- `quiet_reason`: required when `should_notify=false`.
- `signals[].confidence`: use `hard` for calendar/date/weather/structured facts; use `soft` for social notes, vibe, subjective comments, and raw search hits.
- `main_agent_task`: concise instruction for `travel-agent-orchestrator`, not final copy.

## Non-Notify Payload

When not notifying, still return useful diagnostic context:

```json
{
  "should_notify": false,
  "priority": "low",
  "trigger_type": "quiet_observation",
  "quiet_reason": "用户关闭主动推送，或当前没有足够强的时机/兴趣信号。",
  "main_agent_task": null
}
```
