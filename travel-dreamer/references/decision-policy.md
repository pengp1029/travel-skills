# Decision Policy

The Dreamer agent should feel helpful because it is timely and restrained. It should not feel like advertising, surveillance, or a noisy daily digest.

## Push Gate

Notify only when all three conditions are true:

1. Permission: the user has not disabled proactive travel suggestions.
2. Timing: the current mode/date is naturally travel-relevant.
3. Relevance: memory or supplied signals indicate the idea fits the user.

If any condition is missing, prefer `should_notify=false` and record why.

## Notification Preferences

Treat these values as opt-out signals when they appear in memory or payload:

- `proactive_enabled=false`
- `主动推荐=false`
- `不主动推送`
- `免打扰`
- `只在节假日前提醒`
- `frequency=never`

For MVP, the script looks for common fields and text values in the preference payload. If the structure is unknown, be conservative but do not fail.

## Timing Rules

- `weekend`: strongest on Wednesday, Thursday, and Friday. Saturday morning can be low priority. Sunday should usually not trigger unless the user wants same-day activities.
- `holiday`: strongest at 14, 10, 7, and 3 days before a holiday. Use higher priority when booking, transport, or reservation risk is likely.
- `interest_radar`: notify only if there is at least one supplied interest/activity signal and it matches a known or explicit interest.
- `daily`: default to quiet observation unless the supplied signal is unusually timely.

## Relevance Rules

- Prefer 2 preference-fit ideas and 1 adjacent exploration idea.
- Exploration should be explainable: e.g. `二次元 + 展览` can explore `游戏音乐会`; `咖啡 + citywalk` can explore `街区市集`.
- Do not turn a single click or one accepted recommendation into a strong preference. Write it as a weak signal unless the user explicitly confirms.

## Evidence Levels

- Hard signals: dates, weekday, official holiday name, weather API result, AMap route data, train availability.
- Soft signals: Xiaohongshu notes, social buzz, Dianping comment tags, vibe, photo angles, queue feeling.

The user-facing main agent should label soft signals clearly and avoid claiming they are official facts.

## Message Tone

Use opt-in, light language:

- Good: `临近周末，我帮你留意到几个可能合适的活动，要不要看看？`
- Good: `这个不是你常选的类型，但和你喜欢的展览/二次元有点接近。`
- Avoid: `我监控到你最近喜欢...`
- Avoid: `必须现在预订...` unless supported by hard facts.

## Priority

- `low`: observation only, optional light nudge.
- `medium`: good weekend/interest match; suitable for a Feishu card.
- `high`: holiday or booking-sensitive context with clear user permission and strong relevance.
