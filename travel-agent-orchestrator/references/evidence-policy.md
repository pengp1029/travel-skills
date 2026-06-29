# Evidence Policy

## Evidence Levels

### Hard Facts

Use these for claims that affect execution:

- Official websites: opening hours, closure days, ticket policy, airport/station rules.
- AMap: geocode, POI existence, route distance/time.
- QWeather: weather and forecast.
- 12306: station codes, ticket availability snapshot, train route stops.
- Dianping: shop existence, rating, price, review count, district, comment tags.

### Soft Signals

Use these for taste and risk, not official facts:

- Xiaohongshu: atmosphere, recent vibe, photo friendliness, perceived queue, subjective pitfalls.
- Dianping comment tags: queue and service patterns, but still summarize as observed review signals.
- Web/social travel notes: useful for context, not authoritative for hours or tickets.

### Derived Judgments

Clearly label these as agent judgment:

- Crowd risk: inferred from holiday, popularity, location, queue reviews, and time of day.
- Route smoothness: inferred from clustering, transport time, and number of transfers.
- Fit score: inferred from user preference and constraints.

## Unsupported Claims

Do not claim any of the following unless the user provides an authoritative tool/source that supports it:

- Real-time crowd count.
- Real-time queue minutes.
- Scenic-ticket inventory locking.
- Restaurant table reservation completion.
- Hotel room inventory locking.
- Payment completion.
- Train ticket booking, waitlist, seat selection, change, or refund.

## How to Phrase Uncertainty

Good:

- “12306 显示这是当前余票快照，最终以官方下单页为准。”
- “大众点评评论里排队信号较强，建议把它当作备选而不是路线锚点。”
- “这属于节假日客流风险判断，不是实时人数。”

Avoid:

- “一定有票。”
- “现场不用排队。”
- “我已经帮你订好了。”
