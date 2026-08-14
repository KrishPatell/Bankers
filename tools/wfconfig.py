"""Declarative config: collections, page meta, and field -> CSS-class bindings.

Every binding here was confirmed by diffing the unbound export templates against
the corresponding live bankersvascular.com page, so the output matches what
Webflow itself renders.

Binding kinds
-------------
text      set escaped text as the element's inner HTML
richtext  inject the CMS HTML unescaped (already sanitised Webflow rich text)
img       set @src, drop @srcset, set @alt
bg        set style="background-image:url(&quot;...&quot;)"
link      set @href on every <a href="#"> in the item
"""

# Canonical host: the live site canonicalises to the bare domain, not www.
SITE_URL = "https://bankersvascular.com"

BRAND_TITLE = "| Bankers Vascular Centre"


# --------------------------------------------------------------- collections

COLLECTIONS = [
    {
        "key": "blog",
        "csv": "Blogs",
        "folder": "blog",
        "template": "detail_blog.html",
        "title": ["Name"],
        "desc": ["Short Details"],
        "og_image": ["Main Image", "Blog Thumbnail"],
        "bind": [
            {"cls": "breadcrumb-heading-3", "field": "Name", "kind": "text"},
            {"cls": "blog-detail-hero-thumbnail", "field": ["Blog Thumbnail", "Main Image"],
             "kind": "img", "alt": "Name", "on_empty": "remove"},
            {"cls": "text-102", "field": "Short Details", "kind": "text",
             "on_empty": "remove"},
            {"cls": "blog-details", "field": "Main Details", "kind": "richtext"},
            # 'blog-meta-text' sits in the Date meta block, not the author one.
            {"cls": "blog-meta-text", "field": "@date", "kind": "text"},
        ],
        # Author photo and name link. The whole `blog-meta-author-block` is
        # dropped when the post has no author or the author is unpublished,
        # rather than rendering an empty avatar and a link to nowhere.
        "author_block": {
            "container": "blog-meta-author-block",
            "image": "blog-meta-author-image",
            "link": "blog-meta-link",
        },
    },
    {
        "key": "blog-author",
        "csv": "Blog Authors",
        "folder": "blog-author",
        "template": "detail_blog-author.html",
        "title": ["Name"],
        "desc": ["Bio"],
        "og_image": ["Picture"],
        "bind": [
            # 'breadcrumb-heading-3' is the static "Blog Author" label on the
            # live site too; the name goes in the breadcrumb trail.
            {"cls": "text-102", "field": "Name", "kind": "text"},
            {"cls": "author-image", "field": "Picture", "kind": "img",
             "alt": "Name"},
            {"cls": "author-bio", "field": "Bio", "kind": "text"},
        ],
        # Four `social-link-block` anchors in document order. Each is removed
        # when its field is empty or is a bare domain with no profile path.
        "socials": {
            "cls": "social-link-block",
            "fields": ["Facebook Profile Link", "Twitter Profile Link",
                       "Linkedin", "Instagram"],
        },
    },
    {
        "key": "blog-category",
        "csv": "Blog Categories",
        "folder": "blog-category",
        "template": "detail_blog-categories.html",
        "title": ["Name"],
        "desc": ["Name"],
        "og_image": [],
        "bind": [
            {"cls": "breadcrumb-heading-3", "field": "Name", "kind": "text"},
        ],
    },
    {
        "key": "departments",
        "csv": "Departments",
        "folder": "departments",
        "template": "detail_departments.html",
        "title": ["Meta Title", "Name"],
        "desc": ["Meta Description", "Department Short Details"],
        "og_image": ["background"],
        "bind": [
            {"cls": "breadcrumb-heading-3--white", "field": "Name", "kind": "text"},
            {"cls": "department-main-details", "field": "Department Details",
             "kind": "richtext"},
            {"cls": "new-combo", "field": "background", "kind": "bg"},
        ],
    },
    {
        "key": "treatment",
        "csv": "Treatments",
        "folder": "treatment",
        "template": "detail_treatment.html",
        "title": ["Name"],          # live: "Hemorrhoids | Bankers Vascular ..."
        "desc": ["Meta Description", "Department Short Details"],
        "og_image": ["background"],
        "bind": [
            {"cls": "breadcrumb-heading-3--white", "field": "Name", "kind": "text"},
            # This template's rich-text class is suffixed '-2' and its hero is
            # 'about-hero-section', unlike the other department-shaped templates.
            {"cls": "department-main-details-2", "field": "Department Details",
             "kind": "richtext"},
            {"cls": "about-hero-section", "field": "background", "kind": "bg"},
        ],
    },
    {
        "key": "varicose-veins",
        "csv": "Varicose Veins",
        "folder": "varicose-veins",
        "template": "detail_varicose-veins.html",
        "title": ["Meta Title", "Name"],
        "desc": ["Meta Description", "Department Short Details"],
        "og_image": ["background"],
        "bind": [
            {"cls": "breadcrumb-heading-3--white", "field": "Name", "kind": "text"},
            {"cls": "text-101-white", "field": "Name", "kind": "text"},
            {"cls": "sidebar-form-heding", "field": "Name", "kind": "text"},
            {"cls": "department-main-details", "field": "Department Details",
             "kind": "richtext"},
            {"cls": "new-combo", "field": "background", "kind": "bg"},
        ],
    },
    {
        "key": "non-surgical-knee-pain",
        "csv": "Non-Surgical Knee Pains",
        "folder": "non-surgical-knee-pain",
        "template": "detail_non-surgical-knee-pain.html",
        "title": ["Meta Title", "Name"],
        "desc": ["Meta Description", "Department Short Details"],
        "og_image": ["background"],
        "bind": [
            {"cls": "breadcrumb-heading-3--white", "field": "Name", "kind": "text"},
            {"cls": "text-101-white", "field": "Name", "kind": "text"},
            {"cls": "sidebar-form-heding", "field": "Name", "kind": "text"},
            {"cls": "department-main-details", "field": "Department Details",
             "kind": "richtext"},
            {"cls": "new-combo", "field": "background", "kind": "bg"},
        ],
    },
    {
        "key": "our-doctors",
        "csv": "Our Doctors",
        "folder": "our-doctors",
        "template": "detail_our-doctors.html",
        "title": ["Name"],
        "desc": ["Doctor Designation"],
        "og_image": ["Doctor Details Image", "Doctor Thumbnail"],
        "bind": [
            {"cls": "doctor-bio-name", "field": "Name", "kind": "text"},
            {"cls": "doctor-bio-degree", "field": "Doctor Degrree",
             "kind": "text", "on_empty": "remove"},
            {"cls": "doctor-bio-designation", "field": "Doctor Designation",
             "kind": "text", "on_empty": "remove"},
            {"cls": "doctor-main-image",
             "field": ["Doctor Details Image", "Doctor Thumbnail"],
             "kind": "img", "alt": "Name"},
        ],
        # Four identically-classed rich-text blocks, filled in document order.
        # 'dcotor-bio' is a typo in the original Webflow class; the CSS depends
        # on it, so it stays.
        "repeated_richtext": {
            "cls": "dcotor-bio",
            "fields": ["Doctor Bio", "Speciality", "Work Experience",
                       "Awards & Recognition"],
        },
    },
    {
        "key": "products",
        "csv": "Products",
        "folder": None,          # list-only: detail_products.html is an empty stub
        "template": None,
        "require_active": True,
    },
    {
        "key": "testimonials",
        "csv": "Testimonials",
        "folder": None,          # list-only: no detail template exists
        "template": None,
    },
]


# ------------------------------------------------------------ item renderers
#
# One entry per distinct collection-item markup shape found in the export.
# `link` bindings rewrite every <a href="#"> inside the cloned item.

ITEM_BINDINGS = {
    "doctor-card": [
        {"cls": "doctor-thumbnail", "field": ["Doctor Thumbnail", "Doctor Details Image"],
         "kind": "img", "alt": "Name"},
        {"cls": "doctor-name", "field": ["Card Name", "Name"], "kind": "text"},
        {"cls": "doctor-designation", "field": ["Card Designation", "Doctor Designation"],
         "kind": "text", "on_empty": "remove"},
        {"kind": "link"},
    ],
    "department-card": [
        {"cls": "department-icon", "field": "Department Icon", "kind": "img",
         "alt": "Name", "on_empty": "remove:department-icon-wrapper"},
        {"cls": "department-name", "field": "Name", "kind": "text"},
        {"cls": "department-short-details", "field": "Department Short Details",
         "kind": "text"},
        {"kind": "link"},
    ],
    "blog-card": [
        {"cls": "blog-archive-thumbnail", "field": ["Blog Thumbnail", "Main Image"],
         "kind": "img", "alt": "Name"},
        {"cls": "blog-archive-name", "field": "Name", "kind": "text"},
        {"cls": "blog-short-details", "field": "Short Details", "kind": "text",
         "on_empty": "remove"},
        {"cls": "wbs-blog-author-image", "field": "@author.Card Picture", "kind": "img",
         "alt": "@author.Name", "on_empty": "remove:wbs-blog-author"},
        {"cls": "wbs-blog-author-name", "field": "@author.Name", "kind": "text"},
        {"kind": "link"},
    ],
    "blog-large": [
        {"cls": "blog-archive-thumbnail", "field": ["Blog Thumbnail", "Main Image"],
         "kind": "img", "alt": "Name"},
        {"cls": "blog-archive-name", "field": "Name", "kind": "text"},
        {"cls": "wbs-blog-author-image", "field": "@author.Card Picture", "kind": "img",
         "alt": "@author.Name", "on_empty": "remove:wbs-blog-author"},
        {"cls": "wbs-blog-author-name", "field": "@author.Name", "kind": "text"},
        {"kind": "link"},
    ],
    "blog-small": [
        {"cls": "blog-small-item-image", "field": ["Blog Thumbnail", "Main Image"],
         "kind": "img", "alt": "Name"},
        {"cls": "blog-small-item-name", "field": "Name", "kind": "text"},
        {"cls": "wbs-blog-author-image", "field": "@author.Card Picture", "kind": "img",
         "alt": "@author.Name", "on_empty": "remove:wbs-blog-author"},
        {"cls": "wbs-blog-author-name", "field": "@author.Name", "kind": "text"},
        {"kind": "link"},
    ],
    # The four Testimonials rows still carry Webflow's stock item names
    # ("Brown Building", "City at Night", ...) in the Name field while the review
    # bodies are genuine patient quotes. Rendering Name would put "Brown Building"
    # as a heading above a real testimonial, so the Subtext label is used instead.
    # Flagged in the build report for real names to be supplied.
    "testimonial-card": [
        {"cls": "column-item", "field": "BG Image", "kind": "bg"},
        {"cls": "heading", "field": "Subtext", "kind": "text"},
        {"cls": "paragraph-2", "field": "Short Description", "kind": "text"},
        {"kind": "link", "field": "YT"},
    ],
    "product-card": [
        # Only 2 of 19 products have an image; the rest would fall back to
        # Webflow's grey placeholder SVG on its CDN, so drop the <img> instead.
        {"cls": "image-449", "field": "Image", "kind": "img", "alt": "Name",
         "on_empty": "remove"},
        {"cls": "heading-13", "field": "Name", "kind": "text"},
        {"cls": "paragraph-13", "field": "Subtitle", "kind": "text"},
        {"kind": "price", "field": "Price (INR)"},
    ],
    "nav-link": [
        {"kind": "self_text_link"},
    ],
    "featured-link": [
        {"cls": "feature-image", "field": "Department Icon", "kind": "img",
         "alt": "Name", "on_empty": "remove"},
        {"cls": "title-small", "field": "Name", "kind": "text"},
        {"kind": "link"},
    ],
}


# ------------------------------------------------------------------ nav lists
#
# The three CMS-driven nav dropdowns, present on every page. Mapping and item
# counts confirmed against the live site nav (9 doctors / 12 departments /
# 9 treatments).

NAV_LISTS = [
    {"item_cls": "nav-dropdown-link-copy", "collection": "our-doctors",
     "order": ("Order", "numeric"), "bindings": "nav-link"},
    {"items_cls": "department-nav-list", "collection": "departments",
     "order": ("Sorting", "numeric"), "bindings": "nav-link"},
    {"item_cls": "dropdown-2", "collection": "treatment",
     "order": ("Sorting", "numeric"), "bindings": "nav-link"},
]


# ---------------------------------------------------------------- page lists
#
# Page-specific collection lists, keyed by the page they appear on. `items_cls`
# identifies the <div role="list"> inside the w-dyn-list.

# Card-only doctor portraits. These transparent 900 x 1100 uploads apply to
# every reusable doctor-card list, without changing the larger profile images
# used on individual doctor detail pages.
DOCTOR_CARD_IMAGE_OVERRIDES = {
    "dr-mohal-banker": {"Doctor Thumbnail": "/images/doctor-card-mohal-banker.png"},
    "dr-rozil-gandhi": {"Doctor Thumbnail": "/images/doctor-card-rozil-gandhi.png"},
    "dr-payal-vadlani": {"Doctor Thumbnail": "/images/doctor-card-payal-vadlani.png"},
    "dr-dimple": {"Doctor Thumbnail": "/images/doctor-card-dimple-parmar.png"},
    "dr-disha-soni": {"Doctor Thumbnail": "/images/doctor-card-disha-soni.png"},
    "dr-janvi": {"Doctor Thumbnail": "/images/doctor-card-janvi.png"},
    "dr-tensi-trevedi": {"Doctor Thumbnail": "/images/doctor-card-tensi-trivedi.png"},
    "dr-pratiksha-patoliya": {"Doctor Thumbnail": "/images/doctor-card-pratiksha-patoliya.png"},
    "dr-chandresh-bharada": {"Doctor Thumbnail": "/images/doctor-card-chandresh-bharada.png"},
}

PAGE_LISTS = {
    "index.html": [
        {"items_cls": "doctor-archive-list", "collection": "our-doctors",
         "order": ("Order", "numeric"), "bindings": "doctor-card",
         "field_overrides": DOCTOR_CARD_IMAGE_OVERRIDES},
        {"items_cls": "fancy-columns", "collection": "testimonials",
         "order": ("Sort Order", "numeric"), "bindings": "testimonial-card"},
        {"items_cls": "blog-list-left", "collection": "blog",
         "order": "newest", "limit": 1, "bindings": "blog-large"},
        {"items_cls": "blog-list-right", "collection": "blog",
         "order": "newest", "limit": 3, "offset": 1, "bindings": "blog-small"},
    ],
    "blog.html": [
        {"items_cls": "blog-archive", "collection": "blog",
         "order": "newest", "paginate": 100, "bindings": "blog-card"},
    ],
    "departments.html": [
        {"items_cls": "department-archive-list", "collection": "departments",
         "order": ("Sorting", "numeric"), "bindings": "department-card"},
    ],
    "products.html": [
        {"items_cls": "products-grid", "collection": "products",
         "order": ("Name", "text"), "bindings": "product-card"},
    ],
    "contact-us.html": [
        {"items_cls": "doctor-archive-list", "collection": "our-doctors",
         "order": ("Order", "numeric"), "bindings": "doctor-card",
         "field_overrides": DOCTOR_CARD_IMAGE_OVERRIDES},
    ],
    "bng-conference-november-2024.html": [
        {"items_cls": "doctor-archive-list", "collection": "our-doctors",
         "order": ("Order", "numeric"), "bindings": "doctor-card",
         "field_overrides": DOCTOR_CARD_IMAGE_OVERRIDES},
    ],
    "bng-con-2025.html": [
        {"items_cls": "bng-conf", "collection": "our-doctors",
         "order": ("Order", "numeric"), "bindings": "doctor-card",
         "field_overrides": DOCTOR_CARD_IMAGE_OVERRIDES},
    ],
}

# Bankers Notes reuses the blog archive but is intentionally limited to the
# lead doctor's authored articles.
EXTRA_SHELL_PAGES = {
    "bankers-notes.html": {
        "source": "blog.html",
        "output": "bankers-notes/index.html",
        "url": "/bankers-notes",
    },
}

PAGE_LISTS["bankers-notes.html"] = [
    {"items_cls": "blog-archive", "collection": "blog", "order": "newest",
     "author_slug": "dr-mohal", "paginate": 100, "bindings": "blog-card"},
]

# Lists inside detail templates, resolved per rendered item.
DETAIL_LISTS = {
    "detail_blog.html": [
        {"items_cls": "blog-archive", "source": "recent_blogs", "limit": 3,
         "bindings": "blog-card"},
    ],
    "detail_blog-author.html": [
        {"items_cls": "blog-author-archive", "source": "author_posts",
         "bindings": "blog-card",
         "empty_text": "No articles from this author yet."},
    ],
    "detail_blog-categories.html": [
        {"items_cls": "blog-archive", "source": "category_posts",
         "bindings": "blog-card",
         "empty_text": "No articles in this category yet."},
    ],
    # "Related Articles" sidebar: sibling treatments. Its static
    # `w-pagination-wrapper` (all href="#") is removed — dead controls.
    "detail_treatment.html": [
        {"container_cls": "featured-articles", "source": "siblings", "limit": 5,
         "bindings": "featured-link", "drop_pagination": True},
    ],
}


# ---------------------------------------------------------------- page setup

# Listings that must ship as <folder>/index.html because a CMS folder of the
# same name exists. Serving both blog.html and blog/<slug>.html under Vercel
# cleanUrls is ambiguous; directory form removes the ambiguity.
DIRECTORY_PAGES = {
    "blog.html": "blog/index.html",
    "departments.html": "departments/index.html",
    "products.html": "products/index.html",
}

# Never shipped: unbound CMS templates and Webflow pages that were never designed.
EXCLUDE_PAGES = {
    "detail_blog.html", "detail_blog-author.html", "detail_blog-categories.html",
    "detail_departments.html", "detail_treatment.html", "detail_varicose-veins.html",
    "detail_non-surgical-knee-pain.html", "detail_our-doctors.html",
    "detail_products.html", "detail_accordions.html", "detail_app-bankers-opd.html",
    "insurance-departments/untitled.html",
}

# Dead Webflow template lists with no CMS binding. Removed outright:
# `fancy-columns-wrap-copy` renders "Item Heading / Subtitle / eros dolor
# interdum nulla..." lorem ipsum, and `staff-collection` has an empty item
# template so it can only ever render "No items found.".
DEAD_LISTS = ["fancy-columns-wrap-copy", "staff-collection"]

# Pages excluded from sitemap.xml (utility pages).
NOINDEX_PAGES = {"401.html", "404.html"}
