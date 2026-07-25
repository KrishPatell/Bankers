#!/usr/bin/env python3
"""Check a *deployed* URL is serving the built site, not the raw export.

    python tools/smoke.py https://your-deployment.vercel.app

tools/verify.py checks dist/ on disk and cannot catch a deployment that
publishes the wrong directory. That happened: Vercel served the repository root,
so production showed empty doctor/blog sections and "No items found." on every
page while dist/ was flawless and every local check passed.

The decisive signals are the ones that differ between the two:

    raw export index.html   9x "No items found",  1 doctor card, 2 author cards
    built  index.html       0x "No items found",  9 doctor cards, 4 author cards

and the ~334 CMS item pages, which do not exist in the export at all - so a
single 200 from /departments/piles proves the built site is live.
"""

import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; bankersvascular-smoke)"}

failures = []
notes = []


def fail(msg):
    failures.append(msg)


def note(msg):
    notes.append(msg)


def get(base, path, timeout=30):
    """Return (status, body, location). Redirects are reported, not followed."""
    url = base.rstrip("/") + urllib.parse.quote(path, safe="/%?=&#")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise urllib.error.HTTPError(
                req.full_url, code, msg, headers, None)

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(urllib.request.Request(url, headers=UA),
                         timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), None
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") if e.headers else None
        body = ""
        if e.code < 400:
            return e.code, "", loc
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        return e.code, body, loc
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, e), None


# ------------------------------------------------------------------ the checks

def check_home_is_built(base):
    status, html, _ = get(base, "/")
    if status != 200:
        return fail("/ returned %s - nothing else can be trusted" % status)

    for marker, label in (("No items found", "Webflow's empty-state text"),
                          ("w-dyn-bind-empty", "unbound CMS elements"),
                          ('src=""', "images with no source")):
        n = html.count(marker)
        if n:
            fail("/ contains %d x %r (%s) - the RAW EXPORT is being served, "
                 "not dist/. Check Vercel's Root Directory (must be empty) and "
                 "Output Directory (must be dist)." % (n, marker, label))

    doctors = set(re.findall(r'href="(/our-doctors/[^"]+)"', html))
    departments = set(re.findall(r'href="(/departments/[^"]+)"', html))
    if len(doctors) < 9:
        fail("/ links only %d of 9 doctors" % len(doctors))
    if len(departments) < 12:
        fail("/ links only %d of 12 departments" % len(departments))

    cards = html.count("doctor-archive-item")
    if cards < 9:
        fail("/ renders %d of 9 doctor cards - the 9-column gallery will look "
             "broken and scroll sideways" % cards)

    if not failures:
        note("/ is the built site: %d doctors, %d departments, %d doctor cards, "
             "no empty states" % (len(doctors), len(departments), cards))
    return html


def check_cms_pages(base):
    """These paths exist only in the built site."""
    sample = [
        "/departments/piles",
        "/treatment/hemorrhoids",
        "/our-doctors/dr-mohal-banker",
        "/varicose-veins/ahmedabad",
        "/non-surgical-knee-pain/ahmedabad",
        "/blog/how-fibroids-impact-daily-quality-of-life",
        "/blog-author/dr-tensi-trivedi",
        "/blog-category/health-care",
        "/products",
        "/contact-us",
        "/sitemap.xml",
        "/robots.txt",
    ]
    bad = []
    for path in sample:
        status, _body, _loc = get(base, path)
        if status != 200:
            bad.append("%s -> %s" % (path, status))
    if bad:
        for b in bad:
            fail("CMS page not served: %s" % b)
    else:
        note("all %d sampled CMS pages return 200" % len(sample))


def check_blog_pagination(base):
    status, html, _ = get(base, "/blog")
    if status != 200:
        return fail("/blog returned %s" % status)
    cards = html.count("blog-archive-item")
    if cards != 100:
        fail("/blog shows %d post cards, expected 100" % cards)
    if "/blog/page/2" not in html:
        fail("/blog has no link to page 2")
    for path, want in (("/blog/page/2", 100), ("/blog/page/3", 82)):
        st, body, _ = get(base, path)
        if st != 200:
            fail("%s returned %s" % (path, st))
        elif body.count("blog-archive-item") != want:
            fail("%s shows %d cards, expected %d"
                 % (path, body.count("blog-archive-item"), want))
    if not any("blog" in f for f in failures):
        note("/blog paginates correctly: 100 + 100 + 82 = 282 posts")


def check_redirects(base):
    expect = {
        "/blog.html": "/blog",
        "/index.html": "/",
        "/detail_blog": "/blog",
        # A draft item linked from 11 blog posts; must land on the published one.
        "/departments/platelet-rich-plasma": "/treatment/platelet-rich-plasma",
        "/departments/varicose-vein": "/departments/varicose-veins",
    }
    ok = 0
    for path, dest in expect.items():
        status, _body, loc = get(base, path)
        if status not in (301, 302, 307, 308):
            fail("%s returned %s, expected a redirect to %s"
                 % (path, status, dest))
        elif loc and not loc.rstrip("/").endswith(dest.rstrip("/")):
            fail("%s redirects to %s, expected %s" % (path, loc, dest))
        else:
            ok += 1
    if ok == len(expect):
        note("all %d checked redirects resolve correctly" % ok)


def check_home_assets(base, html):
    if not html:
        return
    refs = set(re.findall(r'(?:href|src)="(/[^"]*)"', html))
    for m in re.finditer(r'srcset="([^"]*)"', html):
        for chunk in m.group(1).split(","):
            u = chunk.strip().split(" ")[0]
            if u.startswith("/"):
                refs.add(u)
    for m in re.finditer(r"url\((?:&quot;|[\"']?)(/[^)\"'&]+)", html):
        refs.add(m.group(1))

    assets = sorted(r for r in refs if re.search(
        r"\.(css|js|png|jpe?g|svg|webp|avif|otf|ttf|woff2?)$", r, re.I))
    bad = []
    for a in assets:
        status, _b, _l = get(base, a, timeout=20)
        if status not in (200, 301, 302, 307, 308):
            bad.append("%s -> %s" % (a, status))
    if bad:
        for b in bad[:15]:
            fail("asset not served: %s" % b)
        if len(bad) > 15:
            fail("...and %d more broken assets" % (len(bad) - 15))
    else:
        note("all %d assets referenced by / return 200" % len(assets))


def check_form_endpoint(base):
    """A GET must be rejected; that proves the function is deployed at all."""
    status, _body, _loc = get(base, "/api/contact")
    if status == 405:
        note("/api/contact is deployed (rejects GET with 405)")
    elif status == 404:
        fail("/api/contact returns 404 - the serverless function is not "
             "deployed. Vercel reads api/ from the repository root, so Root "
             "Directory must be empty, not 'dist'.")
    else:
        note("/api/contact responded %s (expected 405 for GET)" % status)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    base = sys.argv[1].rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base
    print("smoke-testing %s\n" % base)

    html = check_home_is_built(base)
    check_cms_pages(base)
    check_blog_pagination(base)
    check_redirects(base)
    check_form_endpoint(base)
    check_home_assets(base, html)

    print("=" * 70)
    for n in notes:
        print("  ok   %s" % n)
    print("=" * 70)
    if failures:
        print("%d FAILURE(S):" % len(failures))
        for f in failures:
            print("  FAIL %s" % f)
        return 1
    print("deployment is serving the built site correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
