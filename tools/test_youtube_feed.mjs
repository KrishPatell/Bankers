import assert from "node:assert/strict";
import {
  buildNormalizedFeed,
  isShortVideo,
  parseIsoDuration,
  parseViewCount,
  syncAndMarkStale,
  youtubeFeed,
} from "../api/youtube.js";

const CHANNEL_ID = "UC-test-bankers";
const API_KEY = "test-key-do-not-use";

function makeKv(initial = null) {
  let value = initial ? JSON.stringify(initial) : null;
  return {
    async get() { return value; },
    async put(_key, next) { value = next; },
    async read() { return value ? JSON.parse(value) : null; },
  };
}

function response(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const videoItems = [
  {
    id: "video-a",
    snippet: {
      title: "Longer vascular explainer",
      description: "",
      publishedAt: "2026-09-01T00:00:00Z",
      thumbnails: { high: { url: "https://i.ytimg.com/vi/video-a/hqdefault.jpg" } },
    },
    statistics: { viewCount: "20" },
    contentDetails: { duration: "PT3M1S" },
  },
  {
    id: "video-b",
    snippet: {
      title: "Three minute #shorts tip",
      description: "",
      publishedAt: "2026-09-03T00:00:00Z",
      thumbnails: { high: { url: "https://i.ytimg.com/vi/video-b/hqdefault.jpg" } },
    },
    statistics: { viewCount: "5" },
    contentDetails: { duration: "PT3M" },
  },
  {
    id: "video-c",
    snippet: {
      title: "Quick knee pain answer",
      description: "",
      publishedAt: "2026-09-02T00:00:00Z",
      thumbnails: { high: { url: "https://i.ytimg.com/vi/video-c/hqdefault.jpg" } },
    },
    statistics: { viewCount: "100" },
    contentDetails: { duration: "PT10S" },
  },
];

assert.equal(parseIsoDuration("PT3M1S"), 181);
assert.equal(parseViewCount("not-a-number"), 0);
assert.equal(parseViewCount("1234"), 1234);
assert.equal(isShortVideo({ duration: "PT3M" }), true);
assert.equal(isShortVideo({ duration: "PT3M1S" }), false);
assert.equal(isShortVideo({ duration: "", title: "A #shorts upload" }), true);

const direct = buildNormalizedFeed({ id: CHANNEL_ID, title: "Test channel" }, videoItems);
assert.deepEqual(direct.latest.map((video) => video.id), ["video-b", "video-c", "video-a"]);
assert.deepEqual(direct.popular.map((video) => video.id), ["video-c", "video-a", "video-b"]);
assert.deepEqual(direct.shorts.map((video) => video.id), ["video-b", "video-c"]);
assert.equal(direct.latest[0].url, "https://www.youtube.com/shorts/video-b");
assert.equal(direct.channel.url, `https://www.youtube.com/channel/${CHANNEL_ID}`);

const originalFetch = globalThis.fetch;
let mode = "ok";
let fetchCount = 0;
globalThis.fetch = async (request) => {
  fetchCount += 1;
  const url = new URL(request);
  if (mode === "timeout") throw new DOMException("timeout", "AbortError");
  if (mode === "invalid") return response({ error: { errors: [{ reason: "keyInvalid" }] } }, 403);
  if (mode === "quota") return response({ error: { errors: [{ reason: "quotaExceeded" }] } }, 403);
  if (url.pathname.endsWith("/channels")) {
    return response({ items: [{ snippet: { title: "Test channel" }, contentDetails: { relatedPlaylists: { uploads: "uploads-test" } } }] });
  }
  if (url.pathname.endsWith("/playlistItems")) {
    if (mode === "empty") return response({ items: [] });
    return response({ items: videoItems.map((video) => ({ contentDetails: { videoId: video.id } })) });
  }
  if (url.pathname.endsWith("/videos")) return response({ items: videoItems });
  return response({});
};

try {
  const env = { YOUTUBE_API_KEY: API_KEY, YOUTUBE_CHANNEL_ID: CHANNEL_ID, YOUTUBE_CACHE: makeKv() };
  const [firstResponse, secondResponse] = await Promise.all([
    youtubeFeed(new Request("https://bankersvascular.com/api/youtube-feed"), env),
    youtubeFeed(new Request("https://bankersvascular.com/api/youtube-feed"), env),
  ]);
  assert.equal(firstResponse.status, 200);
  assert.equal(secondResponse.status, 200);
  assert.equal(fetchCount, 3, "concurrent lazy requests should share one sync");
  const firstBody = await firstResponse.json();
  assert.equal(firstBody.stale, false);
  assert.deepEqual(firstBody.popular.map((video) => video.id), ["video-c", "video-a", "video-b"]);

  mode = "quota";
  const stale = await syncAndMarkStale(env);
  assert.equal(stale.stale, true, "quota failures should retain stale data");
  assert.deepEqual((await env.YOUTUBE_CACHE.read()).latest.map((video) => video.id), firstBody.latest.map((video) => video.id));

  mode = "empty";
  const staleAfterEmpty = await syncAndMarkStale(env);
  assert.equal(staleAfterEmpty.stale, true, "empty channels must not replace the last good snapshot");

  mode = "invalid";
  const invalidEnv = { YOUTUBE_API_KEY: API_KEY, YOUTUBE_CHANNEL_ID: CHANNEL_ID, YOUTUBE_CACHE: makeKv() };
  const invalidResponse = await youtubeFeed(new Request("https://bankersvascular.com/api/youtube-feed"), invalidEnv);
  assert.equal(invalidResponse.status, 503);
  assert.doesNotMatch(await invalidResponse.text(), /test-key-do-not-use|keyInvalid/);

  mode = "timeout";
  const timeoutEnv = { YOUTUBE_API_KEY: API_KEY, YOUTUBE_CHANNEL_ID: CHANNEL_ID, YOUTUBE_CACHE: makeKv() };
  const timeoutResponse = await youtubeFeed(new Request("https://bankersvascular.com/api/youtube-feed"), timeoutEnv);
  assert.equal(timeoutResponse.status, 504);

  const missingResponse = await youtubeFeed(new Request("https://bankersvascular.com/api/youtube-feed"), { YOUTUBE_CACHE: makeKv() });
  assert.equal(missingResponse.status, 503);
  assert.doesNotMatch(await missingResponse.text(), /test-key-do-not-use/);
} finally {
  globalThis.fetch = originalFetch;
}

console.log("YouTube feed unit checks passed");
