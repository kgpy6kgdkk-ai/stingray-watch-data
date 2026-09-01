# fraud-sonar-data

Data feed for the [Fraud Sonar](https://stingray-sonar.carrd.co/) ticker and marketplace-watch panels.

`feed.json` is fetched client-side by the Carrd embed at page load — updating this file updates the live site with no need to touch or republish Carrd.

## Schema

```json
{
  "vectorTaxonomy": {
    "REFUND_ABUSE": "refund abuse",              // fixed, closed list — do not add
    "CHARGEBACK_DISPUTE": "chargebacks & disputes", // new codes without also updating
    "ACCOUNT_TAKEOVER": "account takeover",         // the Carrd filter-chip UI, which
    "TRIANGULATION": "triangulation fraud",         // reads this object to build its
    "CARD_TESTING": "card testing",                 // chip list.
    "COUNTERFEIT": "counterfeit / authenticity",
    "LISTING_FRAUD": "fake listings",
    "AUCTION_ABUSE": "auction / bidding abuse",
    "SOCIAL_ENGINEERING": "social engineering",
    "AGENTIC_AI": "agentic AI fraud",
    "INDUSTRY_NEWS": "industry news"
  },
  "ticker": [
    {
      "tag": "SIGNIFYD",           // shown as [TAG]
      "vector": "AGENTIC_AI",      // one key from vectorTaxonomy above — powers the site's filter chips
      "text": "...",               // row description
      "link": "https://...",       // source URL
      "linkLabel": "signifyd.com", // shown as the link text
      "published": "2026-08-31T20:08:00Z" // ISO 8601 UTC; rendered client-side as "22m ago" etc.
    }
  ],
  "marketplace": [ /* same shape, rendered in the marketplace_watch.sh panel */ ]
}
```

### Fraud vectors

Every item must carry a `vector` field set to one of the keys in `vectorTaxonomy`. This is what lets a visitor filter the live feed down to a specific fraud pattern (e.g. only "counterfeit / authenticity" items). The taxonomy is intentionally closed — pick the closest existing category rather than inventing a new one, since new codes won't have a filter chip on the site until `vectorTaxonomy` and the Carrd embed are both updated to match.

## Raw URL (for the Carrd embed's fetch)

```
https://raw.githubusercontent.com/<owner>/fraud-sonar-data/main/feed.json
```

## Updating

Edit `feed.json` and push to `main`. Keep entries sourced and verified — no fabricated links, no personal-anecdote scam stories, prefer named companies/publications/subreddits over generic claims.
