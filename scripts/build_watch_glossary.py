#!/usr/bin/env python3
"""Build the glossary overlay for Stingray Watch (Carrd embed 07) from glossary.json + archive.json.

  python3 scripts/build_watch_glossary.py [out_file]     (default: build/watch-embed07-glossary.html)

The output is one paste-ready embed: the overlay's full static markup (every term, definition
and "full page" link, plus the 12-vector board with Watch counts and sparklines), then the
inlined scripts/watch_glossary.css and scripts/watch_glossary.js.

- glossary.json is the only copy of the definitions. Watch no longer keeps its own.
- Static markup means crawlers, no-JS visitors and #glossary-<slug> deep links work before any
  fetch. Watch's deep-link code looks the row up on page load, so the ids must be in the embed.
- On first open, the script fetches archive.json and glossary.json from raw.githubusercontent
  (the host Watch already uses for feed.json) and refreshes counts, sparklines, order and
  definition wording in place. If a fetch fails, the static copy stays.
- A new term only reaches Watch after a regenerate + paste into embed 07.

Slug, icons, counting and the sparkline come from build_glossary.py, so Watch and
feed.stingrayfraud.com/glossary/ always agree. Not part of the Pages build: run it by hand
when embed 07 needs updating. Standard library only.
"""
import re
import sys
from pathlib import Path

from build_glossary import BASE, ICONS, MONTHS, esc, load_context, slug, sparkline, vector_board

RAW = "https://raw.githubusercontent.com/kgpy6kgdkk-ai/stingray-watch-data/main/"
LEAD_MIN = 55  # keep in step with split() in watch_glossary.js


def split_def(d):
    """Lead clause + tail. The lead is the text before the first em-dash when it can stand on
    its own; otherwise the whole definition is the lead. Nothing is reworded or hidden, and
    the em-dash stays (at the start of the tail)."""
    head, sep, rest = d.partition(" — ")
    if sep and len(head) >= LEAD_MIN:
        return head, sep + rest
    return d, ""


def icon(key, size):
    # One hidden sprite per embed; each use is ~90 bytes instead of the full path.
    return '<svg class="fs-g-ico" width="%d" height="%d" aria-hidden="true"><use href="#fs-g-i-%s"/></svg>' % (size, size, key)


def sprite():
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>%s</defs></svg>' % "".join(
        '<symbol id="fs-g-i-%s" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round">%s</symbol>' % (k, v) for k, v in ICONS.items()))


def def_html(t):
    lead, tail = split_def(t["definition"])
    s = slug(t["name"])
    # Copy buttons and aria-labels are added by the script, to keep the embed small.
    return ('<p class="fs-g-def"><span class="fs-g-lead">%s</span><span class="fs-g-tail">%s</span> '
            '<a class="fs-gloss-more" href="%s%s/" data-term="%s">full page &rarr;</a></p>' % (esc(lead), esc(tail), BASE, s, s))


def month_name(key):
    return MONTHS[int(key[5:]) - 1]


def build(ctx):
    terms = ctx["terms"]
    months = ctx["months"]
    board, peak, spark_peak = vector_board(ctx)
    others = sorted((t for t in terms if not t.get("vector")), key=lambda t: t["name"].lower())
    since = "%s %s" % (month_name(months[0]), months[0][:4])

    groups = {}
    for t in others:
        L = t["name"][0].upper()
        groups.setdefault(L if L.isalpha() else "#", []).append(t)
    alphabet = ["#"] + [chr(c) for c in range(65, 91)]
    gid = lambda L: "fs-g-l-num" if L == "#" else "fs-g-l-" + L.lower()

    o = ['<div id="glossary" class="fs-g" role="dialog" aria-modal="true" aria-label="fraud glossary" '
         'data-updated="%s" style="display:none;">' % esc(ctx["updated"]), sprite()]

    # Sticky top: header + search + letters in one block, so nothing depends on a magic offset.
    o.append('<div class="fs-g-top"><div class="fs-g-hdr">'
             '<span class="fs-g-title">%sfraud glossary</span><span class="fs-g-count">%d terms</span>'
             '<a class="fs-gloss-all" href="%s">full glossary &rarr;</a>'
             '<button type="button" class="fs-g-back" onclick="window.fsCloseGlossary();" aria-label="Back to feed">&larr; back</button></div>'
             % (icon("a-z", 15), len(terms), BASE))
    o.append('<div class="fs-g-find"><label class="fs-g-search"><svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">'
             '<circle cx="7" cy="7" r="5.2" stroke="currentColor" stroke-width="1.8"/><path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'
             '<input type="search" id="fs-glossary-search" placeholder="search %d terms, like chargeback or ATO" autocomplete="off" aria-label="Search glossary terms"></label>'
             % len(terms))
    # Letters are buttons that scroll inside the overlay. No href="#...": Carrd treats the hash as section navigation.
    letters = ['<button type="button" class="fs-g-jv" data-jump="fs-g-vectors">vectors</button>']
    letters += ['<button type="button" data-jump="%s">%s</button>' % (gid(L), L) if L in groups
                else '<span aria-hidden="true">%s</span>' % L for L in alphabet]
    o.append('<nav class="fs-g-letters" aria-label="Jump to letter">%s</nav></div></div>' % "".join(letters))

    o.append('<div class="fs-g-body">')
    o.append('<section class="fs-g-sec" id="fs-g-vectors"><h2 class="fs-g-h">%sfraud vectors <span class="fs-g-n">%d</span></h2>'
             '<p class="fs-g-sub">the patterns every Watch item gets tagged with, busiest first. '
             'the number is items tagged since %s; the line is month by month.</p>' % (icon("fraud-vectors", 18), len(board), since))
    o.append('<ul class="fs-g-board" id="fs-glossary-core">')
    for t, c, series in board:
        o.append('<li class="fs-g-vrow" id="glossary-%s" data-vector="%s" data-find><span class="fs-g-name">%s</span>%s'
                 '<div class="fs-g-vstat"><span class="fs-g-track"><span class="fs-g-fill" style="width:%.1f%%"></span></span>'
                 '<span class="fs-g-num">%d</span>%s</div></li>' % (
                     slug(t["name"]), esc(t["vector"]), esc(t["name"]), def_html(t),
                     100.0 * c / peak, c, sparkline(series, spark_peak, months, cls="fs-g-spark")))
    o.append('</ul><p class="fs-g-legend"><span><i></i>items tagged on Watch</span>'
             '<span>line: %s &rarr; %s, dot = this month so far</span></p></section>' % (month_name(months[0]), month_name(months[-1])))

    o.append('<section class="fs-g-sec" id="fs-g-az"><h2 class="fs-g-h">%sglossary a&ndash;z <span class="fs-g-n">%d</span></h2>'
             '<p class="fs-g-sub">the rest of the vocabulary: payments, disputes, identity, scams and detection.</p>'
             '<div id="fs-glossary-extended">' % (icon("a-z", 18), len(others)))
    for L in alphabet:
        if L not in groups:
            continue
        o.append('<div class="fs-g-letter" id="%s"><h3>%s</h3><div class="fs-g-entries">' % (gid(L), L))
        for t in groups[L]:
            c = ctx["cat_by_slug"][t["category"]]
            o.append('<div class="fs-g-entry" id="glossary-%s" data-cat="%s" data-find>'
                     '<div class="fs-g-term"><span class="fs-g-name">%s</span><span class="fs-g-chip">%s%s</span></div>%s</div>' % (
                         slug(t["name"]), c["slug"], esc(t["name"]), icon(c["slug"], 12), esc(c["name"]), def_html(t)))
        o.append("</div></div>")
    o.append('</div></section><p class="fs-g-empty" id="fs-glossary-noresults" hidden>no terms match that search. '
             '<a class="fs-gloss-all" href="%s">try the full glossary &rarr;</a></p>' % BASE)
    o.append('<p class="fs-g-foot">every term has its own page: how it plays out, what analysts look for, and what Watch has seen. '
             '<a class="fs-gloss-all" href="%s">open the full glossary &rarr;</a></p>' % BASE)
    o.append("</div></div>")
    return "".join(o)


def minify(src):
    # Comments and line breaks only. Neither file has "/*" inside a string.
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"\s*\n\s*", "", src)


def main():
    repo = Path(__file__).resolve().parent.parent
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else repo / "build" / "watch-embed07-glossary.html"
    ctx = load_context(repo)
    css = minify((repo / "scripts" / "watch_glossary.css").read_text(encoding="utf-8"))
    js = (repo / "scripts" / "watch_glossary.js").read_text(encoding="utf-8").replace("__RAW__", RAW)
    js = "\n".join(line.strip() for line in re.sub(r"/\*.*?\*/", "", js, flags=re.S).splitlines() if line.strip())
    embed = build(ctx) + "<style>" + css + "</style><script>" + js + "</script>"
    ids = re.findall(r'id="glossary-([^"]+)"', embed)
    if len(ids) != len(ctx["terms"]) or len(set(ids)) != len(ids):
        sys.exit("deep-link ids don't line up with glossary.json terms")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(embed, encoding="utf-8")
    print("watch glossary embed: %s, %d terms, %s bytes" % (out, len(ids), format(len(embed.encode("utf-8")), ",")))


if __name__ == "__main__":
    main()
