# YouTube feed sync

The `/youtube` page is a static shell. The Cloudflare Worker fetches the
channel's uploads playlist server-side, reads video details in batches of up to
50 IDs, normalizes the result, and stores the last successful snapshot in the
`YOUTUBE_CACHE` KV namespace. The browser only requests `/api/youtube-feed`.

The Worker runs the sync daily at `04:00 UTC` (`0 4 * * *`). A request only
performs a lazy first sync when KV is empty; an isolate-level in-flight promise
prevents concurrent first requests from starting duplicate syncs. Scheduled or
upstream failures retain the previous snapshot and mark it `stale: true`.

## Cloudflare setup

Create the namespace, replace the placeholder ID in `wrangler.jsonc`, and set
encrypted secrets for each environment:

```text
npx wrangler kv namespace create YOUTUBE_CACHE
npx wrangler secret put YOUTUBE_API_KEY
npx wrangler secret put YOUTUBE_CHANNEL_ID
```

For a separately named staging environment, create a second KV namespace and
set the secrets in that environment as well. Do not put real values in
`.dev.vars`, source files, or `wrangler.jsonc`; `.dev.vars.example` contains
placeholders only.

The sync uses `channels.list`, paginated `playlistItems.list`, and batched
`videos.list`; it never uses `search.list`. For `N` uploaded videos, a full
sync uses approximately `1 + ceil(N / 50) + ceil(N / 50)` quota units (one
channel lookup, playlist pages, and video-detail batches). A daily run keeps
the expected usage low for normal-sized channels.

The Data API does not expose the Shorts label. The code treats videos up to
180 seconds as Shorts candidates, reflecting YouTube's current three-minute
limit, and also honors a `#shorts` hint in the title or description. This is a
deliberate heuristic and should be spot-checked against the channel after the
first production sync.
