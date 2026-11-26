# Google Reviews sync

The homepage Google Reviews spotlight is backed by the Google Business Profile
APIs. It does not scrape Google Search or Google Maps, and it does not post
reviews or replies.

## What is implemented

- `worker.js` exposes `GET /api/google-reviews` and runs `syncGoogleReviews`
  from the Worker scheduled handler.
- `api/google-reviews.js` discovers locations from the authorized account, then
  accepts only the two locations whose returned address matches the configured
  Ahmedabad/Satellite and Vadodara/Akota address rules. Google location IDs are
  never hard-coded.
- Each complete reconciliation lists both branches, keeps source-confirmed
  five-star reviews only, deduplicates by location ID + review ID, applies
  edits, sorts newest first, and replaces the cache only after both branches
  succeed. A partial or failed run leaves the previous cache untouched.
- The client loads the cached feed without a build or publish, shows the
  official full-color Google wordmark, five desktop cards, swipe on mobile,
  five stars, branch attribution, rating-only reviews without an invented
  quote, and a separate “View … on Google” link for each branch.
- Cache entries expire after 30 days. The intended reconciliation interval is
  30 minutes; the Worker cron trigger is configured in `wrangler.jsonc`, but
  deployment is not complete until the production KV namespace and Google
  credentials are approved and configured.

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

## Required staging/production configuration

Create or use a Google Cloud project with access approved for the Business
Profile APIs, enable Account Management, Business Information, and the
Reviews API, and authorize an owner/manager of both verified locations. Store
these as server-side Worker secrets/variables; never put them in `src/`:

```text
GOOGLE_BUSINESS_PROFILE_CLIENT_ID
GOOGLE_BUSINESS_PROFILE_CLIENT_SECRET
GOOGLE_BUSINESS_PROFILE_REFRESH_TOKEN
```

For a short-lived staging run, `GOOGLE_BUSINESS_PROFILE_ACCESS_TOKEN` may be
used instead of the refresh-token trio. The refresh-token route is the normal
long-lived configuration. The required OAuth scope is:

```text
https://www.googleapis.com/auth/business.manage
```

Create separate preview and production Cloudflare KV namespaces, then add the
binding to the approved deployment configuration. The 30-minute cron trigger
is already present in `wrangler.jsonc`:

```jsonc
{
  "triggers": { "crons": ["*/30 * * * *"] },
  "kv_namespaces": [
    {
      "binding": "GOOGLE_REVIEWS_CACHE",
      "id": "<production KV namespace id>",
      "preview_id": "<preview KV namespace id>"
    }
  ]
}
```

Those IDs are environment-specific and are deliberately not fabricated in
this checkout. Until the binding and credentials are supplied, the endpoint
returns a not-ready response and the homepage keeps the section hidden rather
than displaying stale hard-coded reviews.

Google's optional [notification setup](https://developers.google.com/my-business/content/notification-setup)
can reduce latency with Pub/Sub review notifications, but a periodic
reconciliation is still required to catch edits and deletions. The current
implementation uses the simpler 30-minute reconciliation and does not create
or change any live Pub/Sub or Business Profile settings.

## Staging test command

The fixture suite covers both branch address resolution, a new five-star
review, exclusion of a four-star review, location+review deduplication,
rating-only reviews, edits, deletions, cached API reads, and preservation of a
complete cache when one branch fails:

```text
node --test tests/google-reviews.test.mjs
```

The fixtures are synthetic and do not call Google or publish anything. A true
staging verification still needs an authorized test token, the two Google
location IDs discovered by the account, and preview KV credentials.
