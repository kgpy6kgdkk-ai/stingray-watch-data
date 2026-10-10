# stingray-watch-data

Data feed for the [Stingray Watch](https://watch.stingrayfraud.com/) site: the industry-signal ticker, the marketplace-watch panel, and the high-risk-items panel.

`feed.json` is fetched client-side by the Carrd embed at page load — updating this file updates the live site with no need to touch or republish Carrd.

`archive.json` powers a second, separate on-page section (the permanent archive, below the live ticker) — see [Archive](#archivejson-permanent-history) below.

## Schema

```json
{
  "vectorTaxonomy": {
    "REFUND_ABUSE": "refund abuse",
    "CHARGEBACK_DISPUTE": "chargebacks & disputes",
    "ACCOUNT_TAKEOVER": "account takeover",
    "TRIANGULATION": "triangulation fraud",
    "CARD_TESTING": "card testing",
    "COUNTERFEIT": "counterfeit / authenticity",
    "LISTING_FRAUD": "fake listings",
    "AUCTION_ABUSE": "auction / bidding abuse",
    "SOCIAL_ENGINEERING": "social engineering",
    "AGENTIC_AI": "agentic AI fraud",
    "STOLEN_PAYMENT": "stolen payment methods",
    "PROMO_ABUSE": "promo abuse",
    "INDUSTRY_NEWS": "industry news"
  },
  "featured": "https://...",     // optional: the `link` of this week's lead item (see "Featured story" below)
  "ticker": [
    {
      "tag": "SIGNIFYD",           // shown as [TAG]
      "vector": "AGENTIC_AI",      // one key from vectorTaxonomy above — powers the site's filter chips
      "headline": "...",           // short sentence-case title, ~6-12 words; the bold link on Watch and the RSS title
      "text": "...",               // row description
      "link": "https://...",       // source URL
      "linkLabel": "signifyd.com", // shown as the link text
      "published": "2026-08-31T20:08:00Z" // ISO 8601 UTC; rendered client-side as "22m ago" etc.
    }
  ],
  "marketplace": [ /* same shape, rendered in the marketplace_watch.sh panel */ ],
  "highrisk": [ /* same shape, rendered in the high_risk_items.sh panel */ ]
}
```

### Featured story

`featured` is an optional top-level string holding the exact `link` of one item currently in `ticker`, `marketplace` or `highrisk`. The site's `this_week.sh` summary strip shows that item as "biggest story". If `featured` is missing, or matches no live item (for example, because the item was pruned), the strip falls back to the newest `highrisk` item, then the newest item overall. Every refresh that adds items sets it (AGENT_INSTRUCTIONS.md step 5). On the Sunday run it matches the item featured in the LinkedIn link; the Wednesday run, which builds no LinkedIn link, still updates it so the strip leads with that run's best story.

### Fraud vectors

Every item must carry a `vector` field set to one of the keys in `vectorTaxonomy`. This is what lets a visitor filter the live feed down to a specific fraud pattern (e.g. only "counterfeit / authenticity" items). The site's filter-chip bar is built dynamically from this object at page load — adding a new key here is enough to give it a chip, no Carrd changes needed. Still, keep the list deliberate: adding a code without also tagging items to it just gives visitors a dead-end chip that always shows "no items tagged this vector."

### Which panel does an item belong in?

This is the part that actually matters for keeping the site coherent — the three arrays are scoped by **different axes** (channel vs. item category), and it's easy to miscategorize an item if you're not paying attention to which axis it's on:

- **`ticker`** — general industry signal. Fraud-prevention industry news, research reports, vendor announcements, broad trend data. Not tied to a specific platform or product category.
- **`marketplace`** — **two-sided marketplace mechanics only.** Stories about how a specific two-sided marketplace (Etsy, eBay, Amazon, Whatnot, Vinted, etc.) runs its dispute/refund/bidding/review systems, and fraud patterns that exploit those *mechanics* (card testing against a platform's signup flow, shill bidding in a live auction, a platform's refund-policy change). If the story is about a *platform's operational choices or platform-level fraud technique*, it goes here — regardless of what product category happens to be involved.
- **`highrisk`** — **specific high-fraud-risk item categories**, regardless of which platform the story happens to involve. Current scope: sneakers, streetwear, TCG/Pokémon and sports cards, bullion (gold/silver/precious metals), electronics (phones, laptops, GPUs, gaming consoles), designer bags, luxury watches, gift cards, event tickets, and designer toys/collectibles (Labubu/Pop Mart, LEGO). If the story is fundamentally about counterfeiting, authentication failure, or fraud risk *specific to one of these product categories* — even if it happened on a marketplace also covered above — it goes here, not in `marketplace`. (Example: a StockX counterfeit-sneaker lawsuit is a `highrisk` item, not a `marketplace` item, even though StockX is a marketplace — the story is about sneaker authentication, not about how StockX's marketplace mechanics work.)

When a story is genuinely both (e.g., a marketplace changes its policy specifically *because* of counterfeit sneakers flowing through it), pick whichever angle the story is actually about — usually the mechanics/policy change goes in `marketplace`, the underlying counterfeit-item stat goes in `highrisk`, and they can be two separate entries if both angles are independently newsworthy.

## Raw URL (for the Carrd embed's fetch)

```
https://raw.githubusercontent.com/<owner>/stingray-watch-data/main/feed.json
```

## Updating

Edit `feed.json` and push to `main`. Keep entries sourced and verified — no fabricated links, no personal-anecdote scam stories, prefer named companies/publications/subreddits over generic claims.

### Retention: feed.json is a rolling 90-day window

`ticker`, `marketplace`, and `highrisk` are **not** fixed-size — each is a rolling 90-day window. Each weekly run should:

1. **Append** 2-4 new verified items to the appropriate array (don't overwrite existing ones).
2. **Prune** any item whose `published` timestamp is more than 90 days before the current date, from either array.
3. **Re-sort** each array by `published` descending (newest first) before writing — the site does not re-sort client-side beyond a defensive sort, so keep the file itself in order.
4. Skip a candidate if it's a near-duplicate of an item already in the file (same link, or same story already covered in the last ~14 days).

Array length will drift with real publishing volume — that's expected. A quiet week for a given fraud vector just means its filter chip shows fewer (or temporarily zero) results, which the site already handles gracefully.

## archive.json: permanent history

Carrd can't host a separate `/archive` page (it's a single-page builder), so instead of individually-indexable permalinks per item, the archive lives as a second growing section on the same page — everything ever published, never pruned. This is the only piece of the site whose SEO value compounds over time instead of resetting each week the ticker rotates.

Schema is a flat array under `items`, each entry the same shape as a `feed.json` row plus a `panel` field (`"ticker"` or `"marketplace"`) saying which panel it originally appeared in:

```json
{
  "items": [
    {
      "panel": "ticker",
      "tag": "SIGNIFYD",
      "vector": "AGENTIC_AI",
      "text": "...",
      "link": "https://...",
      "linkLabel": "signifyd.com",
      "published": "2026-08-31T20:08:00Z"
    }
  ]
}
```

**Updating `archive.json`:** whenever new items are added to `feed.json`, also **prepend** those same items (with `panel` added) to `archive.json`'s `items` array. Never remove or edit existing entries — this file should only ever grow. There's currently no scheduled job doing this automatically; it's a manual step alongside the weekly `feed.json` update until one exists.
