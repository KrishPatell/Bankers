# Daily blog automation

The repository now contains a GitHub Actions publisher at
`.github/workflows/daily-blog-publish.yml`. It runs at **01:30 UTC**, which is
**07:00 Asia/Kolkata (IST)**, and can also be started manually with a dry-run.

GitHub Actions schedules are best-effort. They do not guarantee that a runner
starts at exactly 07:00:00 IST. This workflow uses the scheduled run as the
trigger and publishes only the row whose sheet date equals the current
Asia/Kolkata date. If an exact-to-the-second guarantee is required, an external
managed scheduler must call `workflow_dispatch` or a future deployment-independent
publisher; no scheduler can honestly be described as exact from this repository
alone.

## One-time GitHub configuration

Create a read-only Google service account and grant it Viewer access to the
monthly schedule spreadsheets, the linked Google Docs, and the thumbnail Drive
folder. Add these repository secrets:

| Secret | Purpose |
| --- | --- |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Complete service-account JSON document |
| `GOOGLE_DRIVE_SCHEDULE_FOLDER_ID` | Optional folder containing future monthly Sheets; enabling this activates discovery by tab/name convention |
| `GOOGLE_DRIVE_THUMBNAIL_FOLDER_ID` | Optional folder containing future thumbnail images |

The October sheet ID is kept in `automation/daily_blog_config.json` so the
existing schedule works before a folder is configured. Future tabs should use
the existing `JAN-2026`, `FEB-2026`, … naming convention. If a folder secret is
present, all matching monthly Sheets in that folder are discovered
automatically. The `thumbnail` cell may contain an exact Drive file ID or file
name; otherwise the image is matched to the blog slug. Missing or ambiguous
images fail safely and are not published.

The GitHub Actions job needs `contents: write` on the repository. Cloudflare
must remain connected to `origin/main` with its normal build command
(`python tools/build.py`). The job intentionally does not use Wrangler or a
Cloudflare API token. It pushes only validated CMS/image source changes and
then checks the non-www production URL, `/blog`, and `/sitemap.xml` before
considering the article published.

## Safety and idempotency

- Only today's date is eligible. Future rows are left alone, and missed past
  dates are reported in the run artifact rather than bulk-published.
- A live HTTP 200 page containing the expected slug is reported as
  `Already Published`.
- Existing CMS rows are updated by the stable slug rather than duplicated.
- The source row's `Doc ID`, date, title, author, metadata, and thumbnail are
  validated before the local publisher is called.
- Each run uploads a JSON source report and a production verification report
  for 90 days. A failure leaves a red GitHub Actions run and a step summary;
  enable GitHub repository/Actions notifications for email alerts.
- No row is reported as published unless the live URL, blog listing, and
  sitemap checks pass.

## Testing

Use **Actions → Daily blog publishing → Run workflow → dry_run=true** first.
This reads today's sheet row, exports the referenced document, validates the
author and thumbnail, and makes no repository or production change. The normal
scheduled run performs the full build and repository push, then verifies live
production. It is safe to rerun after a failure because the CMS publisher and
live checks are idempotent.

Automatic publishing is not active until the three required one-time
conditions are satisfied: the service-account secret is present, the account
can read the configured Sheets/Docs/assets, and Cloudflare is successfully
deploying `origin/main`. The workflow will fail visibly rather than claiming
success when any condition is missing.
