"""Verify production pages after a daily blog commit."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


BASE = "https://bankersvascular.com"


def fetch(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "bankers-daily-blog-live-check/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        return 0, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("live-report.json"))
    args = parser.parse_args()
    source = json.loads(args.report.read_text(encoding="utf-8"))
    checks = []
    for item in source.get("results", []):
        if item.get("status") not in {"Prepared", "Already Published"}:
            continue
        slug = item["slug"]
        url = f"{BASE}/blog/{slug}"
        status, body = fetch(url)
        checks.append({
            "title": item["title"],
            "url": url,
            "status": status,
            "has_slug": slug in body,
            "has_thumbnail": f"/images/blog/{slug}." in body,
        })
    for item in checks:
        slug = item["url"].rsplit("/", 1)[-1]
        item["listing_status"], listing = fetch(f"{BASE}/blog")
        item["linked_from_blog"] = f"/blog/{slug}" in listing
        item["sitemap_status"], sitemap = fetch(f"{BASE}/sitemap.xml")
        item["in_sitemap"] = f"{BASE}/blog/{slug}" in sitemap
        item["ok"] = all((item["status"] == 200, item["has_slug"], item["listing_status"] == 200,
                          item["linked_from_blog"], item["sitemap_status"] == 200, item["in_sitemap"]))
    result = {"base": BASE, "checks": checks, "ok": bool(checks) and all(item["ok"] for item in checks)}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
