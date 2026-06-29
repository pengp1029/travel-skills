# Plan DAG

Use this DAG mentally when orchestrating a complete travel-agent answer.

```text
User Request
  -> User Identity
      -> choose stable user_id for memory operations
      -> keep plans and preferences isolated per user
  -> Group Chat Gate
      -> only enter group planning when the current conversation is explicitly a group chat
      -> if this is a one-on-one chat, personal plan, or single-chat proxy request for multiple people, skip multi-user-travel-planner
  -> Group Identity (only for explicit group-chat multi-user requests)
      -> extract group member Feishu ids / aliases / participant count
      -> map each Feishu id to memory.py --user-id
      -> collect coarse origin areas or origin cities
      -> never invent missing homes, preferences, or profiles
  -> Constraint Extraction
      -> city / dates / days / party / pace / budget / hotel
      -> must-go / do-not-go / food / queue tolerance / transport
      -> for explicit group chats: time slot / same-city vs intercity / fairness requirements
  -> Preference Extraction
      -> travel-skill/scripts/memory.py extract-preferences --user-id USER
      -> store only explicit travel preferences, not sensitive data
  -> Group Preference Merge (only for explicit group-chat multi-user requests)
      -> recall each user's preferences with memory.py show-preferences
      -> filter hard constraints first
      -> combine strong preferences, common preferences, budget, pace, transport, and crowd tolerance
      -> preserve per-user conflicts for explanation
  -> Plan Identity
      -> city + days + trip_type + anchors + tags
      -> for explicit group chats: group participants + same-city area or destination city + time slot
      -> distinguish different cities, different days, and different itineraries
  -> Memory Recall
      -> travel-skill/scripts/memory.py recall --user-id USER
      -> reuse or modify an existing plan when the user refers to prior work
      -> for groups, recall per-user memory but do not modify another user's plan unless explicit
  -> Missing-Info Check
      -> same-city group: coarse origins are required for commute fairness
      -> shared destination: origin cities and rough date/season are required for transport/weather confidence
  -> Fact Collection
      -> travel-skill: POI / route / weather / web
      -> train-query: station / ticket / route stops
      -> dianping-info-query: shops / ratings / queue / comments
      -> multi-user-travel-planner: group-chat-only scoring / fairness / compromise explanation
  -> Candidate Generation
      -> same-city: districts / POIs / compact activity areas
      -> intercity: destination cities / transport modes / activity themes
  -> Constraint Verification
      -> time budget
      -> route smoothness
      -> weather sensitivity
      -> booking requirements
      -> queue/crowd risk
      -> group fairness and hard conflicts
  -> Ranking
      -> executable Top 3 or day-by-day plan
      -> for groups: maximize minimum satisfaction before optimizing total score
  -> Plan Persistence
      -> save-plan for new durable itineraries
      -> modify-plan for changes to existing itineraries, preserving versions
      -> do not save precise home addresses or sensitive identity data
  -> Output
      -> concise recommendation
      -> evidence and risks
      -> memory note: recalled / saved / preference updated
      -> for groups: per-user fit, compromises, missing data, fairness rationale
      -> optional map via trip-map-builder
```

## Plan Identity

Identify a plan by the current user plus itinerary dimensions:

- User: never recall or modify another user's plan.
- City: highest priority discriminator.
- Days: normalize `3天`, `三天`, `半天`, `晚上` before matching.
- Trip type: family, couple, elderly, solo, friends, or general.
- Anchors: must-go POIs, hotel/base area, major districts.
- Tags: food, local dishes, museums, night view, low queue, relaxed pace, etc.

For explicit group-chat plans, also identify:

- Participants: stable Feishu ids or aliases when provided.
- Same-city base: city plus candidate gathering area or activity district.
- Intercity base: each user's origin city plus candidate destination city.
- Time slot: afternoon, evening, weekend, multi-day, or exact date.

If two recalled plans are close, prefer the one with the stronger city/day match. Ask a short choice question only when multiple plans are genuinely ambiguous.

## Memory Policy

Use `travel-skill/scripts/memory.py` for durable travel memory:

```bash
python3 scripts/memory.py --user-id USER extract-preferences --query '不喜欢排队，喜欢本地菜'
python3 scripts/memory.py --user-id USER recall --query '杭州 三天 亲子 少排队'
python3 scripts/memory.py --user-id USER save-plan --input plan.json
python3 scripts/memory.py --user-id USER modify-plan --plan-id PLAN_ID --input patch.json
python3 scripts/memory.py --user-id USER show-preferences
```

For explicit group-chat multi-user requests, call `show-preferences` and optional `recall` separately for each Feishu id. Treat memory as a planning aid, not a source of hard facts. Verify current opening hours, weather, train availability, restaurant status, and booking requirements with the relevant sub-skills when they affect the final decision.

## Ranking Heuristics

Prefer plans that are:

- Smooth: low backtracking, one main area per day.
- Executable: enough time for travel, meals, rest, airport/station buffers.
- Honest: risky points are marked or removed.
- Personalized: respects the current user's must-go, do-not-go, budget, pace, and queue tolerance.
- Fair for explicit group chats: avoids a plan where one participant has very low satisfaction.
- Recoverable: has indoor/weather/nearby alternatives.

## Group Ranking Heuristics

For same-city group planning, rank by:

- Commute fairness and maximum travel time.
- Average route efficiency.
- Group preference fit.
- Afternoon/evening activity continuity.
- Queue, crowd, budget, and walking conflict penalties.
- Evidence confidence.

For shared destination city planning, rank by:

- Preference coverage across users.
- Transport accessibility from all origin cities.
- Budget fit.
- Season/weather fit.
- Activity diversity.
- Fairness via lowest individual satisfaction.
- Evidence confidence.

## Deletion Is Part Of Planning

When the user gives too many points, remove some. Say what was removed and why:

- Too far for the available days.
- High holiday crowd risk.
- Weather-sensitive and no fallback.
- Duplicates another experience.
- Makes the final day unsafe for airport/station timing.
- In group planning, creates unfair commute or violates a participant's hard constraint.
