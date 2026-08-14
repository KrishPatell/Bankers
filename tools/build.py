#!/usr/bin/env python3
"""Build the deployable site from the Webflow export + the CMS CSVs.

    python tools/build.py [--skip-assets]

Reads the untouched Webflow export in src/ and writes a complete static site
into dist/. src/ is never modified, so any run is reproducible and a bad run is
undone by deleting dist/.
"""

import argparse
import html as htmllib
import json
import os
import re
import shutil
import sys
import urllib.parse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cmsdata
import wfconfig as CFG
import wfhtml as W

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

# The Webflow export lives in src/, deliberately not at the repository root.
# A root full of ready-looking index.html/css/images is dangerous: if Vercel is
# ever pointed at the root it will happily publish the *unbound* templates -
# empty collection lists, "No items found." everywhere - and the deploy looks
# successful. With the export under src/ that misconfiguration 404s instead.
SRC = os.path.join(ROOT, "src")

STATIC_DIRS = ["css", "js", "images", "fonts", "documents"]

STATIC_META = {
    "bankers-notes.html": {
        "title": "Bankers Notes | Dr. Mohal Banker | Bankers Vascular Centre",
        "desc": "Expert notes, practical guidance, and treatment insights personally shared by Dr. Mohal Banker.",
    },
    "bng-con-2025.html": {
        "title": "BnG Con 2025 | Bankers Vascular Centre",
        "desc": "Learn about BnG Con 2025, a Bankers Vascular Centre conference for vascular and interventional radiology professionals.",
    },
    "bng-conference-november-2024.html": {
        "title": "BnG Conference November 2024 | Bankers Vascular Centre",
        "desc": "Highlights from the November 2024 BnG Conference at Bankers Vascular Centre.",
    },
}

# Verified consultation/branch locations used only on their matching city pages.
CITY_LOCATION_DATA = {
    "rajkot": {
        "eyebrow": "Rajkot consultation location",
        "heading": "Visit us at Akanksha IVF Hospital",
        "name": "Akanksha IVF Hospital",
        "address": "Akshar Square, near Raiya Circle, Tirupati Nagar, Rajkot, Gujarat 360001",
        "phone": "+91-93282-94934",
        "city": "Rajkot",
        "postal_code": "360001",
    },
    "bhavnagar": {
        "eyebrow": "Bhavnagar consultation location",
        "heading": "Visit us at Bajrangdas Arogyadham",
        "name": "Shree Bajrangdasbapa Arogyadham",
        "address": "Chowk, Panwadi, Bhavnagar, Gujarat 364001",
        "phone": "+91-278-664-0664",
        "city": "Bhavnagar",
        "postal_code": "364001",
    },
    "surat": {
        "eyebrow": "Surat consultation location",
        "heading": "Visit us at Gastron Hospital",
        "name": "Gastron Hospital - By Dr Vimal Dhaduk",
        "address": "202, Ayush Doctor House Station to Lal Darwaja Station Road, Lal Darwaja, Surat, Gujarat 395003",
        "phone": "+91-72111-40222",
        "city": "Surat",
        "postal_code": "395003",
    },
    "vadodara": {
        "eyebrow": "Vadodara branch",
        "heading": "Visit Bankers Vascular Centre in Vadodara",
        "name": "Bankers Vascular Centre",
        "address": "2nd Floor, Ignite, 201, Above Meera Clinic and Eye Hospital, Opp. Agrawal Cars, Laxmi Colony, Anand Nagar, Akota, Vadodara, Gujarat 390007",
        "phone": "+91-99099-08428",
        "city": "Vadodara",
        "postal_code": "390007",
    },
    "rajasthan": {
        "eyebrow": "Rajasthan consultation location",
        "heading": "Visit us at Gyayak Hospital, Banswara",
        "name": "GYAYAK HOSPITAL",
        "address": "GCHF+3J5, 40, Banswara Road, Industrial Area, Banswara, Rajasthan 327001",
        "phone": "+91-74140-32100",
        "city": "Banswara",
        "postal_code": "327001",
    },
}


# Shell pages copied through the shell-rewrite pass.
def shell_pages():
    pages = sorted(
        f for f in os.listdir(SRC)
        if f.endswith(".html") and f not in CFG.EXCLUDE_PAGES
    )
    return pages + sorted(CFG.EXTRA_SHELL_PAGES)


warnings = []


def warn(msg):
    warnings.append(msg)


# --------------------------------------------------------------- URL rewriting

# index.html -> /, everything else -> /<name>, with the three directory pages
# mapped to their folder form.
def page_url(filename):
    extra = CFG.EXTRA_SHELL_PAGES.get(filename)
    if extra:
        return extra["url"]
    if filename == "index.html":
        return "/"
    if filename in CFG.DIRECTORY_PAGES:
        return "/" + CFG.DIRECTORY_PAGES[filename].rsplit("/", 1)[0]
    return "/" + filename[:-len(".html")]


PAGE_URLS = None  # filled in main()

# Historic URLs still occur in exported CMS rich text and Webflow shells.
# Resolve them while building so they cannot reintroduce internal 404s.
LEGACY_INTERNAL_PATHS = {
    "/departments/platelet-rich-plasma": "/treatment/platelet-rich-plasma",
    "/departments/varicose-vein": "/departments/varicose-veins",
    "/varicose-vein": "/varicose-veins/ahmedabad",
    "/varicose-vein/": "/varicose-veins/ahmedabad",
}


def rewrite_links(html):
    """Make every in-page reference root-absolute.

    Generated CMS pages live one directory deep, so the export's relative
    'css/…' / 'images/…' / 'about.html' references would resolve wrongly there.
    Root-absolute paths remove the whole class of depth bugs at once. The CSS
    file is left alone: its '../images/' is already correct relative to /css/.
    """
    def fix(url):
        u = url.strip()
        if not u or u.startswith((
            "#", "/", "http://", "https://", "mailto:", "tel:", "data:",
            "javascript:",
        )):
            return url
        u = re.sub(r"^\./", "", u)
        u = re.sub(r"^(\.\./)+", "", u)
        base = u.split("?")[0].split("#")[0]
        tail = u[len(base):]
        if base in PAGE_URLS:
            return PAGE_URLS[base] + tail
        for d in STATIC_DIRS:
            if base.startswith(d + "/"):
                return "/" + u
        if base.endswith(".html"):
            return "/" + base[:-len(".html")] + tail
        return url

    def attr_sub(m):
        return '%s="%s"' % (m.group(1), fix(m.group(2)))

    html = re.sub(r'\b(href|src)="([^"]*)"', attr_sub, html)

    # The exported sidebar and CTA links use a Bitly redirect. Point visitors
    # directly to WhatsApp so the destination is transparent and dependable.
    html = html.replace(
        "https://bit.ly/4cMeFYa",
        "https://api.whatsapp.com/send/?phone=%2B919909908428&amp;text=&amp;type=phone_number&amp;app_absent=0",
    )

    def srcset_sub(m):
        parts = []
        for chunk in m.group(1).split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            bits = chunk.split(None, 1)
            bits[0] = fix(bits[0])
            parts.append(" ".join(bits))
        return 'srcset="%s"' % ", ".join(parts)

    html = re.sub(r'srcset="([^"]*)"', srcset_sub, html)

    # Keep in-content links to the live domain on-site.
    html = re.sub(
        r'https?://(?:www\.)?bankersvascular\.com(?=[/"\'\s])',
        "", html,
    )
    html = html.replace('href=""', 'href="/"')
    for old, new in LEGACY_INTERNAL_PATHS.items():
        html = html.replace('href="%s"' % old, 'href="%s"' % new)
    return html


# ------------------------------------------------------------------- head meta

def _esc_attr(s):
    return htmllib.escape(s or "", quote=True)


def set_head_meta(html, title=None, desc=None, image=None, canonical=None,
                  noindex=False):
    if title is not None:
        html = re.sub(r"<title>.*?</title>",
                      lambda m: "<title>%s</title>" % htmllib.escape(title),
                      html, count=1, flags=re.S)
    def meta(pattern, value):
        nonlocal html
        if value is None:
            return
        attr = pattern.replace("\\", "")
        # Webflow exports meta attributes in both orders. Match the entire tag
        # by its identifying attribute rather than assuming content comes first.
        rx = re.compile(r'<meta(?=[^>]*\b%s)[^>]*>' % re.escape(attr))
        repl = '<meta content="%s" %s>' % (_esc_attr(value), attr)
        if rx.search(html):
            html = rx.sub(lambda m: repl, html, count=1)
        else:
            html = html.replace("</head>", "  %s\n</head>" % repl, 1)

    meta('name="description"', desc)
    meta('property="og:title"', title)
    meta('property="og:description"', desc)
    meta('property="og:image"', image)
    meta('name="twitter:title"', title)
    meta('name="twitter:description"', desc)
    meta('name="twitter:image"', image)

    if canonical is not None:
        html = re.sub(r'<link href="[^"]*" rel="canonical">',
                      '<link href="%s" rel="canonical">' % _esc_attr(canonical),
                      html, count=1)
    if noindex and "<title>" in html:
        html = html.replace("</head>", '  <meta name="robots" content="noindex">\n</head>', 1)
    return html


def ensure_meta_description(html):
    """Give indexable pages a useful fallback when a CMS row has no excerpt."""
    has_description = re.search(
        r'<meta[^>]+name="description"[^>]+content="[^\"]+"|'
        r'<meta[^>]+content="[^\"]+"[^>]+name="description"', html, re.I)
    if has_description:
        return html
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    subject = re.sub(r"\s+", " ", htmllib.unescape(title.group(1) if title else ""))
    subject = subject.replace(CFG.BRAND_TITLE, "").strip(" |-")
    return set_head_meta(
        html,
        desc=("Learn about %s at Bankers Vascular Centre. "
              "Contact our team to book a consultation." % subject)[:300],
    )


def enforce_single_h1(html):
    """Keep the first page H1 and demote accidental additional H1s."""
    matches = list(re.finditer(r"</?h1\b[^>]*>", html, re.I))
    if len(matches) <= 2:
        return html
    first_close = next((i for i, m in enumerate(matches) if m.group(0).lower().startswith("</")), None)
    if first_close is None:
        return html
    keep_until = matches[first_close].end()
    head, tail = html[:keep_until], html[keep_until:]
    tail = re.sub(r"<(/?)h1(?=[\s>])", r"<\1h2", tail, flags=re.I)
    return head + tail


# ------------------------------------------------------------------- rich text

_BARE_HOST = re.compile(r"^https?://[^/]+/?$", re.I)


def meaningful_url(u):
    """False for empty values and bare domains like 'https://www.facebook.com/'.

    Linking a doctor's 'profile' at facebook.com's homepage is worse than
    showing no icon, so those get dropped.
    """
    u = (u or "").strip()
    return bool(u) and not _BARE_HOST.match(u)


def clean_richtext(rt, assets):
    """Prepare CMS rich text for static hosting."""
    if not rt:
        return ""
    rt = assets.rewrite(rt)
    # Webflow leaves empty id="" on every element; they are noise and
    # duplicate ids are invalid HTML.
    rt = re.sub(r'\s+id=""', "", rt)
    # Keep internal links on-site; open external ones safely.
    rt = re.sub(r'https?://(?:www\.)?bankersvascular\.com(?=[/"\'])', "", rt)
    for old, new in LEGACY_INTERNAL_PATHS.items():
        rt = rt.replace('href="%s"' % old, 'href="%s"' % new)

    def anchor(m):
        tag = m.group(0)
        href = W.get_attr(tag, "href") or ""
        if href.startswith(("http://", "https://")):
            if 'target=' not in tag:
                tag = W.set_attr(tag, "target", "_blank")
            tag = W.set_attr(tag, "rel", "noopener")
        return tag

    rt = re.sub(r"<a\s[^>]*>", anchor, rt)
    # CMS images must not block first paint.
    rt = re.sub(r"<img\s(?![^>]*loading=)", '<img loading="lazy" ', rt)
    # The page template supplies the document H1. Demote pasted rich-text H1s
    # so each indexable page has one unambiguous primary heading.
    rt = re.sub(r"<(/?)h1(?=[\s>])", r"<\1h2", rt, flags=re.I)
    # Webflow's reserved placeholder is not meaningful alternative text.
    rt = re.sub(r'\balt=("|\')__wf_reserved_inherit\1',
                'alt="Medical treatment illustration"', rt)
    return rt


# ------------------------------------------------------------- item rendering

class Binder:
    """Applies a binding set to one cloned collection item."""

    def __init__(self, assets):
        self.assets = assets

    def value(self, item, field):
        """Resolve a field spec: a name, a fallback list, or an @-expression."""
        if isinstance(field, list):
            for f in field:
                v = self.value(item, f)
                if v:
                    return v
            return ""
        if field == "@date":
            d = item.get("_date")
            return d.strftime("%B %d, %Y") if d else ""
        if isinstance(field, str) and field.startswith("@author."):
            author = item.get("_author")
            if not author:
                return ""
            return (author.get(field[len("@author."):]) or "").strip()
        return (item.get(field) or "").strip()

    def apply(self, frag, item, bindings, url=None):
        url = url if url is not None else item.get("_url")
        for b in bindings:
            kind = b["kind"]
            if kind == "link":
                target = self.value(item, b["field"]) if b.get("field") else url
                frag = self._links(frag, target)
            elif kind == "self_text_link":
                frag = self._links(frag, url)
                frag = self._set_text_root(frag, item.name)
            elif kind == "price":
                frag = self._price(frag, self.value(item, b["field"]))
            else:
                frag = self._one(frag, item, b, url)
        return frag

    # -- individual binding kinds

    def _one(self, frag, item, b, url):
        start = W.find_bound(frag, b["cls"])
        if start < 0:
            return frag
        val = self.value(item, b["field"])
        kind = b["kind"]

        # An empty value with on_empty drops the element - or a named ancestor -
        # rather than leaving an empty node or Webflow's grey placeholder image.
        if not val and b.get("on_empty"):
            mode = b["on_empty"]
            if mode == "remove":
                s, e = W.find_block(frag, start)
                return frag[:s] + frag[e:]
            if mode.startswith("remove:"):
                wrapper = mode.split(":", 1)[1]
                blk = W.block_by_class(frag, wrapper)
                if blk:
                    return frag[:blk[0]] + frag[blk[1]:]
                s, e = W.find_block(frag, start)
                return frag[:s] + frag[e:]

        if kind == "img":
            if not val:
                return frag  # leave the placeholder rather than emit src=""
            src = self.assets.url(val)
            alt = self.value(item, b["alt"]) if b.get("alt") else ""
            def fix_img(tag):
                tag = W.set_attr(tag, "src", _esc_attr(src))
                tag = W.del_attr(tag, "srcset")
                tag = W.del_attr(tag, "sizes")
                tag = W.set_attr(tag, "alt", _esc_attr(alt))
                if "loading=" not in tag:
                    tag = W.set_attr(tag, "loading", "lazy")
                return W.drop_class(tag, "w-dyn-bind-empty")
            return W.edit_open_tag(frag, start, fix_img)

        if kind == "bg":
            if not val:
                return frag
            src = self.assets.url(val)
            style = 'background-image:url(&quot;%s&quot;)' % _esc_attr(src)
            return W.edit_open_tag(frag, start,
                                   lambda t: W.set_attr(t, "style", style))

        if kind == "richtext":
            body = clean_richtext(val, self.assets)
        elif kind == "text":
            body = htmllib.escape(val)
        else:
            raise ValueError("unknown binding kind %r" % kind)

        if not val:
            return frag
        frag = W.edit_open_tag(frag, start,
                              lambda t: W.drop_class(t, "w-dyn-bind-empty"))
        return W.set_inner(frag, W.find_block(frag, start), body)

    def _links(self, frag, target):
        if not target:
            return frag
        out, pos = [], 0
        for m in re.finditer(r'<a\s[^>]*href="#"[^>]*>', frag):
            tag = m.group(0)
            new = W.set_attr(tag, "href", _esc_attr(target))
            new = W.drop_class(new, "w-dyn-bind-empty")
            if target.startswith("http"):
                new = W.set_attr(new, "target", "_blank")
                new = W.set_attr(new, "rel", "noopener")
            out.append(frag[pos:m.start()])
            out.append(new)
            pos = m.end()
        out.append(frag[pos:])
        return "".join(out)

    def _set_text_root(self, frag, text):
        """Set the label on the item's anchor.

        Target the <a> specifically: in the Treatment dropdown the wrapping
        toggle <div> carries the same `nav-dropdown-link` class, and writing to
        that would wipe out the anchor inside it.
        """
        m = re.search(r"<a\s[^>]*>", frag)
        if not m:
            return frag
        start = m.start()
        frag = W.edit_open_tag(frag, start,
                              lambda t: W.drop_class(t, "w-dyn-bind-empty"))
        return W.set_inner(frag, W.find_block(frag, start),
                           htmllib.escape(text))

    def _price(self, frag, price):
        """The price <p> has no class of its own; it is the bound <p> inside the
        'Rs.' link block."""
        blk = W.block_by_class(frag, "link-block-15")
        if not blk:
            return frag
        seg = frag[blk[0]:blk[1]]
        i = W.find_by_class(seg, "w-dyn-bind-empty")
        if i < 0:
            return frag
        if not price:
            # No price on file: drop the whole "Rs. ___" link rather than
            # showing a bare "Rs." with nothing after it.
            return frag[:blk[0]] + frag[blk[1]:]
        try:
            shown = "{:,}".format(int(float(price)))
        except ValueError:
            shown = price
        seg = W.edit_open_tag(seg, i, lambda t: W.drop_class(t, "w-dyn-bind-empty"))
        seg = W.set_inner(seg, W.find_block(seg, i), htmllib.escape(shown))
        return frag[:blk[0]] + seg + frag[blk[1]:]


# ------------------------------------------------------------- list population

def find_list(html, spec):
    """Locate (dyn_list_block, items_block) for a list spec."""
    if spec.get("container_cls"):
        outer = W.block_by_class(html, spec["container_cls"])
        if not outer:
            return None
        base = outer[0]
        lst = W.block_by_class(html, "w-dyn-list", base, outer[1])
    elif spec.get("items_cls"):
        i = W.find_by_class(html, spec["items_cls"])
        if i < 0:
            return None
        lst_start = W.open_tag_start(html, html.rfind("w-dyn-list", 0, i))
        lst = W.find_block(html, lst_start)
    else:
        i = W.find_by_class(html, spec["item_cls"])
        if i < 0:
            return None
        lst_start = W.open_tag_start(html, html.rfind("w-dyn-list", 0, i))
        lst = W.find_block(html, lst_start)
    if not lst:
        return None
    items = W.block_by_class(html, "w-dyn-items", lst[0], lst[1])
    return lst, items


def populate(html, spec, items, binder, urls=None, occurrence=0):
    """Fill one w-dyn-list with `items`, cloning its placeholder item."""
    found = find_list(html, spec)
    if not found:
        warn("list not found: %r" % (spec.get("items_cls") or spec.get("item_cls")
                                     or spec.get("container_cls")))
        return html
    lst, items_block = found
    seg = html[lst[0]:lst[1]]

    tpl_rel = W.block_by_class(seg, "w-dyn-item")
    if not tpl_rel:
        warn("no w-dyn-item template in list %r" % spec.get("items_cls"))
        return html
    template = seg[tpl_rel[0]:tpl_rel[1]]

    bindings = CFG.ITEM_BINDINGS[spec["bindings"]]
    field_overrides = spec.get("field_overrides", {})
    rendered = []
    for n, it in enumerate(items):
        url = urls[n] if urls else None
        overrides = field_overrides.get(it.get("Slug"), {})
        render_item = dict(it) if overrides else it
        if overrides:
            render_item.update(overrides)
        rendered.append(binder.apply(template, render_item, bindings, url=url))
    body = "".join(rendered)

    # Replace the items container's contents, then drop the "No items found."
    # sibling now that the list is populated.
    items_rel = (items_block[0] - lst[0], items_block[1] - lst[0])
    seg = W.set_inner(seg, items_rel, body)
    empty = W.block_by_class(seg, "w-dyn-empty")
    if empty:
        if items:
            seg = seg[:empty[0]] + seg[empty[1]:]
        else:
            # A genuinely empty list keeps its empty-state block, but Webflow's
            # default "No items found." reads like a bug to a visitor.
            seg = W.set_inner(seg, empty,
                              "<div>%s</div>" % spec.get(
                                  "empty_text", "Nothing here yet."))
    if spec.get("drop_pagination"):
        pg = W.block_by_class(seg, "w-pagination-wrapper")
        if pg:
            seg = seg[:pg[0]] + seg[pg[1]:]
    return html[:lst[0]] + seg + html[lst[1]:]


def remove_dead_lists(html):
    """Delete Webflow template lists that have no CMS binding at all."""
    for cls in CFG.DEAD_LISTS:
        blk = W.block_by_class(html, cls)
        if blk:
            html = html[:blk[0]] + html[blk[1]:]
    return html


def remove_template_junk(html):
    """Remove the hidden nav <li> full of dead medicio.webflow.io demo links."""
    while True:
        i = html.find('<li class="nav-list-item position-relative hide">')
        if i < 0:
            break
        s, e = W.find_block(html, i)
        html = html[:s] + html[e:]
    # Any stragglers pointing at the template demo site.
    if "medicio.webflow.io" in html:
        html = re.sub(r'href="https?://medicio\.webflow\.io[^"]*"', 'href="/"', html)
    return html


def order_items(cms, spec):
    key = spec["collection"]
    order = spec.get("order")
    if order == "newest":
        items = cms.blogs_newest()
    elif isinstance(order, tuple):
        field, mode = order
        items = cms.sorted_by(key, field, numeric=(mode == "numeric"))
    else:
        items = list(cms.published[key])
    if spec.get("author_slug"):
        items = [item for item in items if item.get("_author") is not None
                 and item["_author"].slug == spec["author_slug"]]
    items = items[spec.get("offset", 0):]
    if spec.get("limit"):
        items = items[:spec["limit"]]
    return items


def apply_nav(html, cms, binder):
    # 401/404 are Webflow utility pages with no navbar at all.
    if "nav-menu-list-wrapper" not in html:
        return html
    for spec in CFG.NAV_LISTS:
        items = order_items(cms, spec)
        html = populate(html, spec, items, binder)
    return html


# ------------------------------------------------------------------ pagination

PAGINATION_TEMPLATE = None  # lifted from detail_treatment.html at startup


def load_pagination_template():
    src = read(os.path.join(SRC, "detail_treatment.html"))
    blk = W.block_by_class(src, "w-pagination-wrapper")
    return src[blk[0]:blk[1]] if blk else None


def build_pagination(page, total_pages, base):
    """Real prev/next controls using the export's own pagination markup."""
    if total_pages < 2 or not PAGINATION_TEMPLATE:
        return ""
    def href(p):
        return base if p == 1 else "%s/page/%d" % (base.rstrip("/"), p)
    frag = PAGINATION_TEMPLATE
    out, pos = [], 0
    for m in re.finditer(r'<a\s[^>]*href="#"[^>]*>', frag):
        tag = m.group(0)
        cls = W.get_attr(tag, "class") or ""
        if "w-pagination-previous" in cls:
            tag = (W.set_attr(tag, "href", href(page - 1)) if page > 1
                   else W.add_class(W.set_attr(tag, "href", "#"), "w-condition-invisible"))
        elif "w-pagination-next" in cls:
            tag = (W.set_attr(tag, "href", href(page + 1)) if page < total_pages
                   else W.add_class(W.set_attr(tag, "href", "#"), "w-condition-invisible"))
        out.append(frag[pos:m.start()]); out.append(tag); pos = m.end()
    out.append(frag[pos:])
    frag = "".join(out)
    # Hidden controls must not be clickable.
    frag = frag.replace('href="#"', 'href="#" aria-disabled="true" tabindex="-1"')
    return frag


# ------------------------------------------------------------------- utilities

def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def dir_size(path):
    return sum(os.path.getsize(os.path.join(b, f))
               for b, _d, fs in os.walk(path) for f in fs)


def write(rel, content):
    path = os.path.join(DIST, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


# ----------------------------------------------------------------- form wiring

HONEYPOT = ('<input type="text" name="_gotcha" tabindex="-1" autocomplete="off" '
            'aria-hidden="true" style="position:absolute;left:-9999px;'
            'width:1px;height:1px;opacity:0">')


def canonical_field(tag, tagname):
    """Map the export's inconsistent field names onto one API contract.

    The same logical field is named four different ways across the site
    (Name / Name-2 / name-2 / name-3), and the phone input on 13 pages is
    misnamed 'email-2' while being type="tel". Normalising here means the
    endpoint has a single, checkable contract.
    """
    name = (W.get_attr(tag, "name") or "").strip()
    itype = (W.get_attr(tag, "type") or "").lower()
    # Webflow reused `email-3` for several plain-text message inputs. The
    # visible placeholder/class is the reliable signal, not that export name.
    low = " ".join(filter(None, [
        name,
        W.get_attr(tag, "id"),
        W.get_attr(tag, "placeholder"),
        W.get_attr(tag, "class"),
        W.get_attr(tag, "data-name"),
    ])).lower()
    if tagname == "textarea":
        return "Message"
    if "message" in low or "text-area" in low:
        return "Message"
    if "phone" in low or "mobile" in low or itype == "tel":
        return "Phone-Number"
    if low.startswith("name"):
        return "Name"
    if itype == "email":
        return "Email"
    if "email" in low:
        return "Email"
    if "date" in low:
        return "Date"
    if "message" in low or low.startswith("field"):
        return "Message"
    return name


def normalize_form_fields(seg):
    out, pos = [], 0
    for m in re.finditer(r"<(input|textarea|select)\s[^>]*>", seg):
        tag = m.group(0)
        if (W.get_attr(tag, "type") or "").lower() in ("submit", "hidden"):
            out.append(seg[pos:m.end()]); pos = m.end()
            continue
        if W.get_attr(tag, "name") == "_gotcha":
            out.append(seg[pos:m.end()]); pos = m.end()
            continue
        canon = canonical_field(tag, m.group(1))
        if canon:
            tag = W.set_attr(tag, "name", canon)
        out.append(seg[pos:m.start()]); out.append(tag); pos = m.end()
    out.append(seg[pos:])
    return "".join(out)


def ensure_submit(seg, page_label):
    """Give the contact form a real submit control.

    Four forms have no <input type="submit"> at all - their only button is
    <a href="#" class="outline-button">Send Message</a>, an anchor that cannot
    submit anything. Converting it to <button type="submit"> keeps every class
    (so the styling and hover interaction are unchanged) and makes the form
    actually work.
    """
    if 'type="submit"' in seg:
        return seg, False
    i = W.find_by_class(seg, "outline-button")
    if i < 0:
        warn("form on %s has no submit control and no outline-button to convert"
             % page_label)
        return seg, False
    s, e = W.find_block(seg, i)
    anchor = seg[s:e]
    open_m = re.match(r"<a\s[^>]*>", anchor)
    attrs = open_m.group(0)
    inner = anchor[open_m.end():anchor.rfind("</a>")]
    cls = W.get_attr(attrs, "class") or ""
    wid = W.get_attr(attrs, "data-w-id")
    btn = '<button type="submit" class="%s"%s data-wait="Please wait...">%s</button>' % (
        cls, ' data-w-id="%s"' % wid if wid else "", inner)
    return seg[:s] + btn + seg[e:], True


def wire_forms(html, page_label):
    """Point Webflow's dead forms at the serverless endpoint.

    Every form in the export is method="get" with no action, so submissions are
    silently dropped once the site leaves Webflow. They keep their existing
    markup and their `w-form-done` / `w-form-fail` blocks; js/forms.js drives
    those states from the POST result.
    """
    count = 0
    # Form metadata is displayed in notification emails. Use reader-friendly
    # labels instead of Webflow's export names such as "Email Form 2".
    page_display = {
        "contact-us.html": "Contact page",
    }.get(page_label, page_label.removesuffix(".html").replace("-", " ").title() + " page")
    out, pos = [], 0
    for m in re.finditer(r"<form\s[^>]*>", html):
        if m.start() < pos:
            continue
        tag = m.group(0)
        if "/.wf_auth" in tag:          # Webflow password page, not a lead form
            out.append(html[pos:m.end()]); pos = m.end()
            continue
        fstart, fend = W.find_block(html, m.start())
        seg = html[fstart:fend]
        name = W.get_attr(tag, "data-name") or W.get_attr(tag, "name") or "Form"
        if page_label == "contact-us.html":
            name = "Contact"

        new_tag = W.set_attr(tag, "method", "post")
        new_tag = W.set_attr(new_tag, "action", "/api/contact")
        new_tag = W.set_attr(new_tag, "data-form-name", _esc_attr(name))
        new_tag = W.set_attr(new_tag, "data-form-page", _esc_attr(page_display))
        for dead in ("data-wf-page-id", "data-wf-element-id", "redirect",
                     "data-redirect"):
            new_tag = W.del_attr(new_tag, dead)

        seg = new_tag + HONEYPOT + seg[m.end() - fstart:]
        seg = normalize_form_fields(seg)
        seg, _converted = ensure_submit(seg, page_label)

        out.append(html[pos:fstart])
        out.append(seg)
        pos = fend
        count += 1
    out.append(html[pos:])
    html = "".join(out)
    if count and "/js/forms.js" not in html:
        html = html.replace("</body>",
                            '  <script src="/js/forms.js" defer></script>\n</body>', 1)
    return html


# ------------------------------------------------------- dead-link repairs

def fix_dead_links(html):
    """Repair anchors the export left pointing at '#'.

    Only unambiguous cases: brand logos, the single-locale switcher, and the
    footer 'Training' link whose target page exists. Interaction-driven toggles
    (the chat widget) legitimately keep href="#".
    """
    # Brand logos in the mobile nav and the footer.
    html = re.sub(r'<a href="#"(\s+class="navbar-brand)', r'<a href="/"\1', html)
    # Single-locale switcher.
    html = re.sub(r'<a hreflang="en" href="#"', '<a hreflang="en" href="/"', html)

    # Footer link whose label names a page that exists.
    labels = {"Training": "/training", "Home": "/", "Blog": "/blog",
              "Contact Us": "/contact-us", "Departments": "/departments",
              "About Us": "/about-banker-vascular-center"}
    def footer_link(m):
        block = m.group(0)
        label = re.search(r"<div>([^<]+)</div>\s*</a>\s*$", block)
        if label:
            target = labels.get(label.group(1).strip())
            if target:
                return block.replace('href="#"', 'href="%s"' % target, 1)
        return block

    html = re.sub(r'<a href="#"\s+class="footer-link-two[^"]*"[^>]*>.*?</a>',
                  footer_link, html, flags=re.S)
    return html


def add_seo_internal_links(html, url):
    """Create visible, contextual routes between conditions, procedures and cities."""
    city_links = {
        "varicose": [
            ("Ahmedabad", "/varicose-veins/ahmedabad"), ("Vadodara", "/varicose-veins/vadodara"),
            ("Rajkot", "/varicose-veins/rajkot"), ("Surat", "/varicose-veins/surat"),
            ("Bhavnagar", "/varicose-veins/bhavnagar"), ("Rajasthan", "/varicose-veins/rajasthan")],
        "knee": [
            ("Ahmedabad", "/non-surgical-knee-pain/ahmedabad"), ("Vadodara", "/non-surgical-knee-pain/vadodara"),
            ("Rajkot", "/non-surgical-knee-pain/rajkot"), ("Surat", "/non-surgical-knee-pain/surat"),
            ("Bhavnagar", "/non-surgical-knee-pain/bhavnagar"), ("Rajasthan", "/non-surgical-knee-pain/rajasthan")],
    }
    links = []
    heading = "Related treatment information"
    if url == "/departments/varicose-veins":
        heading = "Varicose veins treatment locations"
        links = city_links["varicose"] + [("VenaSeal Glue Treatment", "/treatment/venaseal-glue-embolization"), ("Radiofrequency Ablation", "/treatment/radiofrequency-ablation")]
    elif url == "/departments/knee-pain" or url == "/treatment/genicular-artery-embolization":
        heading = "Non-surgical knee pain treatment locations"
        links = city_links["knee"] + [("Genicular Artery Embolization", "/treatment/genicular-artery-embolization")]
    elif url.startswith("/varicose-veins/"):
        links = [("Varicose veins treatment", "/departments/varicose-veins"), ("VenaSeal Glue Treatment", "/treatment/venaseal-glue-embolization"), ("Radiofrequency Ablation", "/treatment/radiofrequency-ablation")]
    elif url.startswith("/non-surgical-knee-pain/"):
        links = [("Knee pain treatment", "/departments/knee-pain"), ("Genicular Artery Embolization", "/treatment/genicular-artery-embolization")]
    elif url.startswith("/blog/"):
        slug = url.lower()
        if any(k in slug for k in ("varicose", "vein", "venaseal")):
            links = [("Varicose veins treatment", "/departments/varicose-veins"), ("Varicose veins treatment in Ahmedabad", "/varicose-veins/ahmedabad")]
        elif any(k in slug for k in ("knee", "gae", "genicular", "arthritis")):
            links = [("Genicular Artery Embolization", "/treatment/genicular-artery-embolization"), ("Non-surgical knee pain treatment in Ahmedabad", "/non-surgical-knee-pain/ahmedabad")]
        elif any(k in slug for k in ("prostate", "bph", "urination")):
            links = [("Prostate artery embolization", "/treatment/prostate-artery-embolization"), ("Non-surgical prostate treatment", "/departments/prostate")]
        elif any(k in slug for k in ("piles", "hemorrhoid", "stool")):
            links = [("Hemorrhoids treatment", "/treatment/hemorrhoids"), ("Non-surgical piles treatment", "/departments/piles")]
        elif "fibroadenoma" in slug:
            links = [("Non-surgical breast fibroadenoma treatment", "/departments/breast-fibroadenoma")]
    if not links or 'data-seo-links="true"' in html:
        return html
    items = "".join('<li><a href="%s">%s</a></li>' % (href, htmllib.escape(label)) for label, href in links)
    location = ""
    city = url.rsplit("/", 1)[-1]
    location_data = CITY_LOCATION_DATA.get(city) if url.startswith(("/varicose-veins/", "/non-surgical-knee-pain/")) else None
    if location_data:
        query = urllib.parse.quote_plus("%s, %s" % (location_data["name"], location_data["address"]))
        location = (
            '<section class="seo-location-section" aria-label="%s">'
            '<div class="seo-location-copy"><p class="seo-location-eyebrow">%s</p>'
            '<h2>%s</h2><p>Visit <strong>%s</strong> at %s.</p>'
            '<a class="seo-location-button" href="https://www.google.com/maps/search/?api=1&amp;query=%s" '
            'target="_blank" rel="noopener">Get directions <span aria-hidden="true">↗</span></a></div>'
            '<div class="seo-location-map"><iframe loading="lazy" title="%s" '
            'src="https://www.google.com/maps?q=%s&amp;output=embed" '
            'referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe></div>'
            '</section>' % tuple(htmllib.escape(value) for value in (
                location_data["eyebrow"], location_data["eyebrow"], location_data["heading"],
                location_data["name"], location_data["address"], query,
                location_data["name"], query,
            ))
        )
    module = ('<section class="seo-links-section" data-seo-links="true" aria-label="Related treatment links">'
              '<div class="seo-links-inner"><h2>%s</h2><ul>%s</ul>%s</div></section>'
              % (htmllib.escape(heading), items, location))
    return html.replace("<footer", module + "<footer", 1)


# ------------------------------------------------------------------- shell pass

def prepare_shell(html, cms, binder, page_label):
    """Transforms every page gets, CMS shells and detail templates alike."""
    # The exported blog template carries one generic FAQPage JSON-LD block on
    # every article, irrespective of visible FAQ content. Remove it; FAQ schema
    # should only be emitted for pages with matching visible questions/answers.
    html = re.sub(r'<script type="application/ld\+json">\s*\{[^<]*"@type"\s*:\s*"FAQPage"[^<]*\}\s*</script>',
                  '', html, flags=re.S)
    # Video/maps below the fold should not compete with the hero for bandwidth.
    html = re.sub(r'<iframe\b(?![^>]*\bloading=)', '<iframe loading="lazy"', html,
                  flags=re.I)
    html = remove_template_junk(html)
    html = remove_dead_lists(html)
    html = rewrite_links(html)
    html = fix_dead_links(html)
    html = apply_nav(html, cms, binder)
    html = wire_forms(html, page_label)
    return html


def add_bankers_notes_nav(html, current=False):
    """Add the personal-notes link beside Blog on every site header."""
    if 'href="/bankers-notes"' in html:
        return html
    if current:
        html = html.replace(
            'href="/blog" aria-current="page" class="nav-link text-block-8 w--current"',
            'href="/blog" class="nav-link text-block-8"', 1)
    link = ('<li class="nav-list-item position-relative">\n'
            '                  <div class="nav-line"></div>\n'
            '                  <a href="/bankers-notes"%s class="nav-link text-block-8%s">Bankers Notes</a>\n'
            '                </li>') % (
                ' aria-current="page"' if current else '',
                ' w--current' if current else '')
    pattern = (r'(<li class="nav-list-item position-relative">\s*'
               r'<div class="nav-line"></div>\s*'
               r'<a href="/blog"[^>]*>Blog</a>\s*</li>)')
    return re.sub(pattern, r'\1\n                ' + link, html, count=1)


def customise_bankers_notes(html):
    """Turn the cloned blog archive into Dr. Mohal Banker's personal page."""
    html = html.replace("Our Blog", "Bankers Notes")
    html = html.replace("Latest blog articles<br>", "Notes from Dr. Mohal Banker<br>")
    html = html.replace(
        "Are you willing to not going for any operative procedure in your body? Than interventional radiologist is a right choice for your treatment. Interventional radiologist treat different disease with small needle puncture, without any kind of cut or suture.",
        "Expert notes, practical guidance, and treatment insights personally shared by Dr. Mohal Banker.")
    html = html.replace('class="about-hero-section about">',
                        'class="about-hero-section about bankers-notes-hero">', 1)
    return html


def build_shells(pages, cms, binder, assets):
    written = []
    for page in pages:
        extra = CFG.EXTRA_SHELL_PAGES.get(page, {})
        source = extra.get("source", page)
        html = prepare_shell(read(os.path.join(SRC, source)), cms, binder, page)
        if page == "bankers-notes.html":
            html = customise_bankers_notes(html)
        html = add_bankers_notes_nav(html, current=(page == "bankers-notes.html"))
        out_rel = extra.get("output", CFG.DIRECTORY_PAGES.get(page, page))
        url = page_url(page)
        specs = CFG.PAGE_LISTS.get(page, [])

        paginated = [s for s in specs if s.get("paginate")]
        plain = [s for s in specs if not s.get("paginate")]
        for spec in plain:
            html = populate(html, spec, order_items(cms, spec), binder)

        if not paginated:
            metadata = STATIC_META.get(page, {})
            html = set_head_meta(html, title=metadata.get("title"),
                                 desc=metadata.get("desc"), canonical=CFG.SITE_URL + url,
                                 noindex=page in CFG.NOINDEX_PAGES)
            if page not in CFG.NOINDEX_PAGES:
                html = add_seo_internal_links(ensure_meta_description(enforce_single_h1(html)), url)
                html = add_page_schema(html, url)
            write(out_rel, html)
            written.append((out_rel, url, page not in CFG.NOINDEX_PAGES))
            continue

        spec = paginated[0]
        items = order_items(cms, spec)
        per = spec["paginate"]
        total = max(1, -(-len(items) // per))
        for p in range(1, total + 1):
            chunk = items[(p - 1) * per: p * per]
            page_html = populate(html, spec, chunk, binder)
            controls = build_pagination(p, total, url)
            if controls:
                found = find_list(page_html, spec)
                if found:
                    lst = found[0]
                    page_html = (page_html[:lst[1] - len("</div>")] + controls
                                 + page_html[lst[1] - len("</div>"):])
            rel = out_rel if p == 1 else "%s/page/%d.html" % (
                out_rel.rsplit("/", 1)[0] if "/" in out_rel else out_rel[:-5], p)
            purl = url if p == 1 else "%s/page/%d" % (url.rstrip("/"), p)
            metadata = STATIC_META.get(page, {})
            page_html = set_head_meta(
                page_html, canonical=CFG.SITE_URL + purl,
                title=metadata.get("title") if p == 1 else "%s - Page %d %s" % (
                    "Bankers Notes" if page == "bankers-notes.html" else "Blog", p,
                    CFG.BRAND_TITLE),
                desc=metadata.get("desc") if p == 1 else None)
            page_html = add_seo_internal_links(ensure_meta_description(enforce_single_h1(page_html)), purl)
            page_html = add_page_schema(page_html, purl)
            write(rel, page_html)
            written.append((rel, purl, True))
    return written


# ------------------------------------------------------------------ detail pass

def build_details(cms, binder, assets):
    written = []
    for spec in CFG.COLLECTIONS:
        tpl = spec.get("template")
        if not tpl:
            continue
        key = spec["key"]
        # The nav/junk/link/form work is identical for every item, so do it
        # once per template rather than 282 times.
        base = add_bankers_notes_nav(
            prepare_shell(read(os.path.join(SRC, tpl)), cms, binder, tpl))
        items = cms.published[key]
        for item in items:
            html = render_detail(base, spec, item, cms, binder, assets)
            rel = "%s/%s.html" % (spec["folder"], item.slug)
            write(rel, html)
            written.append((rel, item.url, True))
        print("  %-24s %3d pages" % (key, len(items)))
    return written


def render_detail(base, spec, item, cms, binder, assets):
    html = base

    for b in spec.get("bind", []):
        html = binder._one(html, item, b, item.url) if b["kind"] != "link" else html

    # The exported detail banners are desktop-wide canvases.  At phone and
    # tablet widths use a purpose-made version of *that item's* artwork so
    # every page keeps its own clinical image instead of sharing one banner.
    responsive_families = {
        "treatment": "about-hero-section",
        "departments": "new-combo",
        "varicose-veins": "new-combo",
        "non-surgical-knee-pain": "new-combo",
    }
    hero_class = responsive_families.get(spec["key"])
    if hero_class:
        hero = W.find_by_class(html, hero_class)
        if hero >= 0:
            mobile_asset = "../images/mobile-%s-%s.webp" % (spec["key"], item.slug)
            html = W.edit_open_tag(
                html, hero,
                lambda t: W.set_attr(
                    W.set_attr(
                        W.add_class(t, "responsive-treatment-hero"),
                        "data-mobile-hero", item.slug),
                    "style", (W.get_attr(t, "style") or "") +
                    ";--responsive-hero-image:url('%s')" % mobile_asset),
            )

    html = fill_repeated_richtext(html, spec, item, assets)
    html = fill_author_block(html, spec, item, assets)
    html = fill_socials(html, spec, item)
    html = fill_detail_lists(html, spec, item, cms, binder)

    title_txt = item.get_text(*spec.get("title", ["Name"]))
    tpl_title = re.search(r"<title>(.*?)</title>", base, re.S).group(1).strip()
    if tpl_title.startswith("|"):
        full_title = "%s %s" % (title_txt, tpl_title)
    else:
        full_title = "%s %s" % (title_txt, CFG.BRAND_TITLE)
    desc = item.get_text(*spec.get("desc", []))
    desc = re.sub(r"<[^>]+>", " ", desc)
    desc = re.sub(r"\s+", " ", htmllib.unescape(desc)).strip()[:300]
    og = item.get_text(*spec.get("og_image", []))
    html = set_head_meta(
        html,
        title=full_title.strip(),
        desc=desc,
        image=assets.url(og) if og else None,
        canonical=CFG.SITE_URL + item.url,
    )
    html = add_seo_internal_links(ensure_meta_description(enforce_single_h1(html)), item.url)
    html = add_article_schema(html, spec, item, assets)
    return add_page_schema(html, item.url, spec, item)


def fill_repeated_richtext(html, spec, item, assets):
    """Fill N identically-classed rich-text blocks in document order."""
    conf = spec.get("repeated_richtext")
    if not conf:
        return html
    cls, fields = conf["cls"], conf["fields"]
    # A cursor is essential here: the blocks keep their shared class after being
    # filled, so searching from 0 each time would rewrite the first block over
    # and over and leave the rest unbound.
    cursor = 0
    for field in fields:
        start = W.find_by_class(html, cls, cursor)
        if start < 0:
            break
        val = (item.get(field) or "").strip()
        if not val:
            # No content for this slot: remove the empty block so the page does
            # not render a stray gap.
            s, e = W.find_block(html, start)
            html = html[:s] + html[e:]
            cursor = s
            continue
        html = W.edit_open_tag(html, start,
                               lambda t: W.drop_class(t, "w-dyn-bind-empty"))
        block = W.find_block(html, start)
        html = W.set_inner(html, block, clean_richtext(val, assets))
        cursor = W.find_block(html, start)[1]
    return html


def fill_author_block(html, spec, item, assets):
    conf = spec.get("author_block")
    if not conf:
        return html
    author = item.get("_author")
    block = W.block_by_class(html, conf["container"])
    if not block:
        return html
    if not author:
        # No author, or the author is a draft: drop the block rather than show
        # an empty avatar and a link to nowhere.
        return html[:block[0]] + html[block[1]:]
    seg = html[block[0]:block[1]]
    pic = (author.get("Picture") or "").strip()
    i = W.find_by_class(seg, conf["image"])
    if i >= 0 and pic:
        src = assets.url(pic)
        seg = W.edit_open_tag(seg, i, lambda t: W.drop_class(
            W.set_attr(W.set_attr(W.del_attr(t, "srcset"), "src", _esc_attr(src)),
                       "alt", _esc_attr(author.name)), "w-dyn-bind-empty"))
    j = W.find_by_class(seg, conf["link"])
    if j >= 0:
        seg = W.edit_open_tag(seg, j, lambda t: W.drop_class(
            W.set_attr(t, "href", author.url), "w-dyn-bind-empty"))
        seg = W.set_inner(seg, W.find_block(seg, j), htmllib.escape(author.name))
    return html[:block[0]] + seg + html[block[1]:]


def fill_socials(html, spec, item):
    conf = spec.get("socials")
    if not conf:
        return html
    cls, fields = conf["cls"], conf["fields"]
    # Walk right-to-left so removing one anchor cannot shift the others.
    starts = list(W.iter_by_class(html, cls))[:len(fields)]
    for start, field in reversed(list(zip(starts, fields))):
        url = (item.get(field) or "").strip()
        s, e = W.find_block(html, start)
        if meaningful_url(url):
            seg = W.edit_open_tag(html[s:e], 0, lambda t: W.set_attr(
                W.set_attr(W.set_attr(t, "href", _esc_attr(url)),
                           "target", "_blank"), "rel", "noopener"))
            html = html[:s] + seg + html[e:]
        else:
            html = html[:s] + html[e:]
    return html


def fill_detail_lists(html, spec, item, cms, binder):
    for lspec in CFG.DETAIL_LISTS.get(spec.get("template"), []):
        source = lspec["source"]
        if source == "recent_blogs":
            items = [b for b in cms.blogs_newest() if b.slug != item.slug]
        elif source == "author_posts":
            items = cms.posts_by_author(item.slug)
        elif source == "category_posts":
            items = cms.posts_by_category(item.slug)
        elif source == "siblings":
            items = [x for x in cms.published[spec["key"]] if x.slug != item.slug]
        else:
            continue
        if lspec.get("limit"):
            items = items[:lspec["limit"]]
        html = populate(html, lspec, items, binder)
    return html


def add_article_schema(html, spec, item, assets):
    """BlogPosting schema for blog posts; the export ships none."""
    if spec["key"] != "blog":
        return html
    author = item.get("_author")
    img = item.get_text("Main Image", "Blog Thumbnail")
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": item.name,
        "url": CFG.SITE_URL + item.url,
        "mainEntityOfPage": CFG.SITE_URL + item.url,
        "publisher": {"@type": "Organization", "name": "Bankers Vascular Centre",
                      "url": CFG.SITE_URL},
    }
    if img:
        data["image"] = CFG.SITE_URL + assets.url(img) if assets.url(img).startswith("/") \
            else assets.url(img)
    if item.get("_date"):
        data["datePublished"] = item["_date"].strftime("%Y-%m-%d")
    if author:
        data["author"] = {"@type": "Person", "name": author.name,
                          "url": CFG.SITE_URL + author.url}
    desc = re.sub(r"\s+", " ", item.get_text("Short Details"))[:300]
    if desc:
        data["description"] = desc
    tag = ('  <script type="application/ld+json">%s</script>\n</head>'
           % json.dumps(data, ensure_ascii=False))
    return html.replace("</head>", tag, 1)


def add_page_schema(html, url, spec=None, item=None):
    """Add the clinic entity, breadcrumbs, and doctor entity where relevant."""
    crumbs = [{"@type": "ListItem", "position": 1, "name": "Home",
               "item": CFG.SITE_URL + "/"}]
    path = url.strip("/")
    if path:
        current = ""
        for position, part in enumerate(path.split("/"), start=2):
            current += "/" + part
            crumbs.append({"@type": "ListItem", "position": position,
                           "name": part.replace("-", " ").title(),
                           "item": CFG.SITE_URL + current})
    graph = [{
        "@context": "https://schema.org",
        "@type": "MedicalClinic",
        "@id": CFG.SITE_URL + "/#medical-clinic",
        "name": "Bankers Vascular Centre",
        "url": CFG.SITE_URL + "/",
        "telephone": "+91-99099-03449",
        "medicalSpecialty": "Interventional Radiology",
        "address": [
            {"@type": "PostalAddress", "streetAddress": "2nd & 3rd Floor, RJP House, 100 Ft Anand Nagar Road, Opp. Scarlet Heights, Near Gopi Restaurant", "addressLocality": "Ahmedabad", "addressRegion": "Gujarat", "postalCode": "380015", "addressCountry": "IN"},
            {"@type": "PostalAddress", "streetAddress": "2nd Floor, Ignite, 201, Above Meera Clinic and Eye Hospital, Opp. Agrawal Cars, Laxmi Colony, Anand Nagar, Akota", "addressLocality": "Vadodara", "addressRegion": "Gujarat", "postalCode": "390007", "addressCountry": "IN"},
        ],
    }, {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": crumbs,
    }]
    if url == "/":
        graph.append({"@context": "https://schema.org", "@type": "WebSite",
                      "name": "Bankers Vascular Centre", "url": CFG.SITE_URL + "/"})
    city = url.rsplit("/", 1)[-1]
    location_data = CITY_LOCATION_DATA.get(city) if url.startswith(("/varicose-veins/", "/non-surgical-knee-pain/")) else None
    if location_data:
        query = urllib.parse.quote_plus("%s, %s" % (location_data["name"], location_data["address"]))
        graph.append({
            "@context": "https://schema.org", "@type": "Place",
            "name": location_data["name"],
            "address": {"@type": "PostalAddress", "streetAddress": location_data["address"], "addressLocality": location_data["city"], "addressRegion": "Rajasthan" if city == "rajasthan" else "Gujarat", "postalCode": location_data["postal_code"], "addressCountry": "IN"},
            "telephone": location_data["phone"],
            "hasMap": "https://www.google.com/maps/search/?api=1&query=" + query,
        })
    if spec and spec.get("key") == "our-doctors" and item:
        graph.append({"@context": "https://schema.org", "@type": "Physician",
                      "name": item.name, "url": CFG.SITE_URL + url,
                      "worksFor": {"@id": CFG.SITE_URL + "/#medical-clinic"},
                      "jobTitle": item.get_text("Doctor Designation")})
    tag = '  <script type="application/ld+json">%s</script>\n</head>' % json.dumps(
        {"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    return html.replace("</head>", tag, 1)


# ------------------------------------------------------------ static + sitemap

def prune_unused_cms_assets():
    """Ship only the CMS images that published pages actually reference.

    images/cms/ is the download cache and holds assets belonging to drafts,
    archived items and unused Webflow template leftovers too. Copying all of it
    would bloat the deployment with files nothing links to.
    """
    cms_dir = os.path.join(DIST, "images", "cms")
    if not os.path.isdir(cms_dir):
        return 0, 0
    used = set()
    for base, _dirs, files in os.walk(DIST):
        for f in files:
            if not f.endswith((".html", ".xml")):
                continue
            # Unescape first: hero backgrounds are written as
            # style="background-image:url(&quot;/images/cms/x.avif&quot;)", and
            # matching the raw text captured the trailing &quot; as part of the
            # filename - which made a referenced file look unused and deleted it.
            text = htmllib.unescape(read(os.path.join(base, f)))
            for m in re.finditer(r"/images/cms/([^\"'\s>)&]+)", text):
                used.add(urllib.parse.unquote(m.group(1)))
    removed = freed = 0
    for f in os.listdir(cms_dir):
        if f in used:
            continue
        p = os.path.join(cms_dir, f)
        freed += os.path.getsize(p)
        os.remove(p)
        removed += 1
    return removed, freed


def strip_missing_refs(missing):
    """Remove <img> tags pointing at assets that no longer exist anywhere.

    Two conference photos were lost in the export and are not on the live site
    either. A removed image is better than a broken-image icon in production.
    """
    if not missing:
        return 0
    targets = ["/" + m for m in missing]
    removed = 0
    for base, _dirs, files in os.walk(DIST):
        for f in files:
            if not f.endswith(".html"):
                continue
            path = os.path.join(base, f)
            html = read(path)
            if not any(t in html for t in targets):
                continue
            out, pos, hits = [], 0, 0
            for m in re.finditer(r"<img\s[^>]*>", html):
                src = W.get_attr(m.group(0), "src") or ""
                if urllib.parse.unquote(src) not in targets:
                    continue
                out.append(html[pos:m.start()])
                pos = m.end()
                hits += 1
            if hits:
                out.append(html[pos:])
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write("".join(out))
                removed += hits
    return removed


def home_page_assets(cms):
    """CDN URLs the home page renders: the doctor gallery, the testimonial
    backdrops and the four newest blog cards (plus their author avatars)."""
    urls = set()

    def add(*vals):
        for v in vals:
            v = (v or "").strip()
            if v.startswith("http"):
                urls.add(v)

    for d in cms.published.get("our-doctors", []):
        add(d.get("Doctor Thumbnail"), d.get("Doctor Details Image"))
    for t in cms.published.get("testimonials", []):
        add(t.get("BG Image"))
    for p in cms.blogs_newest()[:4]:
        add(p.get("Blog Thumbnail"), p.get("Main Image"))
        if p.get("_author"):
            add(p["_author"].get("Picture"))
    return urls


def copy_static(assets):
    for d in STATIC_DIRS:
        src = os.path.join(SRC, d)
        if os.path.isdir(src):
            # cms/ is the raw download cache and cms-opt/ holds the WebP copies
            # actually referenced by the pages. Ship the latter, as images/cms/.
            shutil.copytree(src, os.path.join(DIST, d), dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("cms", "cms-opt"))
    opt = os.path.join(SRC, "images", "cms-opt")
    if os.path.isdir(opt):
        shutil.copytree(opt, os.path.join(DIST, "images", "cms"),
                        dirs_exist_ok=True)
    assets.static_report = assets.repair_static_images(DIST)
    # Nothing else is copied in. Vercel builds this project from the repo root
    # with outputDirectory "dist", so vercel.json, package.json and the
    # api/ functions are read from the root - copying them into dist/ would
    # only publish the function's source at /api/contact.js and serve the
    # config as a static file.


def write_sitemap(written):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = []
    for _rel, url, indexable in written:
        if not indexable:
            continue
        urls.append("  <url><loc>%s%s</loc><lastmod>%s</lastmod></url>"
                    % (CFG.SITE_URL, urllib.parse.quote(url, safe="/-_.~"), today))
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "\n".join(urls) + "\n</urlset>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-assets", action="store_true",
                    help="reuse already-downloaded CMS assets")
    args = ap.parse_args()

    global PAGE_URLS, PAGINATION_TEMPLATE
    os.chdir(ROOT)

    import assets as assets_mod
    assets = assets_mod.AssetMap(skip_download=args.skip_assets)

    # Load the CMS before prefetching so the home page's images can be
    # optimised first - it is the page most people see, and an interrupted run
    # then still leaves the landing page complete.
    cms = cmsdata.Collections(CFG.COLLECTIONS, CFG.SITE_URL)
    assets.home_urls = home_page_assets(cms)
    assets.prefetch()

    print(cms.report())
    print()

    pages = shell_pages()
    PAGE_URLS = {f: page_url(f) for f in pages}
    PAGE_URLS.update({"index.html": "/"})
    PAGINATION_TEMPLATE = load_pagination_template()

    binder = Binder(assets)

    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    written = []
    written += build_shells(pages, cms, binder, assets)
    written += build_details(cms, binder, assets)

    copy_static(assets)
    write_sitemap(written)
    write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n"
          % CFG.SITE_URL)

    gone = strip_missing_refs(assets.static_report.get("still_missing", []))
    if gone:
        print("stripped %d <img> ref(s) to assets that no longer exist" % gone)

    removed, freed = prune_unused_cms_assets()
    if removed:
        print("pruned %d unreferenced CMS images from dist (%.0f MB)"
              % (removed, freed / 1e6))
    print("dist size: %.0f MB" % (dir_size(DIST) / 1e6))
    print("pages written: %d" % len(written))
    if warnings:
        print("\n%d warning(s):" % len(warnings))
        for w in sorted(set(warnings)):
            print("  !", w)
    assets.write_report(os.path.join(ROOT, "tools", "asset-report.txt"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
