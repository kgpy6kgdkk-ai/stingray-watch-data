#!/usr/bin/env python3
"""Build the Stingray fraud glossary pages from glossary.json and archive.json.

Writes to the output directory (default: _site), next to the RSS feeds:
  glossary/index.html             a pattern board for the fraud vectors (Watch
                                  counts + sparklines) and an A-Z of every other term
  glossary/<slug>/index.html      one page per term
  glossary/glossary.css           shared styles
  sitemap.xml, robots.txt         for search engines

glossary.json is the source of truth for terms, categories and explainer copy.
Definitions match the glossary on watch.stingrayfraud.com. The 12 fraud-vector
terms get a monthly chart and a "recent on Watch" list from archive.json, which
is append-only, so the counts only ever grow. Diagrams live in diagrams/ and
are inlined so they pick up the page's light/dark colors.

Run after build_rss.py, which creates the output directory. Standard library
only, no dependencies.
"""
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://feed.stingrayfraud.com/"
BASE = SITE + "glossary/"
WATCH_URL = "https://watch.stingrayfraud.com/"
STINGRAY_URL = "https://stingrayfraud.com/"
SOP_URL = "https://steal.stingrayfraud.com/"
GA_ID = "G-NXWMK36PSF"  # same GA4 stream as Watch and the RSS landing page
LINKEDIN_PARTNER_ID = "9913956"
RECENT_LIMIT = 5
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def esc(s):
    return html.escape(str(s), quote=True)


def slug(s):
    # Same rule as Watch's fsGlossarySlug, so #glossary-<slug> deep links line up.
    s = re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return s[:80]


def utm(url, content):
    return "%s?utm_source=glossary&utm_medium=referral&utm_campaign=glossary&utm_content=%s" % (url, content)


def month_key(iso):
    return iso[:7]


def month_range(first, last):
    y, m = map(int, first.split("-"))
    ly, lm = map(int, last.split("-"))
    out = []
    while (y, m) <= (ly, lm):
        out.append("%04d-%02d" % (y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def month_label(key, with_year=False):
    y, m = key.split("-")
    return MONTHS[int(m) - 1] + (" " + y if with_year else "")


def nice_max(n):
    for step in (1, 2, 5, 10, 20, 50, 100):
        if n <= step * 4:
            top = -(-max(n, 1) // step) * step
            return top, step
    return n, n


# ---------------------------------------------------------------- charts


def month_chart(vector_name, months, counts):
    """Column chart: Watch items tagged with this vector, per month."""
    w, h, left, right, top, bottom = 560, 190, 30, 8, 22, 26
    pw, ph = w - left - right, h - top - bottom
    peak = max(counts) if counts else 0
    ymax, step = nice_max(peak)
    band = pw / max(len(months), 1)
    bw = min(44, band * 0.56)
    parts = ['<svg class="chart" viewBox="0 0 %d %d" role="img" aria-label="%s">' % (
        w, h, esc("Watch items tagged %s per month: %s" % (vector_name, ", ".join(
            "%s %d" % (month_label(m, True), c) for m, c in zip(months, counts)))))]
    for v in range(0, ymax + 1, step):
        y = top + ph - ph * v / ymax
        parts.append('<line class="grid" x1="%d" x2="%d" y1="%.1f" y2="%.1f"/>' % (left, w - right, y, y))
        parts.append('<text class="tick" x="%d" y="%.1f" text-anchor="end">%d</text>' % (left - 8, y + 4, v))
    last = len(months) - 1
    for i, (m, c) in enumerate(zip(months, counts)):
        cx = left + band * i + band / 2
        x = cx - bw / 2
        parts.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (
            cx, h - 8, month_label(m, i == 0 or m.endswith("-01"))))
        tip = "%s: %d item%s" % (month_label(m, True), c, "" if c == 1 else "s")
        # Wide invisible hit target so small bars are easy to hover.
        parts.append('<g class="hit" data-tip="%s"><rect class="target" x="%.1f" y="%d" width="%.1f" height="%d"/>' % (
            esc(tip), left + band * i, top, band, ph))
        if c:
            bh = ph * c / ymax
            y0 = top + ph
            r = min(4, bh)
            parts.append('<path class="bar" d="M%.1f %.1f V%.1f Q%.1f %.1f %.1f %.1f H%.1f Q%.1f %.1f %.1f %.1f V%.1f Z"/>' % (
                x, y0, y0 - bh + r, x, y0 - bh, x + r, y0 - bh, x + bw - r, x + bw, y0 - bh, x + bw, y0 - bh + r, y0))
            if c == peak or i == last:
                parts.append('<text class="val" x="%.1f" y="%.1f" text-anchor="middle">%d</text>' % (cx, y0 - bh - 6, c))
        parts.append("</g>")
    parts.append('<line class="axis" x1="%d" x2="%d" y1="%d" y2="%d"/>' % (left, w - right, top + ph, top + ph))
    parts.append("</svg>")
    rows = "".join("<tr><td>%s</td><td>%d</td></tr>" % (month_label(m, True), c) for m, c in zip(months, counts))
    table = ('<details class="numbers"><summary>see the numbers</summary><table><thead><tr><th>month</th>'
             '<th>items</th></tr></thead><tbody>%s</tbody></table></details>' % rows)
    return '<figure class="chart-wrap">%s%s</figure>' % ("".join(parts), table)


def sparkline(counts, peak, months):
    """Tiny trend line for the pattern board. All rows share one scale so they compare honestly."""
    w, h, p = 84, 26, 3
    n = len(counts)
    xs = [p + (i * (w - 2 * p) / (n - 1) if n > 1 else (w - 2 * p) / 2) for i in range(n)]
    ys = [h - p - (h - 2 * p) * c / max(peak, 1) for c in counts]
    pts = " ".join("%.1f,%.1f" % xy for xy in zip(xs, ys))
    tip = ", ".join("%s %d" % (month_label(m), c) for m, c in zip(months, counts))
    return ('<svg class="spark" viewBox="0 0 %d %d" role="img" aria-label="by month: %s"><title>by month: %s</title>'
            '<line class="base" x1="%d" x2="%d" y1="%d" y2="%d"/><path class="area" d="M%.1f,%d L%s L%.1f,%d Z"/>'
            '<polyline points="%s"/><circle cx="%.1f" cy="%.1f" r="2.6"/></svg>') % (
        w, h, tip, tip, p, w - p, h - p, h - p, xs[0], h - p, " L".join("%.1f,%.1f" % xy for xy in zip(xs, ys)),
        xs[-1], h - p, pts, xs[-1], ys[-1])


# One line icon per category (24px grid, stroke = currentColor).
ICONS = {
    "fraud-vectors": '<path d="M4 12a8 8 0 0 1 8 8"/><path d="M4 5a15 15 0 0 1 15 15"/><circle cx="5.5" cy="18.5" r="1.8" fill="currentColor" stroke="none"/>',
    "payments-and-cards": '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/><path d="M7 15h4"/>',
    "disputes-and-returns": '<path d="M4 9h12l-3-3"/><path d="M20 15H8l3 3"/>',
    "accounts-and-identity": '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/>',
    "scams-and-impersonation": '<path d="M12 3v9a4 4 0 1 1-4-4"/><path d="M8 8l-2 2"/>',
    "bots-and-detection": '<rect x="5" y="8" width="14" height="11" rx="2"/><path d="M12 4v4"/><circle cx="9.5" cy="13.5" r="1.2" fill="currentColor" stroke="none"/><circle cx="14.5" cy="13.5" r="1.2" fill="currentColor" stroke="none"/>',
    "a-z": '<path d="M5 5h14M5 10h14M5 15h9M5 20h6"/>',
}


def icon(key, size=16):
    return ('<svg class="ico" width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>') % (
        size, size, ICONS.get(key, ICONS["a-z"]))


DIAGRAM_DEFS = """<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="arrowhead" d="M0,0 L10,5 L0,10 z"/></marker>
<marker id="ahb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="arrowhead bad" d="M0,0 L10,5 L0,10 z"/></marker>
<marker id="ahm" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="arrowhead muted" d="M0,0 L10,5 L0,10 z"/></marker>
</defs></svg>"""


# ---------------------------------------------------------------- page shell

HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article"><meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}"><meta property="og:url" content="{canonical}">
<meta property="og:image" content="{site}icon-144.png">
<link rel="icon" href="{root}icon.svg" type="image/svg+xml">
<link rel="icon" href="{root}icon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="{root}apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="Stingray Watch" href="{site}rss.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="{root}glossary/glossary.css">
<script async src="https://www.googletagmanager.com/gtag/js?id={ga}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{ga}');</script>
<script type="text/javascript">_linkedin_partner_id="{li}";window._linkedin_data_partner_ids=window._linkedin_data_partner_ids||[];window._linkedin_data_partner_ids.push(_linkedin_partner_id);</script>
<script type="text/javascript">(function(l){{if(!l){{window.lintrk=function(a,b){{window.lintrk.q.push([a,b])}};window.lintrk.q=[]}}var s=document.getElementsByTagName("script")[0];var b=document.createElement("script");b.type="text/javascript";b.async=true;b.src="https://snap.licdn.com/li.lms-analytics/insight.min.js";s.parentNode.insertBefore(b,s);}})(window.lintrk);</script>
<script type="application/ld+json">{jsonld}</script>
</head><body>
<header class="bar"><div class="wrap">
  <a class="brand" href="{root}glossary/">stingray <span>glossary</span></a>
  <nav class="nav" aria-label="Stingray">
    <a href="{watch}" data-cta="nav_watch">watch</a>
    <a href="{root}glossary/">glossary</a>
    <a href="{site}">rss</a>
    <a href="{stingray}" data-cta="nav_stingray">stingray</a>
  </nav>
</div></header>
"""

FOOT = """<footer class="site-foot"><div class="wrap">
  <span>Stingray Fraud Intelligence · case management, rebuilt for investigators</span>
  <span><a href="{watch}">Stingray Watch</a> · <a href="{site}">rss</a> · <a href="{stingray}">stingrayfraud.com</a></span>
</div></footer>
<div class="gtip" id="tip" role="tooltip" hidden></div>
<script>
(function(){{
  function ev(n,p){{if(typeof gtag==='function')gtag('event',n,p||{{}});}}
  var page=document.body.getAttribute('data-term')||'index';
  var q=document.getElementById('q'),cat='all';
  function apply(){{
    var f=q.value.trim().toLowerCase(),any=false;
    document.querySelectorAll('[data-find]').forEach(function(el){{
      var c=el.getAttribute('data-cat');
      var hit=(!f||el.getAttribute('data-find').indexOf(f)>-1)&&(!c||cat==='all'||c===cat);el.hidden=!hit;if(hit)any=true;
    }});
    document.querySelectorAll('[data-group]').forEach(function(g){{
      var vis=g.querySelectorAll('[data-find]:not([hidden])').length;g.hidden=!vis;
      if(f&&vis&&g.tagName==='DETAILS')g.open=true;
    }});
    var nr=document.getElementById('noresults');if(nr)nr.hidden=any;
  }}
  if(q)q.addEventListener('input',apply);
  document.querySelectorAll('.cf').forEach(function(b){{b.addEventListener('click',function(){{
    cat=b.getAttribute('data-cf');document.querySelectorAll('.cf').forEach(function(x){{x.classList.toggle('on',x===b);}});apply();
    ev('glossary_filter',{{category:cat}});
  }});}});
  document.querySelectorAll('[data-rate] button').forEach(function(b){{
    b.addEventListener('click',function(){{
      b.parentNode.querySelectorAll('button').forEach(function(x){{x.setAttribute('aria-pressed',x===b?'true':'false');}});
      var t=b.parentNode.querySelector('.thanks');if(t)t.hidden=false;
      ev('glossary_helpful',{{term:page,answer:b.getAttribute('data-answer')}});
    }});
  }});
  document.querySelectorAll('a[data-cta]').forEach(function(a){{
    a.addEventListener('click',function(){{ev('glossary_cta',{{term:page,target:a.getAttribute('data-cta')}});}});
  }});
  var tip=document.getElementById('tip');
  document.querySelectorAll('[data-tip]').forEach(function(g){{
    function show(e){{tip.textContent=g.getAttribute('data-tip');tip.hidden=false;move(e);g.classList.add('on');}}
    function move(e){{var x=e.clientX,y=e.clientY;if(x===undefined){{var r=g.getBoundingClientRect();x=r.left+r.width/2;y=r.top;}}
      tip.style.left=Math.min(x+12,window.innerWidth-tip.offsetWidth-8)+'px';tip.style.top=(y-tip.offsetHeight-10)+'px';}}
    function hide(){{tip.hidden=true;g.classList.remove('on');}}
    g.addEventListener('mouseenter',show);g.addEventListener('mousemove',move);g.addEventListener('mouseleave',hide);
    g.addEventListener('focus',show);g.addEventListener('blur',hide);
  }});
}})();
</script>
</body></html>
"""


def shell(title, desc, canonical, jsonld, body, term_slug=""):
    head = HEAD.format(title=esc(title), desc=esc(desc), canonical=esc(canonical), site=SITE, root="/",
                       ga=GA_ID, li=LINKEDIN_PARTNER_ID, jsonld=json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/"),
                       watch=utm(WATCH_URL, "nav"), stingray=utm(STINGRAY_URL, "nav"))
    if term_slug:
        head = head.replace("<body>", '<body data-term="%s">' % esc(term_slug), 1)
    return head + body + FOOT.format(watch=utm(WATCH_URL, "footer"), site=SITE, stingray=utm(STINGRAY_URL, "footer"))


def short(text, n=155):
    text = " ".join(text.split())
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(",;:—-") + "..."


def search_band(heading, sub):
    return """<section class="band"><div class="wrap">
  <h1 class="band-title">%s</h1>
  <p>%s</p>
  <label class="search" for="q">
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="7" cy="7" r="5.2" stroke="currentColor" stroke-width="1.8"/><path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
    <input id="q" type="search" placeholder="search terms, like chargeback or ATO" autocomplete="off" aria-label="Search the glossary">
  </label>
</div></section>
""" % (heading, sub)


def sidebar(cats, by_cat, current):
    out = ['<aside class="side" aria-label="Glossary categories">'
           '<label class="search side-search" for="q"><input id="q" type="search" placeholder="search the glossary" '
           'autocomplete="off" aria-label="Search the glossary"></label><h2 class="side-h">categories</h2>']
    for c in cats:
        terms = by_cat[c["slug"]]
        is_open = any(slug(t["name"]) == current for t in terms)
        out.append('<details class="cat" data-group%s><summary><span class="cat-name">%s%s</span><span class="n">%d</span></summary><ul>' % (
            " open" if is_open else "", icon(c["slug"]), esc(c["name"]), len(terms)))
        for t in terms:
            s = slug(t["name"])
            out.append('<li data-find="%s"><a href="/glossary/%s/"%s>%s</a></li>' % (
                esc((t["name"] + " " + t["definition"]).lower()), s, ' aria-current="page"' if s == current else "", esc(t["name"])))
        out.append("</ul></details>")
    out.append('<p class="empty" id="noresults" hidden>no terms match that search.</p></aside>')
    return "".join(out)


def cta(term_slug):
    return """<div class="cta">
  <div><strong>solved one of these before?</strong><p>Stingray keeps the case, the pattern and what you figured out in one place, so the next analyst starts where you left off.</p></div>
  <div class="btns"><a class="btn primary" href="%s" data-cta="stingray">see how Stingray works</a><a class="btn ghost" href="%s" data-cta="sop">steal our chargebacks SOP</a></div>
</div>""" % (esc(utm(STINGRAY_URL, term_slug)), esc(utm(SOP_URL, term_slug)))


def foot_meta(updated):
    d = datetime.strptime(updated, "%Y-%m-%d")
    return """<div class="foot"><span>last updated %s %d, %d</span>
<div class="rate" data-rate><span>was this helpful?</span><button type="button" aria-pressed="false" data-answer="yes">yes</button><button type="button" aria-pressed="false" data-answer="no">no</button><span class="thanks" hidden>thanks, noted.</span></div></div>""" % (
        d.strftime("%B").lower(), d.day, d.year)


def related_cards(names, by_name):
    out = ['<ul class="related">']
    for n in names:
        t = by_name[n]
        out.append('<li><a href="/glossary/%s/"><b>%s</b><span>%s</span></a></li>' % (slug(n), esc(n), esc(t["definition"])))
    out.append("</ul>")
    return "".join(out)


def item_title(item):
    h = " ".join(str(item.get("headline", "")).split())
    return h or short(item.get("text", ""), 110)


# ---------------------------------------------------------------- pages


def term_page(t, ctx):
    s = slug(t["name"])
    cat = ctx["cat_by_slug"][t["category"]]
    ex = t.get("explainer") or {}
    vector = t.get("vector")
    body = []
    body.append(DIAGRAM_DEFS)
    body.append('<div class="wrap layout">')
    body.append(sidebar(ctx["cats"], ctx["by_cat"], s))
    body.append("<main>")
    body.append('<nav class="crumbs" aria-label="Breadcrumb"><a href="/glossary/">glossary</a><span>›</span>'
                '<a href="/glossary/#%s">%s</a><span>›</span><span>%s</span></nav>' % (cat["slug"], esc(cat["name"]), esc(t["name"])))
    body.append("<article>")
    body.append("<h1>%s</h1>" % esc(t["name"]))
    tags = ['<span class="tag">%s%s</span>' % (icon(cat["slug"], 12), esc(cat["name"]))]
    items = ctx["items_by_vector"].get(vector, []) if vector else []
    if vector:
        tags.append('<span class="tag code">%s</span>' % esc(vector))
        tags.append('<span class="tag code">%d item%s on Watch</span>' % (len(items), "" if len(items) == 1 else "s"))
    body.append('<div class="tags">%s</div>' % "".join(tags))
    body.append('<p class="def">%s</p>' % esc(t["definition"]))
    if ex.get("context"):
        body.append("<p>%s</p>" % esc(ex["context"]))

    if ex.get("steps"):
        body.append("<h2>how it plays out</h2>")
        if ex.get("diagram"):
            svg = (ctx["repo"] / "diagrams" / ex["diagram"]).read_text(encoding="utf-8")
            body.append('<figure class="diagram">%s<figcaption>the numbers match the steps below. '
                        'coral marks where the fraud happens.<span class="swipe"> swipe sideways to see all of it.</span></figcaption></figure>' % svg)
        body.append('<ol class="steps">')
        for st in ex["steps"]:
            body.append("<li><div><b>%s</b><p>%s</p></div></li>" % (esc(st["title"]), esc(st["body"])))
        body.append("</ol>")
    if ex.get("hard"):
        body.append('<div class="callout warn"><h3>why it\'s hard to catch</h3><p>%s</p></div>' % esc(ex["hard"]))
    if ex.get("lookFor"):
        body.append('<div class="callout tip"><h3>what analysts look for</h3><ul>%s</ul></div>' % "".join(
            "<li>%s</li>" % esc(x) for x in ex["lookFor"]))

    if vector:
        body.append("<h2>on Watch, month by month</h2>")
        body.append('<p class="chart-note">items tagged <b>%s</b> on Stingray Watch since %s.</p>' % (
            esc(t["name"]), month_label(ctx["months"][0], True)))
        counts = [ctx["month_counts"][vector].get(m, 0) for m in ctx["months"]]
        body.append(month_chart(t["name"], ctx["months"], counts))
        if items:
            body.append("<h2>recent on Watch</h2><ul class=\"watch\">")
            for it in items[:RECENT_LIMIT]:
                body.append('<li><time datetime="%s">%s</time><div><a href="%s" rel="noopener">%s</a>'
                            '<span class="src">%s</span></div></li>' % (
                                esc(it["published"][:10]), esc(it["published"][:10]), esc(it["link"]),
                                esc(item_title(it)), esc(it.get("linkLabel", ""))))
            body.append("</ul>")
        body.append('<p class="more"><a href="%s" data-cta="watch_vector">see everything new on Stingray Watch</a></p>' % esc(utm(WATCH_URL, s)))

    related = t.get("related") or [n["name"] for n in ctx["by_cat"][t["category"]] if n["name"] != t["name"]][:6]
    body.append("<h2>related terms</h2>")
    body.append(related_cards(related, ctx["by_name"]))
    body.append(cta(s))
    body.append(foot_meta(ctx["updated"]))
    body.append("</article></main></div>")

    if ex.get("steps"):
        title = "%s: how it works and what analysts look for | Stingray" % (t["name"][0].upper() + t["name"][1:])
    else:
        title = "What is %s? | Stingray fraud glossary" % t["name"]
    canonical = BASE + s + "/"
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "DefinedTerm", "@id": canonical + "#term", "name": t["name"], "description": t["definition"],
         "url": canonical, "inDefinedTermSet": {"@type": "DefinedTermSet", "@id": BASE + "#set",
                                                "name": "Stingray fraud glossary", "url": BASE}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "glossary", "item": BASE},
            {"@type": "ListItem", "position": 2, "name": cat["name"], "item": BASE + "#" + cat["slug"]},
            {"@type": "ListItem", "position": 3, "name": t["name"], "item": canonical}]}]}
    return shell(title, short(t["definition"]), canonical, jsonld, "".join(body), s)


def letter_of(name):
    ch = name[0].upper()
    return ch if ch.isalpha() else "#"


def index_page(ctx):
    """Reference-book index: a pattern board for the 12 vectors, then an A-Z of everything else."""
    vectors = [t for t in ctx["terms"] if t.get("vector")]
    others = sorted((t for t in ctx["terms"] if not t.get("vector")), key=lambda t: t["name"].lower())
    count = lambda t: len(ctx["items_by_vector"].get(t["vector"], []))
    vectors.sort(key=lambda t: (-count(t), t["name"]))
    months = ctx["months"]
    peak = max([count(t) for t in vectors] + [1])
    monthly = {t["vector"]: [ctx["month_counts"][t["vector"]].get(m, 0) for m in months] for t in vectors}
    spark_peak = max([max(v) for v in monthly.values()] + [1])
    span = "%s–%s" % (month_label(months[0]), month_label(months[-1]))

    body = [search_band("fraud glossary",
                        "%d fraud and trust &amp; safety terms, written the way fraud analysts actually use them. "
                        "read it top to bottom, or jump to a term." % len(ctx["terms"]))]
    body[0] = body[0].replace("</label>\n</div></section>",
                              '</label>\n  <div class="jump"><a href="#vectors">the %d fraud vectors</a>'
                              '<a href="#az">A–Z, %d more terms</a></div>\n</div></section>' % (len(vectors), len(others)))
    body.append('<main class="wrap index">')

    body.append('<section id="vectors"><h2 class="sec-h">%s fraud vectors <span class="n">%d</span></h2>' % (
        icon("fraud-vectors", 22), len(vectors)))
    body.append('<p class="sec-p">the patterns Stingray Watch tracks, busiest first. the bar is every item Watch has '
                'tagged since %s, the line is how it\'s moved month to month.</p>' % month_label(months[0], True))
    body.append('<ul class="board"><li class="board-head" aria-hidden="true"><span>pattern</span>'
                '<span>on Watch · %s</span><span>what it is</span></li>' % span)
    for t in vectors:
        c = count(t)
        body.append('<li class="vrow" data-find="%s"><a class="vname" href="%s/">%s</a>'
                    '<div class="vstat"><span class="track"><span class="fill" style="width:%.1f%%"></span></span>'
                    '<span class="num">%d</span>%s</div><p class="vdef">%s</p></li>' % (
                        esc((t["name"] + " " + t["definition"]).lower()), slug(t["name"]), esc(t["name"]),
                        100.0 * c / peak, c, sparkline(monthly[t["vector"]], spark_peak, months), esc(t["definition"])))
    body.append('</ul><div class="legend"><span><i></i>items tagged on Stingray Watch</span>'
                '<span>line: %s, dot = this month</span></div></section>' % span.replace("–", " → "))

    groups = {}
    for t in others:
        groups.setdefault(letter_of(t["name"]), []).append(t)
    alphabet = ["#"] + [chr(c) for c in range(65, 91)]
    anchor = lambda L: "l-num" if L == "#" else "l-" + L
    letters = "".join('<a href="#%s">%s</a>' % (anchor(L), L) if L in groups else "<span>%s</span>" % L for L in alphabet)
    filters = '<button type="button" class="cf on" data-cf="all">all</button>' + "".join(
        '<button type="button" class="cf" data-cf="%s">%s%s</button>' % (c["slug"], icon(c["slug"], 14), esc(c["name"]))
        for c in ctx["cats"] if any(t["category"] == c["slug"] for t in others))
    body.append('<section id="az"><h2 class="sec-h">%s glossary A–Z <span class="n">%d</span></h2>' % (icon("a-z", 22), len(others)))
    body.append('<p class="sec-p">the rest of the vocabulary: payments, disputes, identity, scams and detection.</p>')
    body.append('<div class="azbar"><nav class="letters" aria-label="Jump to letter">%s</nav>'
                '<div class="cfs" role="group" aria-label="Filter by category">%s</div></div>' % (letters, filters))
    for L in alphabet:
        if L not in groups:
            continue
        body.append('<section class="letter" id="%s" data-group><h3>%s</h3><dl>' % (anchor(L), L))
        for t in groups[L]:
            c = ctx["cat_by_slug"][t["category"]]
            body.append('<div class="entry" data-find="%s" data-cat="%s"><dt><a href="%s/">%s</a>'
                        '<span class="chip">%s%s</span></dt><dd>%s</dd></div>' % (
                            esc((t["name"] + " " + t["definition"]).lower()), c["slug"], slug(t["name"]), esc(t["name"]),
                            icon(c["slug"], 13), esc(c["name"]), esc(t["definition"])))
        body.append("</dl></section>")
    body.append('<p class="empty" id="noresults" hidden>no terms match that search.</p></section>')
    body.append(cta("index"))
    body.append("</main>")
    jsonld = {"@context": "https://schema.org", "@type": "DefinedTermSet", "@id": BASE + "#set",
              "name": "Stingray fraud glossary", "url": BASE,
              "description": "E-commerce fraud and trust & safety terms for fraud analysts.",
              "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t["name"], "description": t["definition"],
                                  "url": BASE + slug(t["name"]) + "/"} for t in ctx["terms"]]}
    return shell("Fraud glossary: e-commerce fraud and trust & safety terms | Stingray",
                 "Plain-English definitions of %d e-commerce fraud and trust & safety terms, from account takeover to "
                 "triangulation fraud, with how each scheme plays out and what fraud analysts look for." % len(ctx["terms"]),
                 BASE, jsonld, "".join(body))


def main():
    repo = Path(__file__).resolve().parent.parent
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / "_site"
    gloss = json.loads((repo / "glossary.json").read_text(encoding="utf-8"))
    archive = json.loads((repo / "archive.json").read_text(encoding="utf-8"))["items"]
    now = datetime.now(timezone.utc)

    cats = gloss["categories"]
    terms = gloss["terms"]
    by_name = {t["name"]: t for t in terms}
    by_cat = {c["slug"]: [t for t in terms if t["category"] == c["slug"]] for c in cats}
    items = sorted(archive, key=lambda i: i["published"], reverse=True)
    items_by_vector, month_counts = {}, {}
    for it in items:
        v = it.get("vector")
        items_by_vector.setdefault(v, []).append(it)
        month_counts.setdefault(v, Counter())[month_key(it["published"])] += 1
    first = min(month_key(i["published"]) for i in items) if items else now.strftime("%Y-%m")
    months = month_range(first, now.strftime("%Y-%m"))
    for t in terms:
        month_counts.setdefault(t.get("vector"), Counter())

    ctx = dict(repo=repo, cats=cats, terms=terms, by_name=by_name, by_cat=by_cat, updated=gloss["updated"],
               cat_by_slug={c["slug"]: c for c in cats}, items_by_vector=items_by_vector,
               month_counts=month_counts, months=months)

    gdir = out_dir / "glossary"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "glossary.css").write_text((repo / "scripts" / "glossary.css").read_text(encoding="utf-8"), encoding="utf-8")
    (gdir / "index.html").write_text(index_page(ctx), encoding="utf-8")
    urls = [(BASE, gloss["updated"])]
    for t in terms:
        d = gdir / slug(t["name"])
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(term_page(t, ctx), encoding="utf-8")
        urls.append((BASE + slug(t["name"]) + "/", gloss["updated"]))
    print("glossary: %d term pages" % len(terms))

    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
          "  <url><loc>%s</loc></url>" % SITE]
    sm += ["  <url><loc>%s</loc><lastmod>%s</lastmod></url>" % (esc(u), d) for u, d in urls]
    sm.append("</urlset>")
    (out_dir / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    (out_dir / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n" % SITE, encoding="utf-8")


if __name__ == "__main__":
    main()
