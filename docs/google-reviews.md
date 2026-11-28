# Google Reviews sync

The homepage Google Reviews spotlight is backed by the Google Business Profile
APIs. It does not scrape Google Search or Google Maps, and it does not post
reviews or replies.

## What is implemented

- `worker.js` exposes read-only `GET /api/google-reviews`. It reads the
  `google-reviews-feed-v1` value from the production `GOOGLE_REVIEWS_CACHE` KV
  binding; the Worker has no Google Reviews cron handler.
- `scripts/sync-google-reviews.mjs` reuses the server-side location and review
  reconciliation code, then writes the complete JSON feed to the production
  KV namespace with Wrangler. It never writes a partial feed.
- `.github/workflows/sync-google-reviews.yml` runs at `*/30 * * * *` UTC and
  supports `workflow_dispatch` for the first sync or a manual reconciliation.
- `api/google-reviews.js` discovers locations from the authorized account, then
  accepts only the two locations whose returned address matches the configured
  Ahmedabad/Satellite and Vadodara/Akota address rules. Google location IDs are
  never hard-coded.
- Each complete reconciliation lists both branches, keeps source-confirmed
  five-star reviews only, deduplicates by location ID + review ID, applies
  edits, sorts newest first, and replaces the cache only after both branches
  succeed. A partial or failed run leaves the previous cache untouched.
- The existing client keeps the official full-color Google wordmark, five
  desktop cards, mobile swipe, autoplay, five-star rendering, branch
  attribution, review ages, and “View on Google” links. It loads the cached
  feed without a site build or publish.
- Until the API/KV feed is configured, the client temporarily falls back to
  the review text supplied in the implementation handoff so the carousel is
  not blank. This preview has no fabricated review dates or branch attribution;
  only the two supplied five-star ratings show stars. A valid API feed takes
  priority automatically.
- Cache entries expire after 30 days. The GitHub Action reconciles every 30
  minutes, so new reviews, edits, rating changes, and deletions update the
  homepage without a Webflow publish or Git push.

## Google policy choice

The implementation uses the authorized Google Business Profile APIs because
the review list endpoint provides review IDs, star ratings, timestamps, author
attribution, and review text for verified locations. The API requires the
`business.manage` OAuth scope and the account must have access to both
locations.

Google's current policies require authorization, secure handling, provided
Google branding/attribution, and limited storage of Business Profile content.
The cache therefore has a 30-day expiration, retains only the fields needed by
the component, preserves the review author/branch attribution, and does not
aggregate or rewrite review text. See the official [review data documentation](https://developers.google.com/my-business/content/review-data),
[review list reference](https://developers.google.com/my-business/reference/rest/v4/accounts.locations.reviews/list),
and [Business Profile API policies](https://developers.google.com/my-business/content/policies).

No paid third-party review dependency is enabled. Google API access and
Cloudflare Worker/KV usage remain subject to the accounts' own quotas and
plans; no new vendor subscription was added.

The supplied `https://share.google/g7R9DdUawjDISQNm4` link was checked as a
read-only link and resolves to a generic Google Search shell rather than a
clean, branch-verifiable Maps identity. It is not used as an API endpoint or
as proof of either branch. The server derives each branch's visitor link from
the authorized location metadata instead.

## Required Google OAuth setup

Use a Google Cloud project owned by the business or its authorized operator:

1. In **Google Cloud Console → APIs & Services → Library**, enable the
   Account Management API, Business Profile Information API, and the Business
   Profile Reviews API used by the project.
2. In **OAuth consent screen**, configure the app and add the scope
   `https://www.googleapis.com/auth/business.manage`.
3. If the consent screen is External and still in Testing, add the same Google
   manager email as a test user. That email must be a verified Owner or Manager
   of both the Ahmedabad Satellite and Vadodara Akota profiles.
4. Create an OAuth client and complete a one-time authorization-code flow with
   offline access (`access_type=offline`, with consent when a refresh token is
   needed). Keep the refresh token private; do not paste it into chat, commit
   it, or print it in an Action log.

The normal single-account GitHub Secrets are:

```text
GOOGLE_BUSINESS_PROFILE_CLIENT_ID
GOOGLE_BUSINESS_PROFILE_CLIENT_SECRET
GOOGLE_BUSINESS_PROFILE_REFRESH_TOKEN
```

The workflow also supports separate authorizations if the same email cannot
see both branches:

```text
GOOGLE_BUSINESS_PROFILE_AHMEDABAD_CLIENT_ID
GOOGLE_BUSINESS_PROFILE_AHMEDABAD_CLIENT_SECRET
GOOGLE_BUSINESS_PROFILE_AHMEDABAD_REFRESH_TOKEN
GOOGLE_BUSINESS_PROFILE_VADODARA_CLIENT_ID
GOOGLE_BUSINESS_PROFILE_VADODARA_CLIENT_SECRET
GOOGLE_BUSINESS_PROFILE_VADODARA_REFRESH_TOKEN
```

Short-lived access-token variants are supported for controlled staging only:
`GOOGLE_BUSINESS_PROFILE_ACCESS_TOKEN`,
`GOOGLE_BUSINESS_PROFILE_AHMEDABAD_ACCESS_TOKEN`, and
`GOOGLE_BUSINESS_PROFILE_VADODARA_ACCESS_TOKEN`.

## Required GitHub and Cloudflare setup

Add these GitHub repository Secrets under **Settings → Secrets and variables →
Actions**:

```text
GOOGLE_BUSINESS_PROFILE_CLIENT_ID
GOOGLE_BUSINESS_PROFILE_CLIENT_SECRET
GOOGLE_BUSINESS_PROFILE_REFRESH_TOKEN
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_KV_NAMESPACE_ID
```

`CLOUDFLARE_API_TOKEN` needs the account's **Workers KV Storage Edit** access.
`CLOUDFLARE_KV_NAMESPACE_ID` must be the production namespace that is bound to
the Worker as `GOOGLE_REVIEWS_CACHE`. The Action uses Wrangler with
`--remote`, `--path`, and a 30-day expiration; it does not expose review text
or credentials in the log.

The Worker binding must also exist in the approved Cloudflare configuration.
Once the real IDs are known, the deployment config should contain:

```jsonc
{
  "kv_namespaces": [
    {
      "binding": "GOOGLE_REVIEWS_CACHE",
      "id": "<production KV namespace id>",
      "preview_id": "<preview KV namespace id>"
    }
  ]
}
```

The IDs are deliberately not fabricated in this checkout. Without the
production binding, the Worker endpoint remains HTTP 503 even if the Action
successfully writes a KV namespace.

## First sync and verification

After the Secrets and binding are configured:

1. Open **Actions → Sync Google Reviews → Run workflow**.
2. Check the run summary for both verified branch location IDs, addresses, Maps
   URLs, sync time, and eligible five-star review count. The summary never
   prints credentials or review text.
3. Confirm `https://bankersvascular.com/api/google-reviews` returns HTTP 200.
4. Confirm the homepage loads the cards from the cache without a new build or
   publish. The scheduled run repeats every 30 minutes thereafter.

For local validation, `node scripts/sync-google-reviews.mjs --dry-run` performs
the Google reconciliation and validates the feed without writing Cloudflare
KV. The fixture suite covers both branch address resolution, new reviews,
exclusion of a four-star review, deduplication, rating-only reviews, edits,
deletions, cached API reads, partial-failure preservation, and separate
authorizations:

```text
node --test tests/google-reviews.test.mjs
```

The fixtures are synthetic and do not call Google or publish anything. A true
staging verification still needs authorized test credentials, the two Google
location IDs discovered by the account, and preview KV credentials.
