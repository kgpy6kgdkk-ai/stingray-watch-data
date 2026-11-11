#!/usr/bin/env python3
"""Build the Stingray guides on feed.stingrayfraud.com/guides/.

Writes, next to the glossary:
  guides/index.html                       the list of guides
  guides/fraud-case-tracker/index.html    free fraud case tracker template + "signs you've outgrown it"
  guides/guides.css                       guide styles (loaded after glossary/glossary.css)

build_glossary.py calls build() from its main(), so the GitHub Pages workflow needs
no extra step, and the returned URLs go into the same sitemap.xml. Pages use the
glossary's shell(): same top bar, GA4 and LinkedIn Insight Tag.

The tracker file itself is NOT in this repo (this repo is public, and the file sits
behind the form on steal.stingrayfraud.com). Every "get the template" button goes to
that form's #tracker section. Standard library only, no dependencies.
"""
from pathlib import Path

from build_glossary import (DIAGRAM_DEFS, SITE, SITE_FOOT, SOP_URL, STINGRAY_URL, esc, foot_meta,
                            related_cards, shell)

GUIDES = SITE + "guides/"
STEAL_URL = "https://steal.stingrayfraud.com/"


def link(url, guide, content, anchor=""):
    """UTM-tag an outbound link (the hash goes after the query string, so Carrd still scrolls to the section)."""
    return "%s?utm_source=guides&utm_medium=referral&utm_campaign=%s&utm_content=%s%s" % (
        url, guide.replace("-", "_"), content, "#" + anchor if anchor else "")


# ---------------------------------------------------------------- shared footer script
# Guide events: guide_cta {guide, target} on any [data-cta] link, guide_helpful {guide, answer}.
GUIDE_FOOT = SITE_FOOT + """<script>
(function(){{
  function ev(n,p){{if(typeof gtag==='function')gtag('event',n,p||{{}});}}
  var guide=document.body.getAttribute('data-guide')||'index';
  document.querySelectorAll('a[data-cta]').forEach(function(a){{
    a.addEventListener('click',function(){{ev('guide_cta',{{guide:guide,target:a.getAttribute('data-cta')}});}});
  }});
  document.querySelectorAll('[data-rate] button').forEach(function(b){{
    b.addEventListener('click',function(){{
      b.parentNode.querySelectorAll('button').forEach(function(x){{x.setAttribute('aria-pressed',x===b?'true':'false');}});
      var t=b.parentNode.querySelector('.thanks');if(t)t.hidden=false;
      ev('guide_helpful',{{guide:guide,answer:b.getAttribute('data-answer')}});
    }});
  }});
  var box=document.getElementById('tk-check'),out=document.getElementById('tk-count');
  if(box&&out){{
    var total=box.querySelectorAll('input').length;
    box.addEventListener('change',function(){{out.textContent=box.querySelectorAll('input:checked').length+' of '+total+' true';}});
  }}
}})();
</script>
</body></html>
"""


def page(title, desc, canonical, jsonld, body, guide_slug="index"):
    html = shell(title, desc, canonical, jsonld, body, brand=("guides", "/guides/"),
                 extra_css="/guides/guides.css", foot=GUIDE_FOOT)
    return html.replace("<body>", '<body data-guide="%s">' % esc(guide_slug), 1)


# ---------------------------------------------------------------- fraud case tracker

TRACKER = {
    "slug": "fraud-case-tracker",
    "name": "free fraud case tracker",
    "updated": "2026-11-10",
    "title": "Free Fraud Case Tracker Template for Fraud Analysts",
    "desc": "A free fraud case tracker spreadsheet with a patterns tab, decision log and weekly view. No macros. "
            "Plus the signs you've outgrown it.",
    "h1": "A free fraud case tracker, and how to tell when you've outgrown it",
    "file": "fraud-case-tracker.xlsx · ~95 KB",
    # SHA-256 of the exact file uploaded behind the steal form (Freddy S11). Rebuilding the file changes it,
    # so update this whenever the file is replaced.
    "sha256": "9ddedd2ee6f5fde000dc8b1675256ddc7ea564596c40968b8f3e08cfba926d7d",
    # Reciprocal links: each of these term pages carries a "guide" line pointing here (glossary.json).
    "related": ["chargebacks & disputes", "friendly fraud", "first-party fraud", "refund abuse", "representment",
                "chargeback ratio"],
}

# Cases columns in the file's order, grouped the way the work runs (Freddy's review).
CASE_GROUPS = [
    ("who, what and when", [
        ("Case ID", ""), ("Opened date", ""),
        ("Source", "alert, chargeback, customer report, manual review, internal referral"),
        ("Fraud type", "stolen card (third-party), account takeover, card testing, friendly or first-party fraud, "
                       "triangulation, promo abuse, refund abuse, marketplace seller fraud, ACH or bank fraud, other"),
        ("Priority", ""), ("Owner", ""), ("Status", "new, investigating, waiting, escalated, closed"),
        ("Escalated to", "legal, payments, law enforcement, a senior analyst")]),
    ("links and signals", [
        ("Order or account reference", "your internal ID"), ("Amount at risk", ""),
        ("Linked signals", "email domain, device, IP, shipping address, recorded as internal references"),
        ("Related case IDs", "cases that look like the same person or ring"), ("Linked pattern ID", ""),
        ("Evidence location", "a ticket or folder reference, not the evidence itself")]),
    ("chargeback block, optional", [
        ("Due date", "turns coral 3 days out"), ("Dispute reason code", ""),
        ("Dispute stage", "inquiry through arbitration, then won, lost or accepted"), ("Customer contacted", "yes or no")]),
    ("decision and money", [
        ("Decision", "confirmed fraud, likely fraud, not fraud, inconclusive"), ("Action taken", ""),
        ("Loss", "gross, before anything comes back"), ("Recovered", "money back after a loss"),
        ("Prevented", "loss stopped before it happened"), ("Closed date", ""), ("Days open", "calc"),
        ("Next step and notes", "")]),
]

# Same fictional rows as the Patterns tab in the file.
SAMPLE_PATTERNS = [
    ("SAMPLE-P-001", "New accounts, shared reshipper address", "Several new accounts ship to the same forwarding address.",
     "A college dorm, a family or an office sharing one address. Older accounts with normal order history point that way.",
     "Link the accounts, review open orders, record the outcome on each case.", 1, "active"),
    ("SAMPLE-P-002", 'Repeat "item not received" claims', "Same customer, repeated not-received claims across orders.",
     "Real porch theft in one area. Check the carrier's delivery scan and photo before deciding.",
     "Pull delivery evidence, check claim history, decide and log the reason.", 2, "active"),
    ("SAMPLE-P-003", "Promo code reused across linked accounts",
     "One promo redeemed by accounts that share a device or payment reference.",
     "Family members sharing one laptop, each with a single normal order.",
     "Link the accounts, review the redemptions, note the action taken.", 1, "dormant"),
]

# Same wording as the Start here tab (Freddy's review, M4 and S10).
HYGIENE = [
    ("never", "Full card numbers, CVV, bank account numbers, government IDs, passwords, one-time codes or reset links."),
    ("avoid", "Names, emails, phone numbers, full addresses and raw IPs. Use your internal order, account and reference IDs."),
    ("fine", "Your internal IDs, an email domain, a card's last 4 digits, a country or city."),
    ("watch out for", "Version history: deleting a pasted card number doesn't remove it, because Google Sheets and "
                      "OneDrive keep old versions. Suspicious links: write them defanged (hxxps://example[.]com). Pasted "
                      "exports: paste as values only, because fraudsters plant formulas (starting with = or @) in names "
                      "and notes on purpose."),
    ("the Patterns tab", "It describes how you catch fraud. Treat the file as confidential, share it with your team only, "
                         "and leave out exact rule thresholds, score cut-offs and rule IDs."),
]

SIGNS = [
    "You solved the same pattern twice, because the first write-up lived in a row nobody could find.",
    "A new analyst asks the most senior person on the team instead of checking the sheet, because asking is faster.",
    'Someone asks "who changed this decision, and why?" and there\'s no answer anywhere.',
    "The evidence for a case lives in Slack threads and screenshots, not on the case itself.",
    "Two people edited at the same time and a filter or a formula quietly broke, and you found out later.",
]


def tab(n, name, text, extra="", heart=False, anchor=""):
    return '<div class="tk-tab%s"%s><span class="tk-num">%d</span><div><h3>%s</h3><p>%s</p>%s</div></div>' % (
        " heart" if heart else "", ' id="%s"' % anchor if anchor else "", n, name, text, extra)


def tracker_page(ctx, repo):
    g = TRACKER
    s = g["slug"]
    get = lambda where: esc(link(STEAL_URL, s, where, "tracker"))
    cols = "".join(
        '<h4 class="tk-group%s">%s</h4><ul class="tk-cols">%s</ul>' % (
            " opt" if "optional" in group else "", esc(group),
            "".join('<li%s><b>%s</b>%s</li>' % (' class="calc"' if note == "calc" else "", esc(name),
                                                " <span>%s</span>" % esc(note) if note and note != "calc" else "")
                    for name, note in items))
        for group, items in CASE_GROUPS)
    rows = "".join(
        '<tr><td class="id" data-label="Pattern ID">%s</td><td data-label="Pattern name">%s</td>'
        '<td data-label="Identifying signals">%s</td><td data-label="Legit look-alikes">%s</td>'
        '<td data-label="Playbook">%s</td><td class="c" data-label="Linked cases">%d</td>'
        '<td data-label="Status">%s</td></tr>' % (esc(pid), esc(name), esc(sig), esc(alike), esc(play), n, esc(st))
        for pid, name, sig, alike, play, n, st in SAMPLE_PATTERNS)
    signs = "".join('<li><label><input type="checkbox"><span>%s</span></label></li>' % esc(x) for x in SIGNS)
    diagram = (repo / "diagrams" / "case-to-pattern.svg").read_text(encoding="utf-8")

    body = [DIAGRAM_DEFS, '<div class="wrap layout">']
    body.append("""<aside class="side"><div class="tk-sticky">
  <h2 class="side-h">on this page</h2>
  <ol class="tk-toc">
    <li><a href="#inside"><span class="n">01</span>what's in the tracker</a></li>
    <li><a href="#patterns"><span class="n">02</span>the patterns tab</a></li>
    <li><a href="#data"><span class="n">03</span>what goes in the sheet</a></li>
    <li><a href="#outgrown"><span class="n">04</span>signs you've outgrown it</a></li>
  </ol>
  <div class="tk-side-cta">
    <b>fraud case tracker.xlsx</b>
    <span class="tk-meta">6 tabs · no macros · free</span><br>
    <a class="btn primary" href="%s" data-cta="tracker_get_side">get the template</a>
  </div>
</div></aside>""" % get("side"))
    body.append("<main>")
    body.append('<nav class="crumbs" aria-label="Breadcrumb"><a href="/guides/">guides</a><span>›</span>'
                '<span>fraud case tracker</span></nav>')
    body.append("<article>")
    body.append("<h1>%s</h1>" % esc(g["h1"]))
    body.append('<div class="tags"><span class="tag">guide</span><span class="tag code">.xlsx · 6 tabs · no macros</span></div>')
    body.append("""<p class="tk-lede">A spreadsheet is a perfectly good place to run fraud cases. It's free, it's fast, everyone on the team already knows how to use one, and when you're a team of one to three working a manageable number of cases, it does the job without asking anyone for budget.</p>
<p>Most trackers stop at the cases, though, and that's where the real cost hides. You close a case, the row scrolls out of view, and six months later someone works the same pattern from scratch because the first write-up lived in a cell nobody thought to search. So we built the tracker we'd have wanted on our first fraud team, with a tab for the patterns behind the cases, not just the cases themselves.</p>
<p>It's free, it's yours to change, and you can see every tab below before you download anything.</p>""")
    body.append('<div class="tk-get"><a class="btn primary" href="%s" data-cta="tracker_get_top">get the template</a>'
                '<span class="tk-meta">%s</span></div>' % (get("top"), esc(g["file"])))
    body.append('<p class="tk-gate">The download sits behind a short form on steal.stingrayfraud.com: a name, any email '
                'and a tick to say we can email you, then the file.</p>')

    body.append('<h2 id="inside">what\'s in the tracker</h2>')
    body.append("<p>One .xlsx file with six tabs. No macros, no external links, nothing your security team has to think "
                "twice about before opening.</p>")
    body.append('<div class="tk-official"><p><b>The official file is .xlsx only, with no macros.</b> If you were sent a '
                '.xlsm, a .zip or anything that asks you to enable content, it isn\'t from us.</p>'
                '<p class="tk-hash"><span>SHA-256</span><code>%s</code></p></div>' % esc(g["sha256"]))
    body.append(tab(1, "Start here", "What each tab is for, what every column means, and a short note on keeping "
                                     "sensitive data out of a shared file."))
    body.append(tab(2, "Cases", "One row per case, from the moment it's opened to the decision and what was recovered, "
                                "with the columns in the order you work a case. The chargeback block is grouped, so a "
                                "team that doesn't work disputes can fold it away with one click. The columns:", cols))
    body.append(tab(3, 'Patterns <span class="tk-pill">the heart of it</span>',
                    "This is the tab most trackers don't have, and the one we'd keep if we could only keep one. Each row "
                    "is a pattern your team has worked out: when you first and last saw it, the signals that identify it, "
                    "how it was confirmed, the steps that worked, and who figured it out. A linked case count pulls from "
                    "the Cases tab, so you can see which patterns keep coming back, and a status column marks each one "
                    "active or dormant. When a new analyst asks \"have we seen this before?\", this is where the answer "
                    "should live.", '<p>Each pattern also gets its legit look-alikes, the innocent customers who can '
                    'look like it and how to tell them apart, and a last reviewed date that turns yellow when an active '
                    'playbook hasn\'t been checked in 90 days. First seen and last seen fill themselves in from the '
                    'linked cases.</p>', heart=True, anchor="patterns"))
    body.append("""<figure class="tk-sheet" aria-label="Preview of the Patterns tab with the template's sample rows">
  <div class="tk-sheet-bar" aria-hidden="true"><span>Start here</span><span>Cases</span><span class="on">Patterns</span><span>Decision log</span><span>Weekly view</span><span>Lists</span></div>
  <div class="tk-scroll" tabindex="0" aria-label="Patterns tab, scrolls sideways">
  <table><thead><tr><th>Pattern ID</th><th>Pattern name</th><th>Identifying signals</th><th>Legit look-alikes</th><th>Playbook</th><th>Linked<br>cases</th><th>Status</th></tr></thead>
  <tbody>%s</tbody></table>
  </div>
</figure>
<p class="tk-cap">The Patterns tab with the template's sample rows. The file also has fraud type, first seen, last seen, how it was confirmed, worked out by and last reviewed. Grey cells calculate themselves.</p>""" % rows)
    body.append('<figure class="diagram">%s<figcaption>How cases link to patterns inside the tracker.'
                '<span class="swipe"> swipe sideways to see all of it.</span></figcaption></figure>' % diagram)
    body.append(tab(4, "Decision log", "Timestamp, case ID, who decided, the decision it changed from and to, why, the "
                                       "evidence it was based on, and who approved it. The first decision gets logged "
                                       "too, not just later changes. In a spreadsheet you fill this in by hand, and "
                                       "we'll be honest that it only works if everyone remembers to do it, but a team "
                                       "that keeps it can answer \"why did we close this?\" months later."))
    body.append(tab(5, "Weekly view", "Formulas only, nothing to type: what's due in the next 7 days and what's past "
                                      "due, open cases by status and fraud type, average days open, gross loss, "
                                      "recovered, net loss and prevented on confirmed fraud, not-fraud decisions by "
                                      "source (your false positives), and the patterns with the most linked cases. It's "
                                      "the page you'd screenshot for a Monday check-in."))
    body.append(tab(6, "Lists", "Every dropdown value in one place, so you can rename statuses or add a fraud type that "
                                "fits your business without touching a formula."))
    body.append('<div class="callout tip"><h3>sample rows</h3><p>The sample rows are clearly fictional (example.com '
                'addresses, IDs marked SAMPLE), so delete them and start fresh.</p></div>')

    body.append('<h2 id="data">a note on what goes in the sheet</h2>')
    body.append("<p>A shared spreadsheet is the wrong place for full card numbers, government IDs or a customer's full "
                "personal details. The tracker is built around your internal order and account IDs, so the detail stays "
                "in the systems designed to protect it and the sheet holds the investigation. The Start here tab spells "
                "it out:</p>")
    body.append('<div class="callout warn"><h3>keep sensitive data out of the file</h3><dl class="tk-hygiene">%s</dl></div>' % "".join(
        "<div><dt>%s</dt><dd>%s</dd></div>" % (esc(k), esc(v)) for k, v in HYGIENE))

    body.append('<h2 id="outgrown">signs you\'ve outgrown it</h2>')
    body.append("<p>None of these mean you did anything wrong, they just mean the team grew faster than the file did. "
                "Count how many are true for you:</p>")
    body.append('<ul class="tk-check" id="tk-check">%s</ul>' % signs)
    body.append('<div class="tk-tally"><output id="tk-count" aria-live="polite">0 of %d true</output></div>' % len(SIGNS))
    body.append('<p class="tk-close">When three of these are true, that\'s what <a href="%s" data-cta="tracker_demo">'
                'Stingray</a> was built for.</p>' % esc(link(STINGRAY_URL, s, "close", "embed10")))

    body.append("""<div class="cta">
  <div><strong>still a spreadsheet team? good.</strong><p>Take the tracker and change whatever you like, just keep the Patterns tab, because that's where a closed case stops getting forgotten.</p></div>
  <div class="btns"><a class="btn primary" href="%s" data-cta="tracker_get_bottom">get the template</a><a class="btn ghost" href="%s" data-cta="sop">steal our chargebacks SOP</a></div>
</div>""" % (get("bottom"), esc(link(SOP_URL, s, "bottom"))))

    body.append("<h2>related glossary terms</h2>")
    body.append(related_cards(g["related"], ctx["by_name"]))
    body.append(foot_meta(g["updated"]))
    body.append("</article></main></div>")

    canonical = GUIDES + s + "/"
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "@id": canonical + "#article", "headline": g["h1"], "description": g["desc"],
         "url": canonical, "dateModified": g["updated"], "inLanguage": "en",
         "author": {"@type": "Organization", "name": "Stingray Fraud Intelligence", "url": STINGRAY_URL},
         "publisher": {"@type": "Organization", "name": "Stingray Fraud Intelligence", "url": STINGRAY_URL}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "guides", "item": GUIDES},
            {"@type": "ListItem", "position": 2, "name": "fraud case tracker", "item": canonical}]}]}
    return page(g["title"], g["desc"], canonical, jsonld, "".join(body), s)


# ---------------------------------------------------------------- index

INDEX_TITLE = "Guides for fraud analysts | Stingray"
INDEX_DESC = ("Practical guides and free tools for fraud analysts, starting with a free fraud case tracker template "
              "with a patterns tab.")


def index_page(ctx, guides):
    body = ["""<section class="band tk-band"><div class="wrap">
  <h1 class="band-title">guides</h1>
  <p>practical guides and free tools for fraud analysts. read every one here before you download anything.</p>
</div></section>
<main class="wrap index">
<section><ul class="tk-list">"""]
    for g in guides:
        body.append('<li><a href="/guides/%s/"><b>%s</b><span>%s</span><span class="tk-meta">updated %s</span></a></li>' % (
            esc(g["slug"]), esc(g["h1"]), esc(g["desc"]), esc(g["updated"])))
    body.append('<li><a href="/glossary/"><b>fraud glossary</b><span>%d fraud and trust &amp; safety terms, written the '
                'way fraud analysts actually use them.</span></a></li>' % len(ctx["terms"]))
    body.append("</ul></section></main>")
    jsonld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Stingray guides", "url": GUIDES,
              "description": INDEX_DESC,
              "hasPart": [{"@type": "Article", "headline": g["h1"], "url": GUIDES + g["slug"] + "/"} for g in guides]}
    return page(INDEX_TITLE, INDEX_DESC, GUIDES, jsonld, "".join(body))


def build(out_dir, ctx):
    """Write the guides into out_dir and return [(url, lastmod)] for the sitemap."""
    repo = Path(__file__).resolve().parent.parent
    gdir = Path(out_dir) / "guides"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "guides.css").write_text((repo / "scripts" / "guides.css").read_text(encoding="utf-8"), encoding="utf-8")
    guides = [TRACKER]
    for name in TRACKER["related"]:  # fail the build, not the page, if a related term is renamed
        if name not in ctx["by_name"]:
            raise KeyError("guide related term not in glossary.json: %r" % name)
    d = gdir / TRACKER["slug"]
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text(tracker_page(ctx, repo), encoding="utf-8")
    (gdir / "index.html").write_text(index_page(ctx, guides), encoding="utf-8")
    print("guides: %d guide page%s + index" % (len(guides), "" if len(guides) == 1 else "s"))
    return [(GUIDES, max(g["updated"] for g in guides))] + [(GUIDES + g["slug"] + "/", g["updated"]) for g in guides]


if __name__ == "__main__":
    import sys
    from build_glossary import load_context
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "_site",
          load_context(Path(__file__).resolve().parent.parent))
