# trip-map-builder

OpenClaw travel map skill for turning messy trip inputs into a practical itinerary and a mobile-friendly Leaflet HTML map.

Use this skill when the user asks for an itinerary map, trip map, route page, travel HTML, or wants to combine hotel/flight/wishlist/restaurant research into one usable map.

## Workflow

1. Plan: extract constraints, decide daily areas, delete impossible or high-risk points.
2. Research: verify hard facts and enrich restaurants/soft signals via Dianping and Xiaohongshu.
3. Build: fill `assets/template.html` with hotel, days, locations, links, reservation notes, and map coordinates.

## Inputs

Minimum useful input:

- Dates and arrival/departure time.
- Hotel name and address.
- City or region.
- Must-go and do-not-go list.

Better input:

- Budget, walking tolerance, queue tolerance, food preferences, party size, and weather sensitivity.

## Outputs

- A concise planning explanation.
- A structured day-by-day itinerary.
- A generated HTML map using the bundled Leaflet template.
- Clear notes about what was removed, what needs booking, and which facts still need confirmation.
