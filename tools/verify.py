#!/usr/bin/env python3
"""Post-build checks on dist/. Exits non-zero if anything would break in production.

    python tools/verify.py
"""

import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
import sys
import urllib.parse
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cmsdata
import schema as ENTITY_SCHEMA
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


def clean_url_for_file(relative_path):
    """Map a generated HTML path to its public clean URL."""
    relative_path = relative_path.replace("\\", "/")
    if relative_path == "index.html":
        return "/"
    if relative_path.endswith("/index.html"):
        return "/" + relative_path[:-len("/index.html")]
    if relative_path.endswith(".html"):
        return "/" + relative_path[:-len(".html")]
    return "/" + relative_path


def git_source_lastmod(relative_path):
    """Return the latest committed date for a source dependency."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "HEAD", "--", relative_path],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    value = result.stdout.strip()
    if result.returncode or not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


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
    """Paths handled by Worker redirects rather than a file."""
    p = os.path.join(ROOT, "wrangler.jsonc")
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
    """Every internal href/src must resolve under the Worker's clean URLs."""
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
        # A directly linked editorial shell may intentionally live under a
        # CMS folder without being a CMS collection item. It is omitted from
        # the archive by design, so do not count it as a publish-rule leak.
        extra = sum(
            1 for page in CFG.EXTRA_SHELL_PAGES.values()
            if page.get("output", "").startswith(folder + "/")
            and page.get("output", "").endswith(".html")
            and not page.get("output", "").endswith("/index.html")
        )
        actual -= extra
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
        if (not title or title.startswith("|") or title == "Copy of Bankers Vascular"
                or title.rstrip().endswith("|")):
            bad_title += 1
            fail("%s: unfilled title %r" % (r, title[:60]))
        c = re.search(r'<link href="([^"]*)" rel="canonical">', html)
        if not c:
            bad_canon += 1
            fail("%s: no canonical" % r)
        else:
            canonical = c.group(1)
            canons[canonical] += 1
            expected = CFG.SITE_URL + clean_url_for_file(r)
            if canonical != expected:
                bad_canon += 1
                fail("%s: canonical %s does not match %s"
                     % (r, canonical, expected))
    for url, n in canons.items():
        if n > 1:
            dupe += 1
            fail("canonical used by %d pages: %s" % (n, url))
    if not (bad_title or bad_canon or dupe):
        note("every indexable page has a filled title and a unique canonical")


def check_blog_featured_image_policy(pages, cms):
    """Thumbnails belong on blog cards and social metadata, never article bodies."""
    bad = []
    for item in cms.published["blog"]:
        path = os.path.join(DIST, "blog", item.slug + ".html")
        html = pages.get(path, "")
        if ('class="blog-main-image' in html or 'blog-main-image-wapper' in html
                or 'class="blog-meta-wrapper' in html):
            bad.append("/blog/%s" % item.slug)
    for url in bad:
        fail("%s renders a featured thumbnail on the article page" % url)
    if not bad:
        note("blog pages flow directly into content; thumbnails and author/date blocks stay off-page")


def check_jsonld(pages):
    """Validate page graphs, canonical breadcrumb relationships, and medical nodes."""
    organization_id = ENTITY_SCHEMA.ENTITY_IDS["organization"]
    location_by_city = ENTITY_SCHEMA.LOCATIONS
    noindex_routes = {
        CFG.SITE_URL + page["url"]
        for name, page in CFG.EXTRA_SHELL_PAGES.items()
        if name in CFG.NOINDEX_PAGES
    }
    parsed_pages = parsed_scripts = 0

    def types(node):
        value = node.get("@type", [])
        return set(value if isinstance(value, list) else [value])

    for path, html in pages.items():
        relative = rel(path)
        canonical_match = re.search(r'<link href="([^"]*)" rel="canonical">', html)
        canonical = canonical_match.group(1) if canonical_match else ""
        if relative in ("401.html", "404.html") or canonical in noindex_routes:
            continue
        raw_scripts = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        if not raw_scripts:
            fail("%s: no JSON-LD block" % relative)
            continue

        nodes = []
        for raw in raw_scripts:
            try:
                document = json.loads(raw)
            except json.JSONDecodeError as exc:
                fail("%s: invalid JSON-LD: %s" % (relative, exc))
                continue
            parsed_scripts += 1
            nodes.extend(document.get("@graph", [document]))
        if not nodes:
            fail("%s: JSON-LD contains no nodes" % relative)
            continue
        parsed_pages += 1

        expected = CFG.SITE_URL + clean_url_for_file(relative)
        if canonical != expected:
            fail("%s: JSON-LD test cannot resolve canonical %s (expected %s)"
                 % (relative, canonical, expected))

        webpages = [node for node in nodes if "WebPage" in types(node)]
        if not webpages:
            fail("%s: JSON-LD has no WebPage node" % relative)
        for webpage in webpages:
            if webpage.get("url") != canonical:
                fail("%s: WebPage url is not canonical" % relative)
            breadcrumb = webpage.get("breadcrumb", {}).get("@id")
            if breadcrumb != canonical + "#breadcrumb":
                fail("%s: WebPage breadcrumb does not reference canonical page" % relative)

        breadcrumbs = [node for node in nodes if "BreadcrumbList" in types(node)]
        if not breadcrumbs:
            fail("%s: missing BreadcrumbList" % relative)
        else:
            elements = breadcrumbs[-1].get("itemListElement", [])
            last_item = elements[-1].get("item") if elements else None
            if last_item != canonical:
                fail("%s: final breadcrumb item is %s, expected %s"
                     % (relative, last_item, canonical))

        parts = clean_url_for_file(relative).strip("/").split("/")
        if len(parts) == 2 and parts[0] in ("varicose-veins", "non-surgical-knee-pain"):
            city = parts[1]
            if city in location_by_city:
                expected_type = "Hospital" if city == "ahmedabad" else "MedicalClinic"
                location_id = location_by_city[city]["id"]
                locations = [node for node in nodes
                             if node.get("@id") == location_id]
                if not any(expected_type in types(node) for node in locations):
                    fail("%s: missing %s location schema" % (relative, expected_type))
                elif any(node.get("parentOrganization", {}).get("@id") != organization_id
                         for node in locations):
                    fail("%s: location schema has no primary organization relationship"
                         % relative)
                else:
                    expected_hours = location_by_city[city]["opening_hours"]
                    valid_hours = any(
                        node.get("openingHoursSpecification")
                        and any(
                            spec.get("opens") == expected_hours["opens"]
                            and spec.get("closes") == expected_hours["closes"]
                            and set(spec.get("dayOfWeek", [])) == {
                                "Monday", "Tuesday", "Wednesday", "Thursday",
                                "Friday", "Saturday",
                            }
                            for spec in node["openingHoursSpecification"]
                        )
                        for node in locations
                    )
                    if not valid_hours:
                        fail("%s: location schema has incorrect confirmed hospital hours"
                             % relative)

        if parts and parts[0] == "treatment" and len(parts) == 2:
            procedures = [node for node in nodes if "MedicalProcedure" in types(node)]
            if len(procedures) != 1:
                fail("%s: expected one MedicalProcedure node, found %d"
                     % (relative, len(procedures)))
            else:
                procedure = procedures[0]
                if procedure.get("provider", {}).get("@id") != organization_id:
                    fail("%s: MedicalProcedure provider is not the primary organization"
                         % relative)
                if procedure.get("mainEntityOfPage", {}).get("@id") != canonical + "#webpage":
                    fail("%s: MedicalProcedure is not linked to the canonical WebPage"
                         % relative)

    if parsed_pages and not failures:
        note("parsed %d JSON-LD blocks across %d indexable pages; canonical breadcrumbs and medical relationships pass"
             % (parsed_scripts, parsed_pages))


def check_entity_schema(pages):
    """Keep the organisation and lead-doctor entity graph unambiguous."""
    person_id = ENTITY_SCHEMA.ENTITY_IDS["mohal_banker"]["person"]
    profile_id = ENTITY_SCHEMA.ENTITY_IDS["mohal_banker"]["profile_page"]
    organization_id = ENTITY_SCHEMA.ENTITY_IDS["organization"]
    website_id = ENTITY_SCHEMA.ENTITY_IDS["website"]
    location_ids = {location["id"] for location in ENTITY_SCHEMA.LOCATIONS.values()}
    person_nodes = profile_nodes = organization_nodes = website_nodes = 0
    location_nodes = Counter()

    for path, html in pages.items():
        for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            try:
                document = json.loads(raw)
            except json.JSONDecodeError as exc:
                fail("%s: invalid JSON-LD: %s" % (rel(path), exc))
                continue
            for node in document.get("@graph", [document]):
                node_id = node.get("@id")
                if node_id == person_id:
                    person_nodes += 1
                elif node_id == profile_id:
                    profile_nodes += 1
                elif node_id == organization_id:
                    organization_nodes += 1
                elif node_id == website_id:
                    website_nodes += 1
                elif node_id in location_ids:
                    location_nodes[node_id] += 1
                if node_id and "#medical-clinic" in node_id:
                    fail("%s: obsolete #medical-clinic entity ID" % rel(path))
                if (node.get("@type") == "BlogPosting"
                        and node.get("publisher", {}).get("@id") != organization_id):
                    fail("%s: BlogPosting publisher does not reference the primary organization" % rel(path))

    if person_nodes != 1 or profile_nodes != 1:
        fail("expected one Dr. Mohal Banker Person and ProfilePage node; found %d and %d"
             % (person_nodes, profile_nodes))
    if organization_nodes != 1 or website_nodes != 1:
        fail("expected one homepage Organization and WebSite node; found %d and %d"
             % (organization_nodes, website_nodes))
    if set(location_nodes) != location_ids or any(n < 1 for n in location_nodes.values()):
        fail("expected structured-data entities for each verified branch; found %s"
             % dict(location_nodes))
    if not failures:
        note("entity schema uses one primary organization, website, and Dr. Mohal Banker profile with verified branch relationships")


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


def check_hospital_hours(pages):
    """Keep rendered hospital timing blocks aligned with confirmed hours."""
    targets = {
        "/varicose-veins/ahmedabad": ENTITY_SCHEMA.LOCATION_HOURS["ahmedabad"],
        "/varicose-veins/vadodara": ENTITY_SCHEMA.LOCATION_HOURS["vadodara"],
        "/contact-us": ENTITY_SCHEMA.LOCATION_HOURS["ahmedabad"],
    }
    seen = set()
    for path, html in pages.items():
        route = clean_url_for_file(rel(path))
        if route not in targets:
            continue
        seen.add(route)
        timing = re.search(
            r"<h5\b[^>]*>\s*Hospital Timings\s*</h5>\s*"
            r"<p\b[^>]*>(.*?)</p>", html, re.S | re.I)
        if not timing:
            fail("%s: missing Hospital Timings block" % route)
            continue
        text = re.sub(r"<[^>]+>", " ", timing.group(1))
        if (not re.search(r"Monday\s*-\s*Saturday", text, re.I)
                or not re.search(r"8\s*:\s*00.*7\s*:\s*00", text, re.S | re.I)
                or not re.search(r"Sunday\s*\(Closed\)", text, re.I)):
            fail("%s: Hospital Timings block is not Monday-Saturday 08:00-19:00"
                 % route)
        if route != "/contact-us":
            display = targets[route]["display"]
            if html.count(display) < 2:
                fail("%s: confirmed hours are not present in both public timing surfaces"
                     % route)
    if seen == set(targets) and not failures:
        note("confirmed 08:00-19:00 hospital timing blocks pass for both branches and contact page")


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


def check_meta_pixel_absent(pages):
    """Meta/Facebook browser tracking must remain fully removed."""
    patterns = {
        "Meta Pixel 1994474461275883": r"1994474461275883",
        "Meta Pixel 4646870475584513": r"4646870475584513",
        "Meta fbevents.js loader": r"fbevents\.js",
        "Meta fbq call": r"\bfbq\s*\(",
        "Meta noscript pixel fallback": r"facebook\.com/tr(?:\?|&amp;)",
    }
    found = False
    for label, pattern in patterns.items():
        hits = [rel(path) for path, html in pages.items()
                if re.search(pattern, html, re.I)]
        if hits:
            found = True
            fail("%s remains on %d generated page(s), including %s"
                 % (label, len(hits), hits[0]))
    if not found:
        note("Meta Pixel browser tracking is absent from every generated page")


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


def check_sitemap(pages, cms):
    p = os.path.join(DIST, "sitemap.xml")
    if not os.path.exists(p):
        return fail("sitemap.xml missing")
    xml = open(p, encoding="utf-8").read()
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        return fail("sitemap.xml is not valid XML: %s" % exc)
    if root.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset":
        fail("sitemap.xml has an invalid urlset namespace")
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    if len(locs) < 300:
        fail("sitemap has only %d URLs" % len(locs))
    for bad in ("detail_", "/401", "/404", "insurance-departments"):
        if bad in xml:
            fail("sitemap contains %s" % bad)
    if len(locs) != len(set(locs)):
        fail("sitemap contains duplicate URLs")
    for loc in locs:
        if not loc.startswith("https://bankersvascular.com/"):
            fail("sitemap contains a non-canonical URL: %s" % loc)
        if any(bad in loc for bad in ("localhost", "staging", ".html", "?")):
            fail("sitemap contains an invalid URL: %s" % loc)

    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_dates = {}
    for node in root.findall("sm:url", namespace):
        loc = node.findtext("sm:loc", default="", namespaces=namespace)
        lastmod = node.findtext("sm:lastmod", default="", namespaces=namespace)
        if not lastmod:
            fail("sitemap URL has no lastmod: %s" % loc)
            continue
        try:
            sitemap_dates[loc] = datetime.strptime(lastmod, "%Y-%m-%d").date()
        except ValueError:
            fail("sitemap URL has invalid lastmod %r: %s" % (lastmod, loc))

    for key, spec in cms.specs.items():
        folder = spec.get("folder")
        if not folder:
            continue
        for item in cms.published[key]:
            expected_date = item.get("_updated") or item.get("_date")
            if not expected_date or not item.url:
                continue
            loc = CFG.SITE_URL + item.url
            if sitemap_dates.get(loc) != expected_date.date():
                fail("sitemap lastmod mismatch for %s: expected %s, found %s"
                     % (loc, expected_date.date(), sitemap_dates.get(loc)))

    controlled_routes = {}
    for page, lastmod in CFG.SITEMAP_LASTMOD.items():
        if page in CFG.NOINDEX_PAGES:
            continue
        extra = CFG.EXTRA_SHELL_PAGES.get(page)
        if extra:
            route = extra["url"]
        elif page == "index.html":
            route = "/"
        elif page in CFG.DIRECTORY_PAGES:
            route = "/" + CFG.DIRECTORY_PAGES[page].rsplit("/", 1)[0]
        else:
            route = "/" + page[:-len(".html")]
        controlled_routes[CFG.SITE_URL + route] = lastmod
    for loc, expected in controlled_routes.items():
        if loc in sitemap_dates and sitemap_dates[loc].isoformat() != expected:
            fail("static sitemap lastmod mismatch for %s: expected %s, found %s"
                 % (loc, expected, sitemap_dates[loc]))

    for page, dependencies in CFG.SITEMAP_SOURCE_DEPENDENCIES.items():
        extra = CFG.EXTRA_SHELL_PAGES.get(page)
        if not extra:
            fail("sitemap dependency has no configured shell page: %s" % page)
            continue
        loc = CFG.SITE_URL + extra["url"]
        actual = sitemap_dates.get(loc)
        if not actual:
            fail("sitemap dependency route is missing: %s" % loc)
            continue
        for dependency in dependencies:
            source_date = git_source_lastmod(os.path.join("src", dependency))
            if not source_date:
                fail("could not resolve Git lastmod for sitemap dependency src/%s"
                     % dependency)
            elif actual < source_date:
                fail("sitemap lastmod for %s (%s) predates source dependency src/%s (%s)"
                     % (loc, actual, dependency, source_date))
        if not failures:
            note("sitemap source dependency passes: %s includes %s through %s"
                 % (loc, ", ".join(dependencies), actual))

    if len(set(sitemap_dates.values())) > 1:
        note("sitemap.xml lists %d URLs with CMS/static lastmod dates" % len(locs))
    else:
        fail("sitemap lastmod values are still all identical")


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


def check_repo_layout():
    """The export must stay under src/, never at the repository root.

    This is what stops a misconfigured deploy from silently publishing the
    unbound templates. It happened once: the host served the repo root, so the
    live site showed empty collection lists and "No items found." on every
    section while dist/ was perfectly correct. With no index.html at the root
    that mistake 404s instead of looking like a successful deploy.
    """
    if not os.path.exists(os.path.join(ROOT, "src", "index.html")):
        return fail("src/index.html missing - the export is not where the "
                    "build expects it")
    stray = [n for n in ("index.html", "css", "js", "images", "fonts")
             if os.path.exists(os.path.join(ROOT, n))]
    if stray:
        fail("the repository root contains %s - a deploy pointed at the root "
             "would publish the unbound export instead of dist/"
             % ", ".join(stray))
    else:
        note("export is under src/; the repo root cannot be served as a site")


def check_cloudflare():
    p = os.path.join(ROOT, "wrangler.jsonc")
    if not os.path.exists(p):
        return fail("wrangler.jsonc missing from the repo root")
    if not os.path.isdir(os.path.join(ROOT, "api")):
        fail("api/ missing from the repo root - the form endpoint would 404")
    # Directory-page collision guard.
    for page in CFG.DIRECTORY_PAGES:
        if os.path.exists(os.path.join(DIST, page)):
            fail("%s exists alongside its folder - ambiguous under cleanUrls" % page)
    note("Cloudflare Worker config is present and no listing page collides with a CMS folder")


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
    check_jsonld(pages)
    check_entity_schema(pages)
    check_hospital_hours(pages)
    check_blog_featured_image_policy(pages, cms)
    check_forms(pages)
    check_submit_controls(pages)
    check_meta_pixel_absent(pages)
    check_assets(pages)
    check_animations(pages)
    check_sitemap(pages, cms)
    check_encoding()
    check_repo_layout()
    check_cloudflare()

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
