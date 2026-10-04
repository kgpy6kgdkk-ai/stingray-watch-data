#!/usr/bin/env python3
"""Build Stingray Watch RSS feeds from feed.json.

Writes to the output directory (default: _site):
  rss.xml                   every item in the 90-day window
  rss-industry-news.xml     ticker panel only
  rss-marketplace.xml       marketplace panel only
  rss-high-risk-items.xml   highrisk panel only
  index.html                small landing page listing the feeds
  CNAME                     custom domain for GitHub Pages

Item links point at the item's deep link on watch.stingrayfraud.com, using the
same entry-id rule as the Watch page (fsEntryId), so the page scrolls to and
highlights the item. Standard library only, no dependencies.
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

WATCH_URL = "https://watch.stingrayfraud.com/"
FEED_HOST = "feed.stingrayfraud.com"
FEED_BASE = "https://" + FEED_HOST + "/"
UTM = "utm_source=rss&utm_medium=rss&utm_campaign=watch_feed"
WINDOW_DAYS = 90

# Same panel order the Watch page renders in; entry-id de-duplication depends on it.
PANELS = [
    ("ticker", "industry news", "rss-industry-news.xml"),
    ("marketplace", "marketplace", "rss-marketplace.xml"),
    ("highrisk", "high-risk items", "rss-high-risk-items.xml"),
]


def parse_date(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return s[:80]


def title_for(item, limit=90):
    text = " ".join(str(item.get("text", "")).split())
    if len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0]
        text = cut.rstrip(",;:") + "..."
    return "[%s] %s" % (item.get("tag", ""), text)


def collect(feed, now):
    """Return items in Watch render order, each annotated with panel and entry id."""
    used = set()
    out = []
    cutoff = now - timedelta(days=WINDOW_DAYS)
    for key, label, _ in PANELS:
        items = [i for i in feed.get(key, []) if parse_date(i["published"]) >= cutoff]
        items.sort(key=lambda i: parse_date(i["published"]), reverse=True)
        for item in items:
            base = slug("%s %s" % (item.get("tag", ""), item.get("text", ""))) or "entry"
            entry_id, n = base, 2
            while entry_id in used:
                entry_id = "%s-%d" % (base, n)
                n += 1
            used.add(entry_id)
            out.append(dict(item, _panel=key, _panel_label=label, _id=entry_id))
    return out


def item_xml(item, taxonomy):
    link = "%s?%s#%s" % (WATCH_URL, UTM, item["_id"])
    vector = taxonomy.get(item.get("vector"), "")
    body = '<p>%s</p><p>source: <a href="%s">%s</a> &middot; %s</p>' % (
        escape(item.get("text", "")),
        escape(item.get("link", ""), {'"': "&quot;"}),
        escape(item.get("linkLabel", "") or "source"),
        escape(item["_panel_label"]),
    )
    cats = [item["_panel_label"]] + ([vector] if vector else [])
    return "\n".join([
        "    <item>",
        "      <title>%s</title>" % escape(title_for(item)),
        "      <link>%s</link>" % escape(link),
        '      <guid isPermaLink="false">stingray-watch:%s</guid>' % escape(item["_id"]),
        "      <pubDate>%s</pubDate>" % format_datetime(parse_date(item["published"])),
        "".join("      <category>%s</category>\n" % escape(c) for c in cats).rstrip("\n"),
        "      <description><![CDATA[%s]]></description>" % body.replace("]]>", "]]&gt;"),
        "    </item>",
    ])


def channel_xml(title, description, filename, items, taxonomy, now):
    head = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        "    <title>%s</title>" % escape(title),
        "    <link>%s</link>" % WATCH_URL,
        "    <description>%s</description>" % escape(description),
        "    <language>en-us</language>",
        "    <lastBuildDate>%s</lastBuildDate>" % format_datetime(now),
        "    <ttl>720</ttl>",
        '    <atom:link href="%s%s" rel="self" type="application/rss+xml"/>' % (FEED_BASE, filename),
    ]
    body = [item_xml(i, taxonomy) for i in items]
    return "\n".join(head + body + ["  </channel>", "</rss>", ""])


INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stingray Watch RSS feeds</title>
<style>body{{margin:0;background:#000;color:#E1F5EE;font:14px/1.6 ui-monospace,monospace;padding:32px 16px}}
main{{max-width:640px;margin:0 auto}}h1{{color:#39FF14;font-weight:500;font-size:22px}}a{{color:#4FB37A}}li{{margin:6px 0}}</style>
</head><body><main>
<h1>stingray watch rss</h1>
<p>chargeback trends, fraud patterns, and industry news from <a href="{watch}">stingray watch</a>, updated twice a week. paste a feed url into your reader, or into slack's rss app to post new items to a channel.</p>
<ul>
{links}
</ul>
</main></body></html>
"""


def main():
    repo = Path(__file__).resolve().parent.parent
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / "_site"
    out_dir.mkdir(parents=True, exist_ok=True)
    feed = json.loads((repo / "feed.json").read_text(encoding="utf-8"))
    taxonomy = feed.get("vectorTaxonomy", {})
    now = datetime.now(timezone.utc).replace(microsecond=0)
    items = collect(feed, now)
    newest_first = sorted(items, key=lambda i: parse_date(i["published"]), reverse=True)

    feeds = [("rss.xml", "Stingray Watch", "all panels", newest_first)]
    for key, label, filename in PANELS:
        feeds.append((filename, "Stingray Watch: " + label, label,
                      [i for i in newest_first if i["_panel"] == key]))

    links = []
    for filename, title, label, its in feeds:
        desc = "Chargeback trends, fraud patterns, and e-commerce fraud signals (%s), sourced and updated twice a week." % label
        (out_dir / filename).write_text(channel_xml(title, desc, filename, its, taxonomy, now), encoding="utf-8")
        links.append('<li><a href="%s">%s</a> (%s, %d items)</li>' % (filename, filename, label, len(its)))
        print("%s: %d items" % (filename, len(its)))

    (out_dir / "index.html").write_text(INDEX_HTML.format(watch=WATCH_URL, links="\n".join(links)), encoding="utf-8")
    (out_dir / "CNAME").write_text(FEED_HOST + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
