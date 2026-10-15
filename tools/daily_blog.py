"""Prepare the blog scheduled for today from Google Sheets and Drive.

The GitHub Actions job is deliberately the orchestrator: this module reads the
existing monthly schedule, exports the referenced Google Doc, resolves the
matching thumbnail, and reuses ``publish_blog.py`` for CMS generation. It does
not publish past or future rows, and it never marks a row published until the
live-site check in the workflow succeeds.

Required runtime secret:
    GOOGLE_SERVICE_ACCOUNT_JSON

Optional discovery settings are documented in ``automation/daily_blog_config.json``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
CMS = ROOT / "cms"
IMAGE_DIR = ROOT / "src" / "images" / "blog"
DEFAULT_CONFIG = ROOT / "automation" / "daily_blog_config.json"
LOCAL_ZONE = ZoneInfo("Asia/Kolkata")
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
SHEET_SCOPES = ("https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets.readonly")

sys.path.insert(0, str(TOOLS))
import publish_blog  # noqa: E402  (shared publisher guardrails)


class AutomationError(RuntimeError):
    """A configuration or source-data failure that should fail the workflow."""


def text(value: Any) -> str:
    return str(value or "").strip()


def normal_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", text(value).lower())


def slugify(value: str) -> str:
    return publish_blog.slugify(value)


def parse_date(value: Any) -> date | None:
    value = text(value)
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            pass
    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", value)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AutomationError(f"automation config not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AutomationError(f"invalid automation config: {exc}") from exc


def cell(row: dict[str, str], *names: str) -> str:
    wanted = {normal_header(name) for name in names}
    for key, value in row.items():
        if normal_header(key) in wanted:
            return text(value)
    return ""


def row_object(headers: list[str], values: list[Any], row_number: int, sheet_id: str, sheet_name: str) -> dict[str, str]:
    row = {headers[i]: text(values[i]) if i < len(values) else "" for i in range(len(headers))}
    row["_row_number"] = str(row_number)
    row["_sheet_id"] = sheet_id
    row["_sheet_name"] = sheet_name
    row["_source_key"] = f"{sheet_id}:{sheet_name}:{row_number}"
    return row


def sheet_item(row: dict[str, str]) -> dict[str, Any]:
    title = cell(row, "BLOG TITLE", "Blog Title", "Name")
    scheduled = parse_date(cell(row, "Blog date", "Date", "Published On"))
    return {
        "title": title,
        "slug": slugify(title) if title else "",
        "scheduled_date": scheduled.isoformat() if scheduled else "",
        "author_label": cell(row, "DR. NAME", "DR NAME", "Author"),
        "doc_id": cell(row, "Doc ID", "Document ID", "Google Doc ID"),
        "thumbnail_ref": cell(row, "thumbnail", "Thumbnail", "Blog Thumbnail"),
        "meta_title": cell(row, "Meta tile", "Meta title", "SEO Title"),
        "meta_description": cell(row, "meta discripation", "Meta description", "SEO Description"),
        "submit_status": cell(row, "sumbit /yes not", "submit /yes not", "Submit"),
        "content_status": cell(row, "Content Status", "Status"),
        "row_number": int(row["_row_number"]),
        "sheet_id": row["_sheet_id"],
        "sheet_name": row["_sheet_name"],
        "source_key": row["_source_key"],
    }


def required_service_clients():
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise AutomationError("Google API dependencies are not installed") from exc
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise AutomationError("missing required secret: GOOGLE_SERVICE_ACCOUNT_JSON")
    try:
        info = json.loads(raw)
        credentials = Credentials.from_service_account_info(info, scopes=SHEET_SCOPES)
    except (ValueError, json.JSONDecodeError) as exc:
        raise AutomationError(f"GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON: {exc}") from exc
    return (
        build("drive", "v3", credentials=credentials, cache_discovery=False),
        build("sheets", "v4", credentials=credentials, cache_discovery=False),
    )


class GoogleSource:
    def __init__(self, config: dict[str, Any]):
        self.drive, self.sheets = required_service_clients()
        self.config = config
        self._thumbnail_files: list[dict[str, Any]] | None = None

    def list_files(self, query: str, fields: str) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        token = None
        while True:
            result = self.drive.files().list(
                q=query,
                pageSize=1000,
                pageToken=token,
                orderBy="name",
                fields=f"nextPageToken,files({fields})",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            files.extend(result.get("files", []))
            token = result.get("nextPageToken")
            if not token:
                return files

    def schedule_file_ids(self) -> list[str]:
        configured = list(self.config.get("schedule_sheet_ids", []))
        configured.extend(filter(None, os.environ.get("GOOGLE_SHEET_IDS", "").split(",")))
        folder_env = self.config.get("schedule_folder_id_env", "GOOGLE_DRIVE_SCHEDULE_FOLDER_ID")
        folder_id = os.environ.get(folder_env, "").strip()
        if folder_id:
            files = self.list_files(
                f"'{folder_id}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.spreadsheet'",
                "id,name,mimeType",
            )
            configured.extend(item["id"] for item in files)
        if configured:
            return list(dict.fromkeys(configured))
        name_re = re.compile(self.config.get("schedule_name_regex", r"^(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[-_ ]20\d{2}$"), re.I)
        files = self.list_files(
            "trashed = false and mimeType = 'application/vnd.google-apps.spreadsheet'",
            "id,name,mimeType",
        )
        return [item["id"] for item in files if name_re.search(text(item.get("name")))]

    def sheet_tabs(self, spreadsheet_id: str) -> list[str]:
        response = self.sheets.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(title))",
        ).execute()
        return [item["properties"]["title"] for item in response.get("sheets", [])]

    def rows(self) -> Iterable[dict[str, str]]:
        ids = self.schedule_file_ids()
        if not ids:
            raise AutomationError("no monthly schedule spreadsheets were discovered")
        for spreadsheet_id in ids:
            for tab in self.sheet_tabs(spreadsheet_id):
                if not re.search(r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[-_ ]20\d{2}", tab, re.I):
                    continue
                values = self.sheets.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{tab.replace(chr(39), chr(39) * 2)}'!A1:Z999",
                    majorDimension="ROWS",
                ).execute().get("values", [])
                if not values:
                    continue
                headers = [text(value) for value in values[0]]
                if not any(normal_header(header) == "blogdate" for header in headers):
                    continue
                for row_number, values_row in enumerate(values[1:], 2):
                    yield row_object(headers, values_row, row_number, spreadsheet_id, tab)

    def export_docx(self, file_id: str, destination: Path) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{10,}", file_id):
            raise AutomationError(f"invalid Google Doc ID: {file_id!r}")
        try:
            content = self.drive.files().export(fileId=file_id, mimeType=DOCX_MIME).execute()
        except Exception as exc:
            raise AutomationError(f"could not export Google Doc {file_id}: {exc}") from exc
        if not isinstance(content, bytes) or not content.startswith(b"PK"):
            raise AutomationError(f"Google Doc export {file_id} was not a DOCX")
        destination.write_bytes(content)

    def thumbnail_files(self) -> list[dict[str, Any]]:
        if self._thumbnail_files is not None:
            return self._thumbnail_files
        folder_env = self.config.get("thumbnail_folder_id_env", "GOOGLE_DRIVE_THUMBNAIL_FOLDER_ID")
        folder_id = os.environ.get(folder_env, "").strip()
        self._thumbnail_files = []
        if folder_id:
            self._thumbnail_files = self.list_files(
                f"'{folder_id}' in parents and trashed = false",
                "id,name,mimeType,size",
            )
        return self._thumbnail_files

    def download_thumbnail(self, item: dict[str, Any], destination_dir: Path) -> Path:
        ref = item["thumbnail_ref"]
        slug = item["slug"]
        files = self.thumbnail_files()
        explicit_id = None
        if ref and ref.lower() not in {"pending", "no", "n/a", "na"}:
            match = re.search(r"[-\w]{20,}", ref)
            explicit_id = match.group(0) if match else None
            local_ref = Path(urllib.parse.urlparse(ref).path).name if urllib.parse.urlparse(ref).path else Path(ref).name
            if local_ref and local_ref != "." and Path(local_ref).suffix.lower() in IMAGE_EXTENSIONS:
                local_matches = [path for path in IMAGE_DIR.glob(local_ref) if path.is_file()]
                if len(local_matches) == 1:
                    return local_matches[0]
        candidates = []
        for file in files:
            name = text(file.get("name"))
            if Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            if explicit_id and file.get("id") == explicit_id:
                candidates = [file]
                break
            ref_name = Path(urllib.parse.urlparse(ref).path).name.lower() if ref else ""
            if ref_name and name.lower() == ref_name:
                candidates.append(file)
                continue
            stem = Path(name).stem.lower()
            if stem == slug.lower() or publish_blog.normalise(stem) == publish_blog.normalise(item["title"]):
                candidates.append(file)
        if ref and ref.lower() not in {"pending", "no", "n/a", "na"} and not candidates and not explicit_id:
            local_name = Path(ref).name.lower()
            candidates = [
                {"id": "local", "name": path.name, "local_path": path}
                for path in IMAGE_DIR.iterdir()
                if path.is_file() and path.name.lower() == local_name and path.suffix.lower() in IMAGE_EXTENSIONS
            ]
            if len(candidates) == 1:
                return candidates[0]["local_path"]
        if not ref or ref.lower() in {"pending", "no", "n/a", "na"}:
            local = list(IMAGE_DIR.glob(f"{slug}.*")) if slug else []
            local = [path for path in local if path.suffix.lower() in IMAGE_EXTENSIONS]
            if len(local) == 1:
                return local[0]
            if len(local) > 1:
                raise AutomationError(f"ambiguous repository thumbnails for {slug}: {[p.name for p in local]}")
        if len(candidates) != 1:
            reason = "missing" if not candidates else "ambiguous"
            raise AutomationError(f"{reason} thumbnail for {item['title']!r}; provide an exact Drive file reference or upload a slug-named image")
        source = candidates[0]
        destination = destination_dir / source["name"]
        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io
            request = self.drive.files().get_media(fileId=source["id"], supportsAllDrives=True)
            with destination.open("wb") as handle:
                downloader = MediaIoBaseDownload(handle, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
        except Exception as exc:
            raise AutomationError(f"could not download thumbnail {source['name']}: {exc}") from exc
        return destination


def live_status(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "bankers-daily-blog-publisher/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        return 0, str(exc)


def author_name(label: str, config: dict[str, Any]) -> str:
    aliases = {publish_blog.normalise(k): text(v) for k, v in config.get("author_aliases", {}).items()}
    wanted = publish_blog.normalise(label)
    if wanted in aliases:
        return aliases[wanted]
    try:
        _, resolved, _ = publish_blog.select_author(label)
        return resolved
    except ValueError:
        candidates = []
        for path in (publish_blog.AUTHORS, publish_blog.DOCTORS):
            _, rows = publish_blog.read_csv(path)
            for row in publish_blog.safe_published(rows):
                actual = text(row.get("Name"))
                normal = publish_blog.normalise(actual)
                if normal.startswith(wanted) or wanted.startswith(normal):
                    candidates.append(actual)
        candidates = sorted(set(candidates))
        if len(candidates) == 1:
            return candidates[0]
        raise AutomationError(f"author {label!r} does not map to one published author/doctor")


def existing_blogs() -> dict[str, dict[str, str]]:
    _, rows = publish_blog.read_csv(publish_blog.BLOGS)
    return {(text(row.get("Slug"))).lower(): row for row in rows if text(row.get("Slug"))}


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        values = {
            "prepared_count": sum(status["status"] == "Prepared" for status in report["results"]),
            "needs_retrigger": str(report.get("needs_retrigger", False)).lower(),
            "actionable": str(report.get("actionable", False)).lower(),
        }
        with open(output, "a", encoding="utf-8") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")


def run(target_date: date, config: dict[str, Any], report_path: Path, dry_run: bool) -> dict[str, Any]:
    source = GoogleSource(config)
    all_items = [sheet_item(row) for row in source.rows()]
    existing = existing_blogs()
    todays = [item for item in all_items if item["scheduled_date"] == target_date.isoformat() and item["title"]]
    report: dict[str, Any] = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "local_date": target_date.isoformat(),
        "timezone": "Asia/Kolkata",
        "dry_run": dry_run,
        "results": [],
        "missed_publication_dates": [],
        "future_scheduled": [],
        "needs_retrigger": False,
        "actionable": False,
    }
    for item in all_items:
        scheduled = parse_date(item["scheduled_date"])
        if scheduled and scheduled < target_date and item["slug"] and item["slug"] not in existing:
            report["missed_publication_dates"].append({
                "source_key": item["source_key"],
                "scheduled_date": scheduled.isoformat(),
                "title": item["title"],
                "slug": item["slug"],
                "reason": "not present in CMS source; not auto-published",
            })
        elif scheduled and scheduled > target_date and item["title"]:
            report["future_scheduled"].append({
                "source_key": item["source_key"],
                "scheduled_date": scheduled.isoformat(),
                "title": item["title"],
                "slug": item["slug"],
                "status": "Scheduled",
            })
    if not todays:
        report["message"] = "No blog is scheduled for today. Future and missed rows were not published."
        write_report(report_path, report)
        return report

    with tempfile.TemporaryDirectory(prefix="bankers-daily-blog-") as temp_dir:
        temp = Path(temp_dir)
        for item in todays:
            result = {
                "source_key": item["source_key"],
                "title": item["title"],
                "scheduled_date": item["scheduled_date"],
                "slug": item["slug"],
                "url": f"https://bankersvascular.com/blog/{item['slug']}",
                "status": "Failed",
            }
            report["results"].append(result)
            if not item["slug"]:
                result["reason"] = "title does not produce a valid slug"
                continue
            status_code, body = live_status(result["url"])
            if status_code == 200 and item["slug"] in body:
                result["status"] = "Already Published"
                result["actual_publication_check"] = "live URL returned HTTP 200"
                continue
            if item["slug"] in existing and status_code != 200:
                report["needs_retrigger"] = True
            if not item["doc_id"]:
                result["reason"] = "missing Doc ID in schedule row"
                continue
            if not item["author_label"]:
                result["reason"] = "missing author in schedule row"
                continue
            try:
                resolved_author = author_name(item["author_label"], config)
                docx = temp / f"{item['slug']}.docx"
                source.export_docx(item["doc_id"], docx)
                thumbnail = source.download_thumbnail(item, temp)
                command = [
                    sys.executable,
                    str(TOOLS / "publish_blog.py"),
                    str(docx),
                    str(thumbnail),
                    "--author",
                    resolved_author,
                    "--published-on",
                    target_date.isoformat(),
                ]
                if item["meta_title"]:
                    command.extend(["--meta-title", item["meta_title"]])
                if item["meta_description"]:
                    command.extend(["--meta-description", item["meta_description"]])
                if dry_run:
                    command.append("--dry-run")
                completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
                if completed.returncode:
                    raise AutomationError(completed.stderr.strip() or completed.stdout.strip() or "publisher failed")
                result.update({
                    "status": "Dry Run" if dry_run else "Prepared",
                    "author": resolved_author,
                    "thumbnail": thumbnail.name,
                    "publisher_output": completed.stdout.strip(),
                })
                if not dry_run:
                    report["actionable"] = True
            except Exception as exc:
                result["reason"] = str(exc)
    write_report(report_path, report)
    if any(result["status"] == "Failed" for result in report["results"]):
        raise AutomationError("one or more scheduled blogs failed validation; see the report artifact")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare today’s scheduled Bankers Vascular blog from Google Drive.")
    parser.add_argument("--date", help="local Asia/Kolkata date in YYYY-MM-DD; defaults to today")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=ROOT / "automation-report.json")
    parser.add_argument("--dry-run", action="store_true", help="validate and report without writing CMS files")
    args = parser.parse_args()
    target = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(LOCAL_ZONE).date()
    try:
        report = run(target, load_config(args.config), args.report, args.dry_run)
    except Exception as exc:
        if not args.report.exists():
            write_report(args.report, {"local_date": target.isoformat(), "results": [], "error": str(exc)})
        print(f"daily blog automation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
