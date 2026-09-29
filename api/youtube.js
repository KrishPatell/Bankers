const API_BASE = "https://www.googleapis.com/youtube/v3";
const CACHE_KEY = "youtube-feed-v1";
const REQUEST_TIMEOUT_MS = 8_000;
const LATEST_LIMIT = 12;
const SHORTS_LIMIT = 12;
const POPULAR_LIMIT = 12;

let inFlightSync = null;

class YouTubeError extends Error {
  constructor(code, status = 502) {
    super(code);
    this.name = "YouTubeError";
    this.code = code;
    this.status = status;
  }
}

function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": status >= 400 ? "no-store" : "public, max-age=300, s-maxage=900",
      ...headers,
    },
  });
}

function configError(env) {
  if (!env?.YOUTUBE_API_KEY || !env?.YOUTUBE_CHANNEL_ID) {
    return new YouTubeError("not_configured", 503);
  }
  if (!env?.YOUTUBE_CACHE || typeof env.YOUTUBE_CACHE.get !== "function") {
    return new YouTubeError("cache_not_configured", 503);
  }
  return null;
}

function parseViewCount(value) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : 0;
}

function parseIsoDuration(value) {
  const match = /^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$/i.exec(String(value || ""));
  if (!match) return 0;
  return (Number(match[1] || 0) * 3600)
    + (Number(match[2] || 0) * 60)
    + Number(match[3] || 0);
}

function isShortVideo({ duration = "", title = "", description = "" } = {}) {
  const hasShortsHint = /(^|\s)#shorts\b/i.test(`${title} ${description}`);
  const durationSeconds = parseIsoDuration(duration);
  // YouTube's Shorts format now allows videos up to three minutes. The Data
  // API does not expose the Shorts label, so duration <= 180 seconds is the
  // primary heuristic; #shorts also covers uploads whose duration metadata is
  // missing or whose creator explicitly labels the format.
  return (durationSeconds > 0 && durationSeconds <= 180) || hasShortsHint;
}

function bestThumbnail(thumbnails = {}) {
  return thumbnails.maxres?.url
    || thumbnails.standard?.url
    || thumbnails.high?.url
    || thumbnails.medium?.url
    || thumbnails.default?.url
    || "";
}

function normalizeVideo(item = {}) {
  const snippet = item.snippet || {};
  const details = item.contentDetails || {};
  const statistics = item.statistics || {};
  const id = typeof item.id === "string" ? item.id : "";
  const title = typeof snippet.title === "string" ? snippet.title : "";
  const description = typeof snippet.description === "string" ? snippet.description : "";
  const duration = typeof details.duration === "string" ? details.duration : "";
  const isShort = isShortVideo({ duration, title, description });

  return {
    id,
    title,
    thumbnail: bestThumbnail(snippet.thumbnails),
    publishedAt: typeof snippet.publishedAt === "string" ? snippet.publishedAt : null,
    viewCount: parseViewCount(statistics.viewCount),
    duration,
    isShort,
    url: `https://www.youtube.com/${isShort ? "shorts/" : "watch?v="}${encodeURIComponent(id)}`,
  };
}

function publishedTime(video) {
  const time = Date.parse(video.publishedAt || "");
  return Number.isFinite(time) ? time : 0;
}

function sortLatest(a, b) {
  return publishedTime(b) - publishedTime(a);
}

function sortPopular(a, b) {
  return b.viewCount - a.viewCount || sortLatest(a, b);
}

function buildNormalizedFeed(channel, items) {
  const videos = items
    .map(normalizeVideo)
    .filter((video) => video.id && video.title && video.thumbnail);
  if (!videos.length) throw new YouTubeError("empty_channel", 503);

  const latest = [...videos].sort(sortLatest).slice(0, LATEST_LIMIT);
  const shorts = videos.filter((video) => video.isShort).sort(sortLatest).slice(0, SHORTS_LIMIT);
  const popular = [...videos].sort(sortPopular).slice(0, POPULAR_LIMIT);
  return {
    ok: true,
    updatedAt: new Date().toISOString(),
    stale: false,
    channel: {
      id: channel.id,
      title: channel.title,
      url: `https://www.youtube.com/channel/${encodeURIComponent(channel.id)}`,
    },
    latest,
    shorts,
    popular,
  };
}

async function fetchWithTimeout(url, init = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (error?.name === "AbortError") throw new YouTubeError("timeout", 504);
    throw new YouTubeError("network", 502);
  } finally {
    clearTimeout(timeout);
  }
}

async function youtubeRequest(resource, params, env) {
  const url = new URL(`${API_BASE}/${resource}`);
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
  // Keep the key in the request URL sent upstream, but never log this URL or
  // include upstream error bodies in a response sent to the browser.
  url.searchParams.set("key", env.YOUTUBE_API_KEY);
  const response = await fetchWithTimeout(url.toString());
  let body;
  try {
    body = await response.json();
  } catch {
    throw new YouTubeError("malformed_response", 502);
  }
  if (!response.ok) {
    const reason = body?.error?.errors?.[0]?.reason || body?.error?.status || "upstream_error";
    if (reason === "quotaExceeded" || reason === "rateLimitExceeded") {
      throw new YouTubeError("quota", 503);
    }
    if (response.status === 400 || response.status === 403) {
      throw new YouTubeError("invalid_api_key", 503);
    }
    throw new YouTubeError("upstream_error", 502);
  }
  if (!body || typeof body !== "object") throw new YouTubeError("malformed_response", 502);
  return body;
}

async function fetchFeedFromYouTube(env) {
  const channelResponse = await youtubeRequest("channels", {
    part: "snippet,contentDetails",
    id: env.YOUTUBE_CHANNEL_ID,
  }, env);
  const channelItem = channelResponse.items?.[0];
  const uploads = channelItem?.contentDetails?.relatedPlaylists?.uploads;
  if (!channelItem || !uploads) throw new YouTubeError("channel_not_found", 404);

  const ids = [];
  const seen = new Set();
  let pageToken = "";
  do {
    const page = await youtubeRequest("playlistItems", {
      part: "snippet,contentDetails",
      playlistId: uploads,
      maxResults: "50",
      ...(pageToken ? { pageToken } : {}),
    }, env);
    for (const item of page.items || []) {
      const id = item.contentDetails?.videoId;
      if (id && !seen.has(id)) {
        seen.add(id);
        ids.push(id);
      }
    }
    pageToken = typeof page.nextPageToken === "string" ? page.nextPageToken : "";
  } while (pageToken);

  if (!ids.length) throw new YouTubeError("empty_channel", 503);

  const details = [];
  for (let index = 0; index < ids.length; index += 50) {
    const batch = ids.slice(index, index + 50);
    const response = await youtubeRequest("videos", {
      part: "snippet,statistics,contentDetails",
      id: batch.join(","),
    }, env);
    if (!Array.isArray(response.items)) throw new YouTubeError("malformed_response", 502);
    details.push(...response.items);
  }

  const channelTitle = typeof channelItem.snippet?.title === "string"
    ? channelItem.snippet.title
    : "Bankers Vascular Centre";
  return buildNormalizedFeed({ id: env.YOUTUBE_CHANNEL_ID, title: channelTitle }, details);
}

async function readCache(env) {
  let raw;
  try {
    raw = await env.YOUTUBE_CACHE.get(CACHE_KEY);
  } catch {
    throw new YouTubeError("cache_unavailable", 503);
  }
  if (!raw) return null;
  try {
    const value = JSON.parse(raw);
    if (!value || value.ok !== true || !value.channel || !Array.isArray(value.latest)
        || !Array.isArray(value.shorts) || !Array.isArray(value.popular)
        || typeof value.updatedAt !== "string") return null;
    return value;
  } catch {
    return null;
  }
}

async function writeCache(env, value) {
  try {
    await env.YOUTUBE_CACHE.put(CACHE_KEY, JSON.stringify(value));
  } catch {
    throw new YouTubeError("cache_unavailable", 503);
  }
}

export async function syncYouTubeFeed(env) {
  const error = configError(env);
  if (error) throw error;
  const feed = await fetchFeedFromYouTube(env);
  await writeCache(env, feed);
  return feed;
}

async function syncOnce(env) {
  if (!inFlightSync) {
    inFlightSync = syncYouTubeFeed(env).finally(() => { inFlightSync = null; });
  }
  return inFlightSync;
}

export async function syncAndMarkStale(env) {
  try {
    return await syncOnce(env);
  } catch (error) {
    const cached = await readCache(env).catch(() => null);
    if (!cached) throw error;
    const stale = { ...cached, stale: true };
    await writeCache(env, stale).catch(() => {});
    return stale;
  }
}

function publicError(error) {
  switch (error?.code) {
    case "not_configured":
      return json({ ok: false, error: "YouTube feed is not configured yet." }, 503);
    case "cache_not_configured":
      return json({ ok: false, error: "YouTube feed cache is not configured yet." }, 503);
    case "channel_not_found":
      return json({ ok: false, error: "The configured YouTube channel could not be found." }, 404);
    case "invalid_api_key":
      return json({ ok: false, error: "The YouTube feed is temporarily unavailable." }, 503);
    case "quota":
    case "timeout":
    case "network":
    case "empty_channel":
    case "malformed_response":
    case "upstream_error":
    case "cache_unavailable":
    default:
      return json({ ok: false, error: "The YouTube feed is temporarily unavailable." }, error?.status || 503);
  }
}

export async function youtubeFeed(request, env) {
  if (request.method !== "GET") return json({ ok: false, error: "Method not allowed" }, 405, { Allow: "GET" });
  const config = configError(env);
  if (config) return publicError(config);

  let cached;
  try {
    cached = await readCache(env);
  } catch (error) {
    return publicError(error);
  }
  if (cached) return json(cached);

  try {
    return json(await syncOnce(env));
  } catch (error) {
    return publicError(error);
  }
}

export {
  CACHE_KEY,
  buildNormalizedFeed,
  isShortVideo,
  normalizeVideo,
  parseIsoDuration,
  parseViewCount,
};
