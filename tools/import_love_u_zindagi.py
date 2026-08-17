#!/usr/bin/env python3
"""Import the supplied Love U Zindagi WordPress export into Bankers Notes.

Usage:
  python tools/import_love_u_zindagi.py path/to/wordpress-export.zip

The source export remains untouched.  Each published WordPress post becomes a
Bankers Notes-only Blog row, keeping its original prose and images.  The
operation is idempotent: existing slugs, including the manually published
Simhasth post, are never overwritten.
"""

import csv
import html
import re
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOGS = next((ROOT / "cms").glob("*- Blogs - *.csv"))
WP = "http://wordpress.org/export/1.2/"
CONTENT = "http://purl.org/rss/1.0/modules/content/"


def local_slug(value):
    value = urllib.parse.unquote(value or "")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:110]


def first_image(markup):
    match = re.search(r'<img\b[^>]*\bsrc=["\']([^"\']+)', markup or "", re.I)
    return html.unescape(match.group(1)) if match else ""


def clean_content(markup, attachments):
    # WordPress gallery/caption shortcodes have no meaning in the static
    # renderer. Their actual <img> and prose remain after the wrappers vanish.
    markup = re.sub(r"\[caption[^\]]*\]", "", markup or "", flags=re.I)
    markup = re.sub(r"\[/caption\]", "", markup, flags=re.I)
    def gallery(match):
        ids = re.search(r"\bids=[\"']?([^\"'\] ]+)", match.group(0), re.I)
        if not ids:
            return ""
        images = [attachments.get(image_id.strip()) for image_id in ids.group(1).split(",")]
        images = [image for image in images if image]
        return "".join('<figure class="blog-inline-image"><img src="%s" alt="Travel photograph"></figure>'
                       % html.escape(image, quote=True) for image in images)
    markup = re.sub(r"\[gallery[^\]]*\]", gallery, markup, flags=re.I)
    markup = re.sub(r"<script\b[^>]*>.*?</script>", "", markup, flags=re.I | re.S)
    return markup.strip()


def excerpt(markup):
    text = re.sub(r"<[^>]+>", " ", markup)
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text[:300]


def wf_date(raw):
    try:
        parsed = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        parsed = datetime.now(timezone.utc)
    return parsed.strftime("%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)")


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: import_love_u_zindagi.py export.zip [--archive-imported]")
    archive = Path(sys.argv[1])
    archive_imported = len(sys.argv) == 3 and sys.argv[2] == "--archive-imported"
    with zipfile.ZipFile(archive) as zf:
        xml_name = next(name for name in zf.namelist() if name.endswith(".xml"))
        root = ET.fromstring(zf.read(xml_name))

    with BLOGS.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        rows = list(reader)
    known = {row.get("Slug", "").lower() for row in rows}
    attachments = {
        item.findtext("{%s}post_id" % WP): item.findtext("{%s}attachment_url" % WP)
        for item in root.findall("./channel/item")
        if item.findtext("{%s}post_type" % WP) == "attachment"
    }
    if archive_imported:
        wordpress_slugs = {
            local_slug(item.findtext("{%s}post_name" % WP) or "")
            for item in root.findall("./channel/item")
            if (item.findtext("{%s}post_type" % WP) == "post" and
                item.findtext("{%s}status" % WP) == "publish")
        }
        archived = 0
        for row in rows:
            if (row.get("Slug") in wordpress_slugs and
                    "wordpress.com" in (row.get("Blog Thumbnail") or "")):
                row["Archived"] = "true"
                archived += 1
        with BLOGS.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print("Archived %d local WordPress-import pages." % archived)
        return
    imported = refreshed = 0
    for item in root.findall("./channel/item"):
        if (item.findtext("{%s}post_type" % WP) != "post" or
                item.findtext("{%s}status" % WP) != "publish"):
            continue
        source_name = item.findtext("title") or ""
        source_slug = item.findtext("{%s}post_name" % WP) or ""
        slug = local_slug(source_slug)
        if not slug:
            continue
        body = clean_content(item.findtext("{%s}encoded" % CONTENT) or "", attachments)
        image = first_image(body)
        date = wf_date(item.findtext("{%s}post_date" % WP) or "")
        row = {field: "" for field in fields}
        row.update({
            "Name": html.unescape(source_name).strip(), "Slug": slug,
            "Archived": "false", "Draft": "false", "Created On": date,
            "Updated On": date, "Published On": date, "Blog Thumbnail": image,
            "Main Image": image, "Short Details": excerpt(body), "Main Details": body,
            "Author": "dr-mohal", "time": date,
            "Meta Title": html.unescape(source_name).strip(),
            "Meta Description": excerpt(body), "Bankers Notes": "true",
        })
        existing = next((current for current in rows if current.get("Slug", "").lower() == slug), None)
        # Do not overwrite manually authored content such as Simhasth. Rows
        # with a WordPress thumbnail are exactly the rows created by this tool.
        if existing:
            if "wordpress.com" not in (existing.get("Blog Thumbnail") or ""):
                continue
            existing.update(row)
            refreshed += 1
        else:
            rows.append(row)
            known.add(slug)
            imported += 1

    with BLOGS.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print("Imported %d and refreshed %d Love U Zindagi posts." % (imported, refreshed))


if __name__ == "__main__":
    main()
