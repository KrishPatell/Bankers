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

# The approved transparent portraits are shared by doctor cards and the main
# image on each individual doctor profile. This deliberately leaves unrelated
# doctor CMS fields and historic source-image URLs intact.
DOCTOR_PROFILE_IMAGE_OVERRIDES = {
    "dr-mohal-banker": "/images/doctor-card-mohal-banker.png",
    "dr-rozil-gandhi": "/images/doctor-card-rozil-gandhi.png",
    "dr-chandresh-bharada": "/images/doctor-card-chandresh-bharada.png",
    "dr-dimple": "/images/doctor-card-dimple-parmar.png",
    "dr-pratiksha-patoliya": "/images/doctor-card-pratiksha-patoliya.png",
    "dr-disha-soni": "/images/doctor-card-disha-soni.png",
    "dr-tensi-trevedi": "/images/doctor-card-tensi-trivedi.png",
    "dr-payal-vadlani": "/images/doctor-card-payal-vadlani.png",
    "dr-janvi": "/images/doctor-card-janvi.png",
}

# Blog-card author avatars use the same approved portrait as their matching
# doctor card.  The original author Picture remains available for the author
# detail page and for authors without a published doctor-card counterpart.
BLOG_AUTHOR_DOCTOR_IMAGE_OVERRIDES = {
    "dr-disha-soni": "dr-disha-soni",
    "dr-mohal": "dr-mohal-banker",
    "www-bankersvascular-com-blog-author-dr-dimple-parmar": "dr-dimple",
    "www-bankersvascular-com-our-doctors-dr-payal-vadlani": "dr-payal-vadlani",
    "dr-pratiksha-patoliya": "dr-pratiksha-patoliya",
    "dr-tensi-trivedi": "dr-tensi-trevedi",
}

# Card labels are intentionally separate from the profile designation, SEO
# description, and CMS biography. This lets team cards keep a consistent,
# concise two-line presentation without changing doctor profile content.
DOCTOR_CARD_DESIGNATION_OVERRIDES = {
    "dr-mohal-banker": "Interventional Radiologist\nM.B.B.S., D.M.R.D.\nDirector - BnG Vascular",
    "dr-rozil-gandhi": "Interventional Radiologist\nM.B.B.S., D.M.R.D.\nJoint Director - BnG Vascular",
    "dr-chandresh-bharada": "Interventional Radiologist\nBnG Vascular",
    "dr-dimple": "Operational Head & Head Consultant\nBnG Vascular",
    "dr-pratiksha-patoliya": "Consultant Doctor\nBnG Vascular",
    "dr-disha-soni": "Consultant Doctor\nBnG Vascular",
    "dr-tensi-trevedi": "Consultant Doctor\nBnG Vascular",
    "dr-payal-vadlani": "Consultant Doctor\nBnG Vascular",
    "dr-janvi": "Consultant Doctor\nBnG Vascular",
}

# Keep the longest doctor card name fully readable in its narrow card without
# changing the name used on the profile, navigation, or structured data.
DOCTOR_CARD_NAME_OVERRIDES = {
    "dr-chandresh-bharada": "Dr. Chandresh\nBharada",
}

# Content explicitly withdrawn by the site owner.  Keep the source CSV intact
# so its original record remains recoverable, while excluding it from every
# generated surface (detail page, lists, related content and sitemap).
WITHDRAWN_CONTENT = {
    "blog": {
        "varicose-veins-in-young-adults-why-they-happen-and-when-to-seek-care",
        "simhasth-kumbh-a-spiritual-journey",
    },
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
            withdrawn = WITHDRAWN_CONTENT.get(key, set())
            keep, dropped = [], []
            seen = {}
            for r in rows:
                slug = r.slug
                if not slug:
                    dropped.append((r.name or "(unnamed)", "empty slug"))
                    continue
                if key == "our-doctors" and slug in DOCTOR_DISPLAY_ORDER:
                    r["Order"] = str(DOCTOR_DISPLAY_ORDER[slug])
                if key == "our-doctors" and slug in DOCTOR_PROFILE_IMAGE_OVERRIDES:
                    r["Doctor Details Image"] = DOCTOR_PROFILE_IMAGE_OVERRIDES[slug]
                if key == "our-doctors" and slug in DOCTOR_CARD_DESIGNATION_OVERRIDES:
                    r["Card Designation"] = DOCTOR_CARD_DESIGNATION_OVERRIDES[slug]
                if key == "our-doctors" and slug in DOCTOR_CARD_NAME_OVERRIDES:
                    r["Card Name"] = DOCTOR_CARD_NAME_OVERRIDES[slug]
                if key == "blog-author":
                    doctor_slug = BLOG_AUTHOR_DOCTOR_IMAGE_OVERRIDES.get(slug)
                    r["Card Picture"] = DOCTOR_PROFILE_IMAGE_OVERRIDES.get(
                        doctor_slug, r.get("Picture") or "")
                if slug.lower() in seen:
                    dropped.append((slug, "duplicate slug"))
                    continue
                seen[slug.lower()] = r
                r["_collection"] = key
                r["_url"] = self.item_url(key, slug)
                r["_date"] = parse_wf_date(r.get("time") or r.get("Created On"))
                if slug in withdrawn:
                    dropped.append((slug, "withdrawn by site owner"))
                    continue
                if _truthy(r.get("Archived")):
                    dropped.append((slug, "archived"))
                    continue
                if _truthy(r.get("Draft")) and slug not in forced:
                    dropped.append((slug, "draft"))
                    continue
                # Scheduled blogs stay hidden until their calendar date.  This
                # keeps future monthly entries in the source CSV while
                # preventing early publication on listings, detail routes,
                # related cards, and the sitemap.
                if key == "blog" and r.get("_date") and r["_date"].date() > datetime.now().date():
                    dropped.append((slug, "scheduled for a future date"))
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
