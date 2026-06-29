# Multi-User Travel Scoring

Use scoring as a transparent decision aid, not as a fake exact measurement. Explain the main drivers behind the ranking and lower confidence when facts are missing.

## Preference Model

Represent each participant with these fields when available:

```json
{
  "user_id": "feishu_id_or_stable_id",
  "display_name": "optional name",
  "origin_area": "coarse location only",
  "origin_city": "city",
  "preferences": {
    "crowd": "人少",
    "food": ["本地菜", "咖啡"],
    "pace": "轻松",
    "transport": ["地铁优先", "少步行"],
    "sightseeing": ["自然风景", "夜景"],
    "budget": "人均 120 以内"
  },
  "hard_constraints": ["不吃辣", "不能走太多路"]
}
```

If a field is not recalled or provided, mark it as missing. Do not infer precise home addresses, exact identity data, or private facts.

## Preference Merge

1. Hard constraints first: remove candidates that clearly violate allergies, mobility limits, strict budget caps, unavailable dates, or explicit do-not-go points.
2. Strong preferences second: give higher weight to repeated, high-confidence, or explicitly stated preferences.
3. Common preferences third: boost candidates matching multiple users.
4. Fairness guardrail: avoid a candidate where one user has very low satisfaction even if the group average is high.
5. Explain tradeoffs: say which users benefit and which preferences are compromised.

## Local Same-City Score

Use this score for same-city gathering areas, districts, or POIs:

```text
S_local = 0.30 * route_fairness
        + 0.20 * avg_route_efficiency
        + 0.25 * group_preference_fit
        + 0.10 * time_slot_fit
        + 0.10 * evidence_confidence
        - 0.05 * conflict_penalty
```

### Components

- `route_fairness`: high when the maximum commute time and commute variance are low. Penalize candidates that are excellent for one user but poor for another.
- `avg_route_efficiency`: high when the average route time from all known origins is low.
- `group_preference_fit`: high when the candidate supports shared preferences such as coffee, exhibitions, citywalk, local food, night view, quietness, or low walking effort.
- `time_slot_fit`: high when activities match the requested slot. Afternoon favors cafe, exhibition, park, board game, mall, and street walk. Evening favors dinner, night view, livehouse, movie, dessert, bar, and relaxed walk.
- `evidence_confidence`: high when coordinates, route estimates, business hours, weather, and Dianping signals are verified.
- `conflict_penalty`: increases when a candidate conflicts with queue tolerance, noise tolerance, budget, food restrictions, walking limits, or crowd preference.

### Local Candidate Rules

- Prefer one compact area over disconnected POIs.
- Prefer routes where afternoon activity, dinner, and evening extension are walkable or a short ride apart.
- Include indoor fallback for rain, heat, cold, elderly participants, or children.
- If route API or exact origins are missing, keep ranking but label route scores as low confidence.

## Intercity Destination Score

Use this score for recommending a shared travel city when participants start from different cities:

```text
S_city = 0.25 * preference_coverage
       + 0.20 * transport_accessibility
       + 0.15 * budget_fit
       + 0.15 * season_weather_fit
       + 0.10 * activity_diversity
       + 0.10 * fairness
       + 0.05 * evidence_confidence
       - conflict_penalty
```

### Components

- `preference_coverage`: how many users' food, sightseeing, pace, crowd, and nightlife preferences the city can satisfy.
- `transport_accessibility`: total travel time, directness, station/airport convenience, and schedule practicality from all origin cities. Use `train-query` for rail facts when relevant.
- `budget_fit`: whether transport, lodging, food, and activities fit the group budget.
- `season_weather_fit`: whether the city suits the dates, season, temperature, rain risk, and indoor/outdoor mix.
- `activity_diversity`: whether the city can support nature, culture, local food, night view, shopping, family, or relaxed plans without overpacking.
- `fairness`: high when the lowest individual satisfaction remains acceptable and satisfaction variance is low.
- `evidence_confidence`: high when transport, weather, POI, and restaurant facts are verified.
- `conflict_penalty`: applies for hard conflicts such as too spicy food focus for a non-spicy group, heavy walking for mobility limits, or high crowd risk for low-crowd users.

## Fairness Strategy

Use max-min fairness plus total utility:

1. Remove candidates that violate hard constraints.
2. Estimate each participant's satisfaction from 0 to 1.
3. Keep candidates where the lowest individual satisfaction is acceptable.
4. Sort by total score among remaining candidates.
5. If the top candidate has a weak spot for one user, explicitly state the mitigation or show a second option.

## Evidence Confidence

Use these confidence levels:

- High: route facts, coordinates, weather, business hours, and local-life signals are checked.
- Medium: route and POI facts are checked, but restaurant/queue/weather facts are incomplete.
- Low: only preferences and city/area common knowledge are available.

When confidence is medium or low, phrase recommendations as “当前建议” or “需要进一步验证”, not as confirmed facts.

## Missing Data Handling

- Missing one user's origin: keep preference-based ranking but do not claim commute fairness for that user.
- Missing all origins: ask for coarse origin areas before same-city midpoint planning.
- Missing exact date: use generic seasonal advice and ask for date before weather, ticket, or booking-sensitive claims.
- Missing preferences: default to moderate pace, moderate crowd, route smoothness, and food options with broad appeal.
