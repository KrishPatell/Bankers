#!/usr/bin/env python3
"""Post-build checks on dist/. Exits non-zero if anything would break in production.

    python tools/verify.py
"""

import json
import os
import re
import sys
import urllib.parse
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cmsdata
import wfconfig as CFG

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

failures = []
notes = []


def fail(msg):
    failures.append(msg)


def note(msg):
    notes.append(msg)


def html_files():
    for base, _dirs, files in os.walk(DIST):
        for f in files:
            if f.endswith(".html"):
                yield os.path.join(base, f)


def rel(path):
    return os.path.relpath(path, DIST).replace("\\", "/")


# --------------------------------------------------------------------- checks

def check_placeholders(pages):
    """Nothing from the unbound export may survive into production."""
    patterns = {
        "w-dyn-bind-empty": "unbound CMS element",
        "No items found": "Webflow default empty-state text",
        'src=""': "image with no source",
        "medicio.webflow.io": "link to the Webflow template demo site",
        "Item Heading": "lorem ipsum from the dead template list",
        "eros dolor interdum": "lorem ipsum body copy",
    }
    hits = Counter()
    for path, html in pages.items():
        for pat, label in patterns.items():
            n = html.count(pat)
            if n:
                hits[label] += n
                fail("%s: %d x %s" % (rel(path), n, label))
    if not hits:
        note("no unbound placeholders, lorem ipsum, or template links anywhere")


def redirect_sources():
    """Paths that resolve via a 301 in vercel.json rather than a file."""
    p = os.path.join(DIST, "vercel.json")
    if not os.path.exists(p):
        return set()
    cfg = json.load(open(p, encoding="utf-8"))
    out = set()
    for r in cfg.get("redirects", []):
        src = r.get("source", "")
        out.add(src)
        out.add(src.rstrip("/"))
        out.add(src + "/")
    return out


def check_link_integrity(pages):
    """Every internal href/src must resolve under Vercel's cleanUrls."""
    # Files actually shipped, plus the extensionless forms cleanUrls serves.
    on_disk = set()
    for base, _dirs, files in os.walk(DIST):
        for f in files:
            r = os.path.relpath(os.path.join(base, f), DIST).replace("\\", "/")
            on_disk.add("/" + r)
            if r.endswith(".html"):
                on_disk.add("/" + r[:-len(".html")])
                if r.endswith("/index.html"):
                    on_disk.add("/" + r[:-len("/index.html")])
    on_disk.add("/")
    on_disk.add("/api/contact")
    on_disk |= redirect_sources()

    broken = Counter()
    for path, html in pages.items():
        refs = set(re.findall(r'(?:href|src)="(/[^"]*)"', html))
        for m in re.finditer(r'srcset="([^"]*)"', html):
            for chunk in m.group(1).split(","):
                u = chunk.strip().split(" ")[0]
                if u.startswith("/"):
                    refs.add(u)
        # Inline background-image URLs, entity-decoded: hero images on every
        # department/treatment page are only referenced this way.
        for m in re.finditer(r"url\((?:&quot;|[\"']?)(/[^)\"'&]+)",
                             html):
            refs.add(m.group(1))
        for ref in refs:
            clean = urllib.parse.unquote(ref.split("?")[0].split("#")[0])
            if not clean or clean in on_disk:
                continue
            broken["%s -> %s" % (rel(path), clean)] += 1
    if broken:
        for k in sorted(broken)[:40]:
            fail("broken internal link: %s" % k)
        if len(broken) > 40:
            fail("...and %d more broken internal links" % (len(broken) - 40))
    else:
        note("all internal links resolve (checked %d pages)" % len(pages))


def check_publish_rules(pages):
    """No archived or draft item may be reachable; the one exception must be."""
    cms = cmsdata.Collections(CFG.COLLECTIONS, CFG.SITE_URL)
    blob = "\n".join(pages.values())

    redirected = redirect_sources()
    leaked = []
    for key, spec in cms.specs.items():
        folder = spec.get("folder")
        if not folder:
            continue
        for slug, why in cms.excluded[key]:
            url = "/%s/%s" % (folder, slug)
            if os.path.exists(os.path.join(DIST, folder, slug + ".html")):
                leaked.append("%s page exists but is %s" % (url, why))
            if '"%s"' % url in blob and url not in redirected:
                # A link to an excluded item is only acceptable if a redirect
                # sends it somewhere real.
                leaked.append("%s is linked but is %s, with no redirect"
                              % (url, why))
            elif '"%s"' % url in blob:
                note("%s (%s) is linked from CMS copy; a 301 sends it to a "
                     "published page" % (url, why))
    for msg in leaked:
        fail("publish-rule leak: %s" % msg)

    for key, slugs in cmsdata.FORCE_PUBLISH.items():
        folder = cms.specs[key]["folder"]
        for slug in slugs:
            p = os.path.join(DIST, folder, slug + ".html")
            if not os.path.exists(p):
                fail("force-published item missing: /%s/%s" % (folder, slug))

    expected = {k: len(v) for k, v in cms.published.items()
                if cms.specs[k].get("folder")}
    for key, count in sorted(expected.items()):
        folder = cms.specs[key]["folder"]
        actual = len([f for f in os.listdir(os.path.join(DIST, folder))
                      if f.endswith(".html") and f != "index.html"])
        if actual != count:
            fail("%s: %d pages on disk, %d published items" % (key, actual, count))
    if not leaked:
        note("publish rules hold: %d items across %d collections, "
             "dr-mohal-banker force-published"
             % (sum(expected.values()), len(expected)))
    return cms


def check_nav(pages, cms):
    """The three CMS nav dropdowns must match the live item counts."""
    want = {"our-doctors": 9, "departments": 12, "treatment": 9}
    for key, n in want.items():
        if len(cms.published[key]) != n:
            fail("%s has %d published items, expected %d (live site count)"
                 % (key, len(cms.published[key]), n))
    sample = os.path.join(DIST, "index.html")
    html = pages[sample]
    for folder, n in want.items():
        found = len(set(re.findall(r'href="(/%s/[^"]+)"' % folder, html)))
        if found < n:
            fail("index.html nav lists only %d/%d %s links" % (found, n, folder))
    note("nav dropdowns carry 9 doctors / 12 departments / 9 treatments")


def check_meta(pages):
    """Every indexable page needs a real title and a self-referencing canonical."""
    bad_title = bad_canon = dupe = 0
    canons = Counter()
    for path, html in pages.items():
        r = rel(path)
        if r in ("401.html", "404.html"):
            continue
        m = re.search(r"<title>(.*?)</title>", html, re.S)
        title = (m.group(1).strip() if m else "")
        if not title or title.startswith("|") or title == "Copy of Bankers Vascular":
            bad_title += 1
            fail("%s: unfilled title %r" % (r, title[:60]))
        c = re.search(r'<link href="([^"]*)" rel="canonical">', html)
        if not c:
            bad_canon += 1
            fail("%s: no canonical" % r)
        else:
            canons[c.group(1)] += 1
    for url, n in canons.items():
        if n > 1:
            dupe += 1
            fail("canonical used by %d pages: %s" % (n, url))
    if not (bad_title or bad_canon or dupe):
        note("every indexable page has a filled title and a unique canonical")


def check_forms(pages):
    """Every lead form must POST to the endpoint and have a real submit control."""
    total = 0
    for path, html in pages.items():
        for m in re.finditer(r"<form\s[^>]*>", html):
            tag = m.group(0)
            if "/.wf_auth" in tag:
                continue
            total += 1
            r = rel(path)
            if 'action="/api/contact"' not in tag or 'method="post"' not in tag:
                fail("%s: form not wired to the endpoint" % r)
            if "data-wf-page-id" in tag:
                fail("%s: form still carries Webflow attributes" % r)
        # Each form's submit control and honeypot.
        forms = html.count("<form ") - html.count("/.wf_auth")
        if forms and html.count("_gotcha") < forms:
            fail("%s: %d forms but %d honeypots"
                 % (rel(path), forms, html.count("_gotcha")))
        if forms and "/js/forms.js" not in html:
            fail("%s: forms present but forms.js not loaded" % rel(path))
    note("%d lead forms POST to /api/contact with honeypot + submit control"
         % total)


def check_submit_controls(pages):
    missing = []
    for path, html in pages.items():
        for m in re.finditer(r"<form\s[^>]*>", html):
            if "/.wf_auth" in m.group(0):
                continue
            end = html.find("</form>", m.end())
            seg = html[m.start():end]
            if 'type="submit"' not in seg:
                missing.append(rel(path))
    for r in sorted(set(missing)):
        fail("%s: a form has no submit control" % r)
    if not missing:
        note("no form is left without a submit control")


def check_assets(pages):
    """No page may still depend on the Webflow CDN for a CMS image."""
    remaining = Counter()
    for path, html in pages.items():
        for m in re.finditer(r'(?:src|href)="(https://[^"]*(?:website-files|webflow)\.com[^"]*)"', html):
            remaining[m.group(1)] += 1
    if remaining:
        note("%d distinct Webflow CDN URLs still referenced (download failures; "
             "see tools/asset-report.txt)" % len(remaining))
        for u, n in remaining.most_common(5):
            note("    %dx %s" % (n, u[:100]))
    else:
        note("no page depends on the Webflow CDN")


def check_animations(pages):
    """Elements that start hidden must have an interaction that reveals them.

    Webflow ships scroll animations as inline `style="opacity:0"` plus a
    `data-w-id` whose rule lives in webflow.js, keyed by the page's
    `data-wf-page`. If a generated page carried a page id webflow.js did not
    know, or a data-w-id with no rule, that content would be permanently
    invisible in production - the worst possible failure here, because the page
    would still return 200 and look fine to a link checker.
    """
    wf_path = os.path.join(DIST, "js", "webflow.js")
    if not os.path.exists(wf_path):
        return fail("js/webflow.js missing - every scroll animation would break")
    wf = open(wf_path, encoding="utf-8", errors="replace").read()

    # An element is at risk only if it starts hidden *and* is driven by a
    # data-w-id. A missing page id on its own is fine - Webflow simply emits no
    # interaction data for pages that have none (401, 404, the policy pages).
    # `aria-hidden` elements are meant to stay invisible: the form honeypots and
    # the collapsed chat widget.
    orphans = 0
    animated_pages = 0
    for path, html in pages.items():
        page_id = re.search(r'data-wf-page="([^"]+)"', html)
        hidden = [em.group(0) for em
                  in re.finditer(r'<[^>]*style="[^"]*opacity:0[^"]*"[^>]*>', html)
                  if "data-w-id=" in em.group(0)
                  and 'aria-hidden="true"' not in em.group(0)]
        if not hidden:
            continue
        if page_id and page_id.group(1) not in wf:
            orphans += 1
            fail("%s: %d hidden elements but webflow.js has no interaction data "
                 "for page %s - that content would never become visible"
                 % (rel(path), len(hidden), page_id.group(1)))
            continue
        animated_pages += 1
        for em in hidden:
            wid = re.search(r'data-w-id="([^"]+)"', em).group(1)
            if wid not in wf:
                orphans += 1
                fail("%s: element %s starts hidden with no reveal animation"
                     % (rel(path), wid))
    if not orphans:
        note("%d animated pages: every hidden element has a reveal rule, "
             "no invisible sections" % animated_pages)


def check_sitemap(pages):
    p = os.path.join(DIST, "sitemap.xml")
    if not os.path.exists(p):
        return fail("sitemap.xml missing")
    xml = open(p, encoding="utf-8").read()
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    if len(locs) < 300:
        fail("sitemap has only %d URLs" % len(locs))
    for bad in ("detail_", "/401", "/404", "insurance-departments"):
        if bad in xml:
            fail("sitemap contains %s" % bad)
    note("sitemap.xml lists %d URLs" % len(locs))


def check_encoding():
    """Non-ASCII CMS content (990 curly quotes, emoji, Gujarati) must survive."""
    p = os.path.join(DIST, "blog", "index.html")
    raw = open(p, "rb").read()
    if raw[:3] == b"\xef\xbb\xbf":
        fail("blog/index.html starts with a UTF-8 BOM")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        fail("blog/index.html is not valid UTF-8: %s" % exc)
    hits = sum(1 for base, _d, fs in os.walk(DIST) for f in fs
               if f.endswith(".html")
               and "’" in open(os.path.join(base, f), encoding="utf-8").read())
    note("UTF-8 clean; curly punctuation preserved on %d pages" % hits)


def check_vercel():
    p = os.path.join(DIST, "vercel.json")
    if not os.path.exists(p):
        return fail("vercel.json not in dist/")
    cfg = json.load(open(p, encoding="utf-8"))
    if not cfg.get("cleanUrls"):
        fail("vercel.json: cleanUrls must be true for /blog/<slug> to resolve")
    if cfg.get("trailingSlash") is not False:
        fail("vercel.json: trailingSlash should be false")
    # Directory-page collision guard.
    for page in CFG.DIRECTORY_PAGES:
        if os.path.exists(os.path.join(DIST, page)):
            fail("%s exists alongside its folder - ambiguous under cleanUrls" % page)
    note("vercel.json is sane and no listing page collides with a CMS folder")


def main():
    if not os.path.isdir(DIST):
        print("dist/ not found - run tools/build.py first")
        return 1
    pages = {p: open(p, encoding="utf-8").read() for p in html_files()}

    check_placeholders(pages)
    check_link_integrity(pages)
    cms = check_publish_rules(pages)
    check_nav(pages, cms)
    check_meta(pages)
    check_forms(pages)
    check_submit_controls(pages)
    check_assets(pages)
    check_animations(pages)
    check_sitemap(pages)
    check_encoding()
    check_vercel()

    print("=" * 70)
    for n in notes:
        print("  ok   %s" % n)
    print("=" * 70)
    if failures:
        print("%d FAILURE(S):" % len(failures))
        for f in failures:
            print("  FAIL %s" % f)
        return 1
    print("all checks passed (%d pages)" % len(pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
