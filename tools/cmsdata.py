"""Load the Webflow CSV exports, apply publish rules, resolve joins."""

import csv
import glob
import os
import re
import sys
from datetime import datetime

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CMS_DIR = "cms"

# Webflow's Draft flag means "not published". We honour it, with one explicit
# exception confirmed with the site owner: Dr. Mohal Banker is the lead doctor
# and is live today despite being flagged Draft in the export.
FORCE_PUBLISH = {
    "our-doctors": {"dr-mohal-banker"},
}

# Approved display order for every published doctor card, profile list, event
# roster, and navigation list. The exported CMS rows leave several Order
# values blank, so keep the same numeric source of ordering in one place.
DOCTOR_DISPLAY_ORDER = {
    "dr-mohal-banker": 1,
    "dr-rozil-gandhi": 2,
    "dr-chandresh-bharada": 3,
    "dr-dimple": 4,
    "dr-pratiksha-patoliya": 5,
    "dr-disha-soni": 6,
    "dr-tensi-trevedi": 7,
    "dr-payal-vadlani": 8,
    "dr-janvi": 9,
}


def _truthy(v):
    return (v or "").strip().lower() == "true"


class Item(dict):
    """A CSV row plus its resolved URL and collection."""

    @property
    def slug(self):
        return self["Slug"].strip()

    @property
    def name(self):
        return (self["Name"] or "").strip()

    @property
    def url(self):
        return self["_url"]

    def get_text(self, *fields):
        """First non-empty value among `fields`."""
        for f in fields:
            v = (self.get(f) or "").strip()
            if v:
                return v
        return ""


def _find_csv(label):
    hits = glob.glob(os.path.join(CMS_DIR, "*- %s -*.csv" % label))
    if not hits:
        raise SystemExit("no CSV found for collection %r in %s/" % (label, CMS_DIR))
    if len(hits) > 1:
        raise SystemExit("ambiguous CSVs for %r: %s" % (label, hits))
    return hits[0]


_DATE_RE = re.compile(r"^[A-Za-z]{3} ([A-Za-z]{3}) (\d{2}) (\d{4})")
_MONTHS = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def parse_wf_date(s):
    """Parse Webflow's 'Mon May 11 2026 00:00:00 GMT+0000 (...)' format."""
    m = _DATE_RE.match((s or "").strip())
    if not m:
        return None
    try:
        return datetime(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))
    except (KeyError, ValueError):
        return None


class Collections:
    def __init__(self, specs, site_url):
        self.site_url = site_url
        self.specs = {s["key"]: s for s in specs}
        self.all = {}        # key -> [Item] every row
        self.published = {}  # key -> [Item] publishable rows only
        self.by_slug = {}    # key -> {slug: Item}
        self.excluded = {}   # key -> [(slug, reason)]
        self._load()
        self._resolve_joins()

    # ------------------------------------------------------------------ load
    def _load(self):
        for key, spec in self.specs.items():
            path = _find_csv(spec["csv"])
            with open(path, encoding="utf-8-sig", newline="") as fh:
                rows = [Item(r) for r in csv.DictReader(fh)]
            forced = FORCE_PUBLISH.get(key, set())
            keep, dropped = [], []
            seen = {}
            for r in rows:
                slug = r.slug
                if not slug:
                    dropped.append((r.name or "(unnamed)", "empty slug"))
                    continue
                if key == "our-doctors" and slug in DOCTOR_DISPLAY_ORDER:
                    r["Order"] = str(DOCTOR_DISPLAY_ORDER[slug])
                if slug.lower() in seen:
                    dropped.append((slug, "duplicate slug"))
                    continue
                seen[slug.lower()] = r
                r["_collection"] = key
                r["_url"] = self.item_url(key, slug)
                r["_date"] = parse_wf_date(r.get("time") or r.get("Created On"))
                if _truthy(r.get("Archived")):
                    dropped.append((slug, "archived"))
                    continue
                if _truthy(r.get("Draft")) and slug not in forced:
                    dropped.append((slug, "draft"))
                    continue
                if spec.get("require_active") and not _truthy(r.get("Active")):
                    dropped.append((slug, "inactive"))
                    continue
                keep.append(r)
            self.all[key] = rows
            self.published[key] = keep
            self.by_slug[key] = {r.slug: r for r in keep}
            self.excluded[key] = dropped

    def item_url(self, key, slug):
        folder = self.specs[key].get("folder")
        if not folder:
            return None
        return "/%s/%s" % (folder, slug)

    # ----------------------------------------------------------------- joins
    def _resolve_joins(self):
        """Attach referenced items. Refs to unpublished items resolve to None so
        callers omit the block rather than render an empty one."""
        authors = self.by_slug.get("blog-author", {})
        cats = self.by_slug.get("blog-category", {})
        for post in self.all.get("blog", []):
            post["_author"] = authors.get((post.get("Author") or "").strip())
            post["_category"] = cats.get((post.get("Category") or "").strip())

    # ------------------------------------------------------------- accessors
    def posts_by_author(self, slug):
        return [p for p in self.published["blog"]
                if p.get("_author") is not None and p["_author"].slug == slug]

    def posts_by_category(self, slug):
        return [p for p in self.published["blog"]
                if p.get("_category") is not None and p["_category"].slug == slug]

    def blogs_newest(self):
        dated = sorted(
            self.published["blog"],
            key=lambda r: (r["_date"] is not None, r["_date"] or datetime.min),
            reverse=True,
        )
        return dated

    def sorted_by(self, key, field, numeric=True):
        """Order by a numeric sort field, blanks last, then by name."""
        def sort_key(r):
            raw = (r.get(field) or "").strip()
            if numeric:
                try:
                    return (0, float(raw), r.name.lower())
                except ValueError:
                    return (1, 0.0, r.name.lower())
            return (0 if raw else 1, raw, r.name.lower())
        return sorted(self.published[key], key=sort_key)

    def report(self):
        lines = []
        for key in self.specs:
            total = len(self.all[key])
            pub = len(self.published[key])
            lines.append("%-24s %3d/%3d published" % (key, pub, total))
            for slug, why in self.excluded[key]:
                lines.append("    - %-52s %s" % (slug, why))
        return "\n".join(lines)
