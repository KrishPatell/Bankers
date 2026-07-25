"""Localise Webflow CDN assets and repair the export's broken image refs.

Two jobs:

1. CMS assets. Every image in the CSVs lives on cdn.prod.website-files.com.
   They are downloaded into images/cms/ so the site does not depend on Webflow's
   CDN once the site has moved off Webflow. Any download that fails keeps its
   original CDN URL - a working remote image beats a broken local one.

2. Export bugs. The export wrote some files with spaces in their names but
   referenced them with hyphens, and nine assets never downloaded at all
   (see MISSING.txt) - including favicon.png, which every page references.
"""

import hashlib
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "images")
CMS_CACHE = os.path.join(IMAGES, "cms")

CDN_HOSTS = (
    "cdn.prod.website-files.com",
    "uploads-ssl.webflow.com",
    "assets.website-files.com",
    "d3e54v103j8qbb.cloudfront.net",
)

_HOST_ALT = "|".join(re.escape(h) for h in CDN_HOSTS)

# Bare-URL match, for CSV columns whose entire value is one URL. Deliberately
# strict about terminators: many CMS filenames contain '(1)' and spaces encoded
# as %20, so a pattern that stopped at ')' truncated them, and one that allowed
# ',' swallowed the following CSV column.
CDN_RE = re.compile(r"https://(?:%s)/[^\s\"'<>,\\]+" % _HOST_ALT)

# URLs inside quoted HTML attributes in rich text. The quote is an unambiguous
# terminator, so parentheses in filenames survive.
ATTR_URL_RE = re.compile(
    r"""(?P<attr>\b(?:src|href|content)\s*=\s*)(?P<q>["'])"""
    r"""(?P<url>https://(?:%s)/[^"']+)(?P=q)""" % _HOST_ALT
)

# url(...) inside inline styles.
CSS_URL_RE = re.compile(
    r"""url\((?P<q>["']?)(?P<url>https://(?:%s)/[^"')]+)(?P=q)\)""" % _HOST_ALT
)

# Webflow's own editor placeholder is UI chrome, not site content.
PLACEHOLDER = "/plugins/Basic/assets/placeholder"

UA = {"User-Agent": "Mozilla/5.0 (compatible; bankersvascular-static-build)"}

LIVE = "https://www.bankersvascular.com"

_SHARED = "https://cdn.prod.website-files.com/6890521b31848ff8d5bc902a/"

# Assets listed in MISSING.txt that never downloaded during the Webflow export.
# The source URLs were recovered by reading the live pages that reference each
# one, so these are the real files rather than lookalikes. Where the original is
# no longer served anywhere, a visually equivalent asset already in images/ is
# substituted; `None` means neither is available and the reference is stripped.
#
#   local name -> (real CDN url or None, local substitute or None)
MISSING_ASSETS = {
    # Referenced by all 25 pages.
    "images/favicon.png": (_SHARED + "6890b58e31b7f97463a32306_c.png", "webclip.png"),
    # Footer/author social icons.
    "images/facebook.svg": (_SHARED + "6890521b31848ff8d5bc913d_facebook.svg",
                            "facebook-white.svg"),
    "images/instagram.svg": (_SHARED + "6890521b31848ff8d5bc9117_instagram.svg",
                             "instagram-white.svg"),
    "images/twitter.svg": (_SHARED + "6890521b31848ff8d5bc913b_twitter.svg",
                           "twitter-white.svg"),
    # "Our values" icons on the About page.
    "images/engagement.svg": (_SHARED + "6890521b31848ff8d5bc9119_engagement.svg", None),
    "images/improvement.svg": (_SHARED + "6890521b31848ff8d5bc913c_improvement.svg", None),
    "images/integrity.svg": (_SHARED + "6890521b31848ff8d5bc9118_integrity.svg", None),
    # Brochure image linked from every doctor page.
    "documents/bankers_vasuclar.jpg.avif":
        (_SHARED + "6890521b31848ff8d5bc9281_bankers_vasuclar.jpg.avif", None),
    # Decorative CSS-only backgrounds; originals are no longer served anywhere.
    "images/department-details-highlighter.svg": (None, "highlighter-shape-4.svg"),
    "images/like.svg": (None, None),
    # Conference photos; the live page no longer carries them.
    "images/Screenshot-2024-10-23-at-8.40.55-AM_1Screenshot-2024-10-23-at-8.40.55-AM.avif":
        (None, None),
    "images/Screenshot-2024-11-11-at-8.40.51-AM_1Screenshot-2024-11-11-at-8.40.51-AM.avif":
        (None, None),
}


def _ext_of(url):
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext and re.fullmatch(r"\.[a-z0-9]{2,5}", ext):
        return ext
    return ""


def local_name(url):
    """Stable, filesystem-safe name. Hash-prefixed because the CSV data has
    duplicate basenames and %2520 double-encoded names."""
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    base = urllib.parse.unquote(urllib.parse.unquote(
        os.path.basename(urllib.parse.urlparse(url).path)))
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-._") or "asset"
    stem, ext = os.path.splitext(base)
    ext = ext if re.fullmatch(r"\.[A-Za-z0-9]{2,5}", ext) else (_ext_of(url) or ".bin")
    return "%s_%s%s" % (digest, stem[:60], ext)


def fetch(url, dest, timeout=30, attempts=4):
    """Download `url` to `dest`, retrying on throttling and transient errors.

    The Webflow CDN answers 403 (not 429) when it decides a client is asking too
    fast, so a first pass without retries reported hundreds of phantom
    "Forbidden" failures for assets that fetch fine on their own.
    """
    import random
    import time

    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    raise urllib.error.HTTPError(
                        url, resp.status, "bad status", None, None)
                data = resp.read()
            if not data:
                raise ValueError("empty body")
            tmp = "%s.%d.part" % (dest, os.getpid())
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, dest)
            return len(data)
        except Exception as exc:
            last = exc
            retriable = (
                isinstance(exc, urllib.error.HTTPError)
                and exc.code in (403, 408, 425, 429, 500, 502, 503, 504)
            ) or not isinstance(exc, urllib.error.HTTPError)
            if not retriable or attempt == attempts - 1:
                break
            time.sleep(min(8.0, 0.7 * (2 ** attempt)) + random.random() * 0.4)
    raise last


class AssetMap:
    """Maps remote CDN URLs to local paths, downloading on first use."""

    def __init__(self, skip_download=False):
        self.skip_download = skip_download
        self.map = {}          # url -> "/images/cms/<name>" or original url
        self.failures = []     # (url, reason)
        self.downloaded = 0
        self.reused = 0
        os.makedirs(CMS_CACHE, exist_ok=True)

    # ------------------------------------------------------------------ public
    def url(self, raw):
        """Local path for a CMS asset URL (downloading if needed)."""
        raw = (raw or "").strip()
        if not raw:
            return ""
        if not raw.startswith("http"):
            return raw
        if raw in self.map:
            return self.map[raw]

        name = local_name(raw)
        dest = os.path.join(CMS_CACHE, name)
        rel = "/images/cms/" + name

        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            self.reused += 1
            self.map[raw] = rel
            return rel
        if self.skip_download:
            self.map[raw] = raw
            return raw
        try:
            fetch(raw, dest)
            self.downloaded += 1
            self.map[raw] = rel
        except Exception as exc:                      # keep the CDN URL working
            self.failures.append((raw, "%s: %s" % (type(exc).__name__, exc)))
            self.map[raw] = raw
        return self.map[raw]

    def rewrite(self, text):
        """Rewrite every CDN URL inside a blob of rich text.

        Works on quoted attribute values and url() rather than scanning for bare
        URLs, so filenames containing parentheses (`unnamed%20(1).png`) are not
        truncated.
        """
        if not text or "http" not in text:
            return text

        def attr(m):
            return "%s%s%s%s" % (m.group("attr"), m.group("q"),
                                 self.url(m.group("url")), m.group("q"))

        def css(m):
            return "url(%s%s%s)" % (m.group("q"), self.url(m.group("url")),
                                    m.group("q"))

        text = ATTR_URL_RE.sub(attr, text)
        return CSS_URL_RE.sub(css, text)

    @staticmethod
    def urls_in_csvs(cms_dir="cms"):
        """Every CDN asset URL the CSVs reference.

        Parses the CSVs with the csv module rather than scanning the raw file:
        a bare-URL regex over raw text ran past the closing quote and absorbed
        the next column (`...back-pain.svg,Foam`), which produced hundreds of
        phantom 403s on the first run.
        """
        import csv as _csv
        import glob

        urls = set()
        for path in glob.glob(os.path.join(cms_dir, "*.csv")):
            with open(path, encoding="utf-8-sig", newline="") as fh:
                for row in _csv.DictReader(fh):
                    for value in row.values():
                        if not value or "http" not in value:
                            continue
                        if "<" in value or "url(" in value:
                            # Rich text: only trust quoted attribute values.
                            for m in ATTR_URL_RE.finditer(value):
                                urls.add(m.group("url"))
                            for m in CSS_URL_RE.finditer(value):
                                urls.add(m.group("url"))
                        else:
                            # A plain column: the cell is the URL (Webflow also
                            # comma-separates multi-image fields).
                            for part in value.split(","):
                                part = part.strip()
                                if part.startswith("https://") and any(
                                        h in part for h in CDN_HOSTS):
                                    urls.add(part)
        return {u for u in urls if PLACEHOLDER not in u}

    def prefetch(self, cms_dir="cms", workers=12):
        """Download every CDN asset the CSVs reference, concurrently.

        Sequentially this is ~1500 round trips; a small thread pool turns
        several minutes into well under one. Failures are recorded and left
        pointing at the CDN, so a partial run still produces a working site.
        """
        from concurrent.futures import ThreadPoolExecutor

        urls = self.urls_in_csvs(cms_dir)

        todo = []
        for u in sorted(urls):
            dest = os.path.join(CMS_CACHE, local_name(u))
            if os.path.exists(dest) and os.path.getsize(dest) > 0:
                self.map[u] = "/images/cms/" + os.path.basename(dest)
                self.reused += 1
            else:
                todo.append((u, dest))

        print("CMS assets: %d referenced, %d cached, %d to download"
              % (len(urls), self.reused, len(todo)))
        if not todo or self.skip_download:
            return

        def one(job):
            u, dest = job
            try:
                fetch(u, dest)
                return u, "/images/cms/" + os.path.basename(dest), None
            except Exception as exc:
                return u, u, "%s: %s" % (type(exc).__name__, exc)

        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for u, mapped, err in pool.map(one, todo):
                self.map[u] = mapped
                if err:
                    self.failures.append((u, err))
                else:
                    self.downloaded += 1
                done += 1
                if done % 100 == 0 or done == len(todo):
                    print("  %d/%d downloaded (%d failed)"
                          % (done, len(todo), len(self.failures)))

    # ---------------------------------------------------------- export repairs
    def repair_static_images(self, dist_root):
        """Fix the two classes of broken local asset reference."""
        report = {"aliased": [], "recovered": [], "still_missing": []}
        dist_images = os.path.join(dist_root, "images")
        present = set(os.listdir(dist_images))

        # 1. Files the export wrote with spaces in their names but referenced
        #    with hyphens (10 hero/background images). Add the hyphenated
        #    spelling as a copy so the existing markup resolves.
        for fname in sorted(present):
            if " " not in fname:
                continue
            alias = fname.replace(" ", "-")
            if alias in present:
                continue
            shutil.copy2(os.path.join(dist_images, fname),
                         os.path.join(dist_images, alias))
            report["aliased"].append(alias)

        # 2. Assets that never downloaded during the export at all.
        for rel_path, (cdn_url, fallback) in MISSING_ASSETS.items():
            dest = os.path.join(dist_root, rel_path.replace("/", os.sep))
            if os.path.exists(dest):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if cdn_url:
                try:
                    fetch(cdn_url, dest, timeout=25)
                    report["recovered"].append(rel_path)
                    continue
                except Exception as exc:
                    self.failures.append((cdn_url, "recovering %s: %s"
                                          % (rel_path, exc)))
            if fallback:
                src = os.path.join(dist_images, fallback)
                if os.path.exists(src):
                    shutil.copy2(src, dest)
                    report["recovered"].append("%s (substituted %s)"
                                               % (rel_path, fallback))
                    continue
            report["still_missing"].append(rel_path)
        return report

    # ------------------------------------------------------------------ report
    def write_report(self, path):
        lines = [
            "CMS asset localisation",
            "=" * 60,
            "unique CDN URLs seen : %d" % len(self.map),
            "downloaded this run  : %d" % self.downloaded,
            "reused from cache    : %d" % self.reused,
            "failed (kept as CDN) : %d" % len(self.failures),
            "",
        ]
        if self.failures:
            lines.append("Failed downloads - these still point at the Webflow CDN")
            lines.append("and will break if that CDN is ever taken down:")
            for url, why in sorted(self.failures):
                lines.append("  %s\n      %s" % (url, why))
        if getattr(self, "static_report", None):
            r = self.static_report
            lines += ["", "Static image repairs", "-" * 60]
            lines.append("hyphen/space aliases added : %d" % len(r["aliased"]))
            lines.append("missing assets recovered   : %d" % len(r["recovered"]))
            for n in r["recovered"]:
                lines.append("    + %s" % n)
            if r["still_missing"]:
                lines.append("STILL MISSING - needs a real asset:")
                for n in r["still_missing"]:
                    lines.append("    ! %s" % n)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
