#!/usr/bin/env python3
"""Build the Stingray fraud glossary pages from glossary.json and archive.json.

Writes to the output directory (default: _site), next to the RSS feeds:
  glossary/index.html             every term, grouped by category, with a chart
                                  of Watch items per fraud vector
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


def vector_chart(rows):
    """Horizontal bars: Watch items per fraud vector, all time. rows = [(term, count)] sorted desc."""
    w, label_w, bar_h, gap, right = 620, 210, 18, 10, 40
    h = len(rows) * (bar_h + gap) + 6
    peak = max(c for _, c in rows) or 1
    pw = w - label_w - right
    parts = ['<svg class="chart" viewBox="0 0 %d %d" role="img" aria-label="%s">' % (
        w, h, esc("Watch items per fraud vector: " + ", ".join("%s %d" % (t["name"], c) for t, c in rows)))]
    for i, (t, c) in enumerate(rows):
        y = 4 + i * (bar_h + gap)
        bw = max(pw * c / peak, 3 if c else 0)
        tip = "%s: %d item%s" % (t["name"], c, "" if c == 1 else "s")
        parts.append('<a href="%s/" class="hit" data-tip="%s">' % (slug(t["name"]), esc(tip)))
        parts.append('<rect class="target" x="0" y="%d" width="%d" height="%d"/>' % (y - gap / 2, w, bar_h + gap))
        parts.append('<text class="cat" x="%d" y="%d" text-anchor="end">%s</text>' % (label_w - 12, y + 13, esc(t["name"])))
        if c:
            r = min(4, bw)
            x0 = label_w
            parts.append('<path class="bar" d="M%d %d H%.1f Q%.1f %d %.1f %d V%d Q%.1f %d %.1f %d H%d Z"/>' % (
                x0, y, x0 + bw - r, x0 + bw, y, x0 + bw, y + r, y + bar_h - r, x0 + bw, y + bar_h, x0 + bw - r, y + bar_h, x0))
        parts.append('<text class="val" x="%.1f" y="%d">%d</text>' % (label_w + bw + 6, y + 13, c))
        parts.append("</a>")
    parts.append('<line class="axis" x1="%d" x2="%d" y1="0" y2="%d"/>' % (label_w, label_w, h))
    parts.append("</svg>")
    return '<figure class="chart-wrap wide">%s</figure>' % "".join(parts)


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
  var q=document.getElementById('q');
  if(q)q.addEventListener('input',function(){{
    var f=q.value.trim().toLowerCase(),any=false;
    document.querySelectorAll('[data-find]').forEach(function(el){{
      var hit=!f||el.getAttribute('data-find').indexOf(f)>-1;el.hidden=!hit;if(hit)any=true;
    }});
    document.querySelectorAll('[data-group]').forEach(function(g){{
      var vis=g.querySelectorAll('[data-find]:not([hidden])').length;g.hidden=!vis;
      if(f&&vis&&g.tagName==='DETAILS')g.open=true;
    }});
    var nr=document.getElementById('noresults');if(nr)nr.hidden=any;
  }});
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
        out.append('<details class="cat" data-group%s><summary>%s<span class="n">%d</span></summary><ul>' % (
            " open" if is_open else "", esc(c["name"]), len(terms)))
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
    tags = ['<span class="tag">%s</span>' % esc(cat["name"])]
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


def index_page(ctx):
    body = [search_band("fraud glossary",
                        "%d fraud and trust &amp; safety terms, written the way fraud analysts actually use them. "
                        "the 12 fraud vectors link to what's showing up on Stingray Watch." % len(ctx["terms"]))]
    body.append('<div class="wrap index">')
    rows = sorted(((t, len(ctx["items_by_vector"].get(t["vector"], []))) for t in ctx["terms"] if t.get("vector")),
                  key=lambda r: (-r[1], r[0]["name"]))
    body.append('<section class="panel"><h2>what Watch has been tracking</h2>'
                '<p class="chart-note">items on Stingray Watch by fraud vector, since %s. tap a bar to open that term.</p>%s</section>' % (
                    month_label(ctx["months"][0], True), vector_chart(rows)))
    for c in ctx["cats"]:
        body.append('<section class="group" id="%s" data-group><h2>%s <span class="n">%d</span></h2><p class="intro">%s</p><ul class="cards">' % (
            c["slug"], esc(c["name"]), len(ctx["by_cat"][c["slug"]]), esc(c["intro"])))
        for t in ctx["by_cat"][c["slug"]]:
            body.append('<li data-find="%s"><a href="%s/"><b>%s</b><span>%s</span></a></li>' % (
                esc((t["name"] + " " + t["definition"]).lower()), slug(t["name"]), esc(t["name"]), esc(t["definition"])))
        body.append("</ul></section>")
    body.append('<p class="empty" id="noresults" hidden>no terms match that search.</p>')
    body.append(cta("index"))
    body.append("</div>")
    jsonld = {"@context": "https://schema.org", "@type": "DefinedTermSet", "@id": BASE + "#set",
              "name": "Stingray fraud glossary", "url": BASE,
              "description": "E-commerce fraud and trust & safety terms for fraud analysts.",
              "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t["name"], "url": BASE + slug(t["name"]) + "/"}
                                 for t in ctx["terms"]]}
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
