# Weekly refresh — agent instructions

You are running unattended, on a schedule. Your changes reach the public
page (watch.stingrayfraud.com fetches `feed.json`/`archive.json` from this
repo's `main` branch directly) only after a one-click PR merge — see step 7.
Be conservative regardless: when genuinely uncertain about a source's
credibility or a claim's accuracy, skip it rather than include it.

## What this repo is

Data feed for [Stingray Watch](https://watch.stingrayfraud.com/), a weekly feed
of chargeback trends, fraud patterns, and marketplace fraud signals for
Stingray Fraud Intelligence. Read `README.md` in this repo now for the full
schema — it's the source of truth, more detailed than this file, and may
have evolved since this file was written. Do not proceed until you've read it.

## Your task, in order

1. **Read `README.md`, `feed.json`, and `archive.json`** in this checkout
   first. You need the current contents of both JSON files to de-duplicate
   against in step 3.

2. **Research fresh signal.** Use web search for current (last 7-14 days)
   e-commerce and marketplace fraud news. Good query angles: "e-commerce
   fraud trends", "chargeback fraud news", "marketplace fraud", "account
   takeover fraud statistics", "refund abuse", "counterfeit marketplace
   fraud", "agentic AI fraud shopping". Vary queries — don't just run one
   search and stop.

   **Also search the high-risk item categories specifically** (this feeds
   the `highrisk` panel — see README for what qualifies): sneakers,
   streetwear, TCG/Pokémon and sports cards, bullion (gold/silver/precious
   metals), electronics (phones, laptops, GPUs, gaming consoles), designer
   bags, luxury watches, gift cards, event tickets, and designer
   toys/collectibles (Labubu/Pop Mart, LEGO). Query angles:
   "[category] counterfeit fraud", "[category] resale scam", "[category]
   authentication fraud". Don't force it — if a category has no
   well-sourced news this week, skip it rather than stretch a weak source
   to fill it.

   **Always specifically check frankonfraud.com** (Frank McKenna's Frank
   on Fraud blog) for recent posts, in addition to general search — either
   search `site:frankonfraud.com` for the topic angles above, or fetch the
   site directly, to see what's been posted in the last 1-2 weeks.

   **Occasionally use Chargeback Nerd** (chargebacknerd.substack.com,
   weekly Monday posts; RSS feed at `/feed`). It's part of Stingray's
   network. Fetch the feed each run and include a post **only** when it
   carries news: a card-network rule change (e.g. Mastercard bringing back
   GMAP), new dispute data, or a dated trend. Skip evergreen advice posts
   and the "History of Payment Disputes" series. Limits: at most one
   Chargeback Nerd item per run, never in place of a stronger item, and
   none at all if `feed.json` already has an item with `linkLabel`
   "Chargeback Nerd" published in the last ~14 days. All the usual rules
   apply (publish date inside the window, verify the link and the claim,
   de-duplicate). Use `linkLabel` "Chargeback Nerd".

3. **Apply editorial judgment. This is the part that matters most — do not
   just post whatever search returns.** Select **2-4 new items per panel**
   (not 2-4 total — `ticker`, `marketplace`, and `highrisk` each get their
   own bar to clear) using these filters:
   - Prefer named companies, publications, or industry-research sources
     (e.g. Signifyd, TransUnion, Chargebacks911, Merchant Risk Council,
     Frank on Fraud (frankonfraud.com), named trade press, named security
     researchers) over generic or unsourced claims.
   - Community sources (Reddit, forums) are fine **only** when they
     document a verifiable pattern multiple people are independently
     reporting — never an individual "I got scammed" personal-anecdote
     post. Those are real but off-tone for a B2B fraud-intelligence feed.
   - **Verify every link actually resolves and its content matches the
     claim you're citing it for**, by fetching it, before including it.
     Never fabricate or guess a URL. If you can't confirm a source
     first-hand, drop the item — don't include it "probably right."
   - Check the selected items against what's **already in `feed.json` and
     `archive.json`** (read in step 1) — skip near-duplicates (same
     underlying story or stat, even from a different source article) and
     skip anything covering the same specific fact already posted in the
     last ~14 days.
   - Split selections between `ticker` (the "industry news" panel: general industry signal),
     `marketplace` (two-sided marketplace **mechanics** — platform policy
     and platform-level fraud technique, not product category), and
     `highrisk` (fraud specific to a high-risk item category, regardless of
     platform). **Read the "Which panel does an item belong in?" section of
     README.md before categorizing anything** — the marketplace/highrisk
     split is easy to get backwards (a StockX counterfeit story is
     `highrisk`, not `marketplace`, even though StockX is a marketplace).

4. **Format each selected item** per `README.md`'s schema: `tag`, `vector`
   (must be an existing key in `vectorTaxonomy` in `feed.json` — only add a
   new taxonomy key if you're tagging an item to it right now, per the
   README's note about dead-end filter chips), `text`, `link`, `linkLabel`,
   `published` (ISO 8601 UTC, current timestamp).
   **`published` must be the actual time of this run, never a future time.**
   Get it from the clock (`date -u +%Y-%m-%dT%H:%M:%SZ`) and space items a
   few seconds or minutes apart going backwards from it, never forwards.
   The RSS feed (feed.stingrayfraud.com) is read by Slack's RSS app, which
   only posts items newer than the newest date it has seen, so one
   future-dated item silently hides the next refresh's items from every
   subscribed channel.
   **No em-dashes (—) in `text`.** The site already renders a separator
   before each source link, and the Stingray voice doesn't use them. Use a
   comma, colon, semicolon, or parentheses instead.

5. **Update `feed.json`:**
   - Append new items to the appropriate array(s) (`ticker`/`marketplace`/`highrisk`).
   - Prune any item whose `published` is more than 90 days before now, from
     any of the three arrays.
   - **Set the top-level `featured` key** to the exact `link` of this run's
     featured item, chosen by step 9's rule (the single most
     attention-grabbing addition; prefer `highrisk` or `ticker`). Replace
     any previous value. The site's `this_week.sh` strip shows it as
     "biggest story", and step 9 uses the same item for the LinkedIn link.
     On a zero-item run, leave `featured` unchanged, even if the item it
     points to was just pruned: the site falls back on its own.
   - Re-sort each array by `published` descending.
   - Validate: `python3 -m json.tool feed.json > /dev/null` must succeed.
   - Validate no future dates (must print nothing and exit 0):
     ```bash
     python3 -c "import json,sys,datetime as d;n=d.datetime.now(d.timezone.utc)+d.timedelta(minutes=5);bad=[i['published'] for k in ('ticker','marketplace','highrisk') for i in json.load(open('feed.json')).get(k,[]) if d.datetime.fromisoformat(i['published'].replace('Z','+00:00'))>n];print(bad) if bad else None;sys.exit(1 if bad else 0)"
     ```
     If it fails, fix those `published` values to the current time before continuing.

6. **Update `archive.json`:**
   - Prepend the same new items (each with a `panel` field:
     `"ticker"`, `"marketplace"`, or `"highrisk"`) to the `items` array.
   - **Never remove, edit, or reorder existing entries.** This file is
     append-only by design — it's the one part of the site whose SEO value
     compounds over time instead of resetting weekly, and that only holds
     if nothing already in it is ever touched.
   - Validate: `python3 -m json.tool archive.json > /dev/null` must succeed.

7. **Commit and open a PR into `main`:**
   Your session runs on a dedicated branch and cannot push directly to
   `main` — that's a fixed platform restriction on this environment, not an
   error to work around. Don't attempt to force-push to `main`, merge it
   yourself, or fight the restriction. Instead:
   ```bash
   git add feed.json archive.json
   git commit -m "Weekly fraud signal refresh: <n> new items (<short description>)"
   git push -u origin "$(git branch --show-current)"
   gh pr create --base main \
     --title "Weekly fraud signal refresh: <n> new items" \
     --body "<one line per item added, tag + panel>"
   ```
   Write a real, specific commit message and PR title — what was actually
   added, not just "update feed." Capture the PR URL printed by
   `gh pr create` — you need it for step 9, and it's the whole point of
   this step: a merge Jared can do in one click instead of hunting for
   what happened.

8. **Confirm the PR is clean:**
   ```bash
   gh pr view --json mergeable,mergeStateStatus
   ```
   Expect `"mergeable": "MERGEABLE"`. The live site will not reflect these
   changes until the PR above is merged — that's expected at this stage,
   not a failure. Don't treat an unmerged PR as something to fix; it's the
   deliverable of this run.

9. **Build this week's shareable LinkedIn link.** Only if at least one item
   was added this run — skip this step entirely on a zero-item run.
   - Pick **one** item from this run's additions to feature: the single most
     attention-grabbing one — a concrete incident, a notable name, or a
     surprising number beats a generic trend stat. Prefer `highrisk` or
     `ticker` items over `marketplace` mechanics, which tend to read drier.
   - This must be the same item you set as `featured` in step 5.
   - Build a UTM-tagged link to the site's homepage (not a deep link to the
     specific item — the page's `og:url`/canonical tag is hardcoded to the
     bare domain with no query string, which strips both query params *and*
     hash anchors when link-preview crawlers like LinkedIn's read it, so a
     deep-link anchor would silently break; the bare homepage + UTM is what
     actually survives):
     ```
     https://watch.stingrayfraud.com/?utm_source=linkedin&utm_medium=social&utm_campaign=<slug>
     ```
     `<slug>` is a short, lowercase, hyphenated tag for the featured item's
     topic (e.g. `repeat_counterfeiter`, `asos_ato_breach`) — distinct enough
     that this week's link is identifiable from GA later, not identical to a
     prior week's.
   - Shorten it (LinkedIn's crawler otherwise reads the page's own `og:url`
     and silently drops your query string — see above; a shortener sidesteps
     this because there's nothing for LinkedIn to canonicalize away):
     ```bash
     curl -s "https://tinyurl.com/api-create.php?url=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "<the full utm url>")"
     ```
     No account or API key needed. Confirm it resolves correctly before
     using it:
     ```bash
     curl -sI "<the tinyurl output>" | grep -i location
     ```
     The `location` header should echo your full UTM URL back exactly. If it
     doesn't, don't guess — fall back to the plain (unshortened) UTM link in
     the email and note the shortening step failed.

10. **Email a run summary to `jared@stingrayfraud.com`** using the Gmail
    tool, every run, regardless of outcome. Subject line should make the
    outcome scannable at a glance, e.g. `Stingray Watch weekly refresh: 3 items
    added` or `Stingray Watch weekly refresh: 0 items added` or `Stingray Watch
    weekly refresh: FAILED at step N`. Body should lead with, in this order:
    1. `Merge to publish: <PR URL>` (from step 7), if a PR was opened.
    2. `This week's LinkedIn link: <shortened URL>` (from step 9), if one
       was built — say one line on which item it features and why you
       picked it.
    3. If a PR was opened: `After merging, tell Claude Code: "refresh the
       watch snapshot"`. This updates the static copy of the rows in the
       Carrd embeds (what search engines and link previews see), which
       doesn't update from the JSON on its own.

    Then include:
    - What was added: for each new item, its tag, one-line text, source
      link, and which panel (ticker/marketplace/highrisk).
    - If fewer than 2 items were added (including zero), a short honest note
      on why (e.g. "search returned mostly duplicates of items already
      posted this month" or "no sources cleared the verification bar this
      week") — don't leave this unexplained.
    - Confirmation that `feed.json`/`archive.json` both validated as JSON
      and the PR is mergeable, or the specific step/error if something failed.
    - If any step failed partway, say so plainly rather than reporting success.

## What NOT to do

- Don't touch anything outside `feed.json`/`archive.json` in this repo.
- Don't overwrite, reorder, or delete anything in `archive.json`.
- Don't skip the de-duplication check against existing entries.
- Don't invent a taxonomy vector, a link, or a statistic. If a claim or
  source can't be verified, leave it out.
- If you end up with fewer than 2 well-sourced, non-duplicate items this
  run, it's fine to post fewer (even zero) — do not lower your bar just to
  hit a target count.
- Don't attempt to push or merge directly to `main`, and don't treat the
  branch restriction as something to route around. Open the PR (step 7)
  and stop there — the merge is Jared's one click, by design.
