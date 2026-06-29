---
name: travel-dreamer
description: >
  OpenClaw 主动出行灵感 Dreamer agent。每当需要根据用户旅行记忆、周末/节假日时机、天气、小红书/大众点评等兴趣信号，判断是否应该主动给用户发送出行推荐、周末灵感、假期提醒或兴趣活动雷达时使用。它是后台观察和触发决策层，不替代 travel-agent-orchestrator 做完整行程规划；适用于定时任务、飞书主动推荐、用户要求“帮我做主动出行提醒/旅行 dreamer/出行灵感后台/根据记忆提前推荐”的场景。
metadata:
  openclaw:
    requires:
      bins:
        - python3
      env:
        - TRAVEL_MEMORY_DIR
        - OPENCLAW_USER_ID
    os:
      - darwin
      - linux
---

# travel-dreamer

## Environment

At the start of every skill run, load environment variables from `/Users/user/.openclaw/.env` if the file exists, before running any bundled script, CLI, browser automation, or network request. Do not print secret values.

## Role

Use this skill as the independent proactive travel Dreamer agent for OpenClaw.

The Dreamer agent does not produce a full itinerary by itself. It reads user travel memory, inspects time/context signals, optionally asks other travel skills for evidence, and emits a structured trigger decision for `travel-agent-orchestrator` to turn into a Feishu card or normal user-facing response.

Think of the split like this:

- `travel-dreamer`: observe, decide whether to interrupt, explain why, and hand off.
- `travel-agent-orchestrator`: talk to the user, plan, verify facts, render Feishu cards, save confirmed plans.
- `travel-skill/scripts/memory.py`: shared memory store for preferences and plans.
- `multi-user-travel-planner`: group-chat-only planner; do not use it for personal proactive Dreamer flows.

## MVP Workflow

1. Identify the user. Use a stable `--user-id` when available; otherwise use `default` only for local testing.
2. Read travel memory through `../travel-skill/scripts/memory.py show-preferences` and `recall` when needed.
3. Classify the trigger mode:
   - `weekend`: 周三/周四/周五的周末灵感。
   - `holiday`: 节假日前 14/7/3 天的提前询问或提醒。
   - `interest_radar`: 兴趣活动雷达，例如二次元、展览、live、市集。
   - `daily`: 低打扰日常观察，通常只记录或轻提醒。
4. Decide whether to notify. Prefer not notifying unless the timing and relevance are both good.
5. Keep recommendation mix roughly `2 preference-fit + 1 exploration` when recommending options. Exploration should be adjacent to user preferences, not random.
6. Output JSON using `references/trigger-schema.md`.
7. If `should_notify=true`, hand the `main_agent_task` to `travel-agent-orchestrator` and ask it to create the final user-facing card or message.

## MVP Script

Use `scripts/dreamer_mvp.py` for deterministic first-pass decisions. It is intentionally lightweight and safe to run from a scheduler later.

Examples:

```bash
python3 scripts/dreamer_mvp.py --user-id USER --city 北京 --mode weekend --date 2026-07-02 --interest 二次元 --interest 展览
python3 scripts/dreamer_mvp.py --user-id USER --city 上海 --mode holiday --holiday-name 国庆 --days-until-holiday 10
python3 scripts/dreamer_mvp.py --user-id USER --city 杭州 --mode interest_radar --interest 二次元 --signal "周末有动漫快闪活动"
```

The script reads shared travel memory and emits a trigger payload. It does not call paid APIs, push Feishu messages, or modify user preferences by default.

## Decision Policy

Read `references/decision-policy.md` before making subjective push/no-push decisions.

Important principles:

- User permission and notification preferences win over enthusiasm.
- Do not overfit one click into a strong preference.
- Treat Xiaohongshu and Dianping as soft signals unless corroborated by official/structured sources.
- Make proactive messages feel helpful and optional, not like advertising or surveillance.
- Avoid mentioning that the system is “monitoring” the user. Say “我帮你留意到” or “临近周末，可以看看”。

## Shared Memory

Use the existing travel memory service instead of creating a separate store for core preferences:

```bash
python3 ../travel-skill/scripts/memory.py --user-id USER show-preferences
python3 ../travel-skill/scripts/memory.py --user-id USER recall --query '北京 周末 二次元 展览'
```

Dreamer-specific observations may be saved later in a separate observation store, but the MVP only emits payloads. If persistence is added, keep it separate from strong user preferences unless the user explicitly confirms a preference.

## External Signals

Use these skills as needed:

- `travel-skill`: weather, AMap, web search, base travel facts.
- `xiaohongshu-skills`: read-only interest/POI notes and soft activity signals.
- `dianping-info-query`: restaurants, districts, queues, shop signals.
- `train-query`: intercity train facts and ticket availability.
- `trip-map-builder`: only after the user accepts a plan and wants a map/page.

For the MVP script, external signals are passed as `--signal` strings or supplied by the calling scheduler/agent. Later versions can call these skills before constructing the trigger payload.

## Handoff To Main Agent

When `should_notify=true`, do not send raw Dreamer analysis directly to the user. Ask `travel-agent-orchestrator` to transform it into a Feishu card or concise message.

The handoff should include:

- user id
- city/base city
- trigger type
- reason
- user preference summary
- hard facts vs soft signals
- suggested card shape
- button options, such as “想看看”, “换个方向”, “本周不出门”, “降低打扰频率”

## Boundaries

This skill does not book tickets, lock inventory, claim real-time crowd counts, or make exact price guarantees. It should not infer sensitive traits from user behavior. It should not store phone numbers, IDs, payment data, login state, ticket credentials, or other sensitive information.
