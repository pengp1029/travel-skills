# Dianping Info Query Reference

This skill uses browser automation rather than a stable public Dianping API.

## Data Sources

- Dianping web pages at `https://www.dianping.com`.
- Browser readability extraction for detail pages and district pages.
- DOM snapshots as fallback.

## Output Contract

Return facts with a source note and distinguish facts from review signals:

- Facts: name, address, phone, business hours, price, score.
- Signals: comment tags, high-frequency mentions, queue-related labels, service/taste sentiment.

## Rate and Safety

Use single-query workflows. Do not batch scrape. Pause for login, captcha, or slider verification.
