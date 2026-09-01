# fraud-sonar-data

Data feed for the [Fraud Sonar](https://stingray-sonar.carrd.co/) ticker and marketplace-watch panels.

`feed.json` is fetched client-side by the Carrd embed at page load — updating this file updates the live site with no need to touch or republish Carrd.

## Schema

```json
{
  "ticker": [
    {
      "tag": "SIGNIFYD",           // shown as [TAG]
      "text": "...",               // row description
      "link": "https://...",       // source URL
      "linkLabel": "signifyd.com", // shown as the link text
      "published": "2026-08-31T20:08:00Z" // ISO 8601 UTC; rendered client-side as "22m ago" etc.
    }
  ],
  "marketplace": [ /* same shape, rendered in the marketplace_watch.sh panel */ ]
}
```

## Raw URL (for the Carrd embed's fetch)

```
https://raw.githubusercontent.com/<owner>/fraud-sonar-data/main/feed.json
```

## Updating

Edit `feed.json` and push to `main`. Keep entries sourced and verified — no fabricated links, no personal-anecdote scam stories, prefer named companies/publications/subreddits over generic claims.
