# Routing

## Intent Routing

Use the smallest set of sub-skills that can answer the user well.

- Broad travel plan, weekend trip, city itinerary, hotel-nearby plan: start with `travel-skill`.
- Group-chat-only travel planning: if and only if the current conversation is explicitly a group chat and group members ask for multiple Feishu ids, per-person preference recall, same-city midpoint/gathering areas, afternoon/evening group activities, or shared destination city ranking, use `multi-user-travel-planner`. For one-on-one chats or personal planning, do not use it.
- Restaurant, cafe, shop, mall, district, Dianping score, queue, review tags: use `dianping-info-query`.
- Trip map, HTML page, Leaflet map, itinerary website, shareable route page: use `trip-map-builder` only after the route and map-readiness inputs are stable: weather, hotel/base or meeting point, transport mode, food plan, scenic/experience anchors, pace/budget, and key preferences are confirmed or explicitly accepted as assumptions.
- High-speed rail, train tickets, 12306, station codes, route stops: use `train-query`.

## Combination Patterns

### Short Trip Top Options

1. `travel-skill` for city/POI/weather/route facts.
2. `dianping-info-query` for food/local-life candidates.
3. Rank by time, route smoothness, budget, queue tolerance, and weather.

### Hotel-Based Itinerary

1. `travel-skill` geocodes hotel and candidate POIs.
2. Cluster one main area per day.
3. `dianping-info-query` adds meal candidates by daily area.
4. Optional `trip-map-builder` generates the map.

### Same-City Group Gathering

Use this pattern only in an explicit group chat. In one-on-one chats, answer with the general travel planning flow even if the user mentions multiple people.

1. `multi-user-travel-planner` identifies group participants, recalls each group member's preferences by Feishu id when available, and lists missing coarse origins.
2. `travel-skill` verifies geocodes, POIs, route time, and weather for candidate areas.
3. `dianping-info-query` adds restaurant, cafe, district, queue, rating, and price signals.
4. Rank candidates by commute fairness, average route efficiency, group preference fit, time-slot fit, evidence confidence, and conflict penalties.
5. Output an afternoon/evening route and show who is satisfied, who compromises, and which facts still need confirmation.

### Shared Destination City

Use this pattern only in an explicit group chat. In one-on-one chats, treat the request as ordinary travel planning and do not call `multi-user-travel-planner`.

1. `multi-user-travel-planner` recalls each group member's preferences and origin city.
2. `train-query` verifies rail accessibility when high-speed rail matters.
3. `travel-skill` checks weather, POI fit, and local route feasibility for shortlisted cities.
4. Rank cities by preference coverage, transport accessibility, budget fit, season/weather fit, activity diversity, fairness, and evidence confidence.
5. Output Top 3 cities with per-user fit, risks, and next verification steps.

### Intercity Travel Plan

1. `train-query` resolves station and ticket facts.
2. `travel-skill` handles local route after arrival.
3. Only then recommend first-day and last-day intensity.

### Map Deliverable

1. Finish constraints and route decisions first.
2. Run a map-readiness gate before generating: weather, hotel/base or meeting point, transport mode, food plan, scenic/experience anchors, pace/budget, and key preferences.
3. If only 1-2 key inputs are missing, ask one compact confirmation question with options instead of generating immediately.
4. Verify coordinates and external links.
5. Call `trip-map-builder` to build the HTML map only after the user accepts the plan or explicitly asks for a draft map.

## Clarification Policy

Ask only when missing information blocks a reliable answer:

- Required for multi-day plans: dates or rough duration, city, hotel/base area if route matters.
- Required before using `multi-user-travel-planner`: explicit group chat context plus multi-person planning intent.
- Required for group-chat same-city midpoint planning: each participant's coarse origin area, unless the group accepts low-confidence route scoring.
- Required for group-chat shared destination city ranking: each participant's origin city and rough date or season.
- Required for train query: date, from station/city, to station/city.
- Required for booking-sensitive advice: exact date and party constraints.

Do not ask about preferences that can be reasonably defaulted. Make the default and continue.
