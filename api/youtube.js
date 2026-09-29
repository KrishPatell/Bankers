const API_BASE = "https://www.googleapis.com/youtube/v3";
const RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id=";
// @bankersvascular. The same channel the footer and schema already link to, so
// the feed works without any Cloudflare configuration.
const DEFAULT_CHANNEL_ID = "UC6UCazRbcXgkVpIP6bhk74g";
// Cloudflare caches upstream responses at the edge so homepage traffic never
// fans out into one YouTube request per visitor.
const UPSTREAM = { cf: { cacheTtl: 1800, cacheEverything: true } };

function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=900, s-maxage=21600",
      ...headers,
    },
  });
}

function cleanVideo(item) {
  const snippet = item.snippet || {};
  const stats = item.statistics || {};
  return {
    id: item.id,
    title: snippet.title || "",
    description: snippet.description || "",
    publishedAt: snippet.publishedAt || null,
    thumbnail: snippet.thumbnails?.high?.url || snippet.thumbnails?.medium?.url || snippet.thumbnails?.default?.url || "",
    views: Number(stats.viewCount || 0),
    likes: Number(stats.likeCount || 0),
    duration: item.contentDetails?.duration || "",
    url: `https://www.youtube.com/watch?v=${encodeURIComponent(item.id)}`,
  };
}

async function yt(url, env) {
  const response = await fetch(`${API_BASE}/${url}&key=${encodeURIComponent(env.YOUTUBE_API_KEY)}`, UPSTREAM);
  if (!response.ok) throw new Error(`YouTube API returned ${response.status}`);
  return response.json();
}

async function fromApi(channelId, env) {
  const channel = await yt(`channels?part=contentDetails&id=${encodeURIComponent(channelId)}`, env);
  const uploads = channel.items?.[0]?.contentDetails?.relatedPlaylists?.uploads;
  if (!uploads) throw new Error("YouTube channel was not found");

  const playlist = await yt(`playlistItems?part=snippet,contentDetails&playlistId=${encodeURIComponent(uploads)}&maxResults=50`, env);
  const ids = (playlist.items || []).map((item) => item.contentDetails?.videoId).filter(Boolean);
  if (!ids.length) return [];

  const details = await yt(`videos?part=snippet,statistics,contentDetails&id=${ids.join(",")}`, env);
  return (details.items || []).map(cleanVideo);
}

const decodeXml = (value) => value
  .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
  .replace(/&#x([0-9a-f]+);/gi, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
  .replace(/&#(\d+);/g, (_, dec) => String.fromCodePoint(Number(dec)))
  .replace(/&(lt|gt|quot|apos|amp);/g, (_, name) => ({ lt: "<", gt: ">", quot: '"', apos: "'", amp: "&" }[name]));

const tag = (xml, name) => {
  const match = xml.match(new RegExp(`<${name}(?:\\s[^>]*)?>([\\s\\S]*?)</${name}>`));
  return match ? decodeXml(match[1].trim()) : "";
};

const attr = (xml, name, attribute) => {
  const match = xml.match(new RegExp(`<${name}\\s[^>]*?${attribute}="([^"]*)"`));
  return match ? decodeXml(match[1]) : "";
};

// The public channel feed needs no API key and always lists the 15 newest
// uploads. Workers have no DOMParser, and the feed's shape is fixed, so a
// scoped per-entry match is enough.
export function parseChannelFeed(xml) {
  return (xml.match(/<entry>[\s\S]*?<\/entry>/g) || []).map((entry) => {
    const id = tag(entry, "yt:videoId");
    return {
      id,
      title: tag(entry, "title") || tag(entry, "media:title"),
      description: tag(entry, "media:description"),
      publishedAt: tag(entry, "published") || null,
      thumbnail: attr(entry, "media:thumbnail", "url") || `https://i.ytimg.com/vi/${id}/hqdefault.jpg`,
      views: Number(attr(entry, "media:statistics", "views") || 0),
      likes: 0,
      duration: "",
      url: `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`,
      isShort: /\/shorts\//.test(attr(entry, "link", "href")),
    };
  }).filter((video) => /^[\w-]{11}$/.test(video.id));
}

async function fromRss(channelId) {
  const response = await fetch(RSS_BASE + encodeURIComponent(channelId), UPSTREAM);
  if (!response.ok) throw new Error(`YouTube feed returned ${response.status}`);
  return parseChannelFeed(await response.text());
}

export async function youtubeFeed(request, env) {
  const channelId = env.YOUTUBE_CHANNEL_ID || DEFAULT_CHANNEL_ID;
  let videos;
  let source = "rss";
  try {
    if (env.YOUTUBE_API_KEY) {
      try {
        videos = await fromApi(channelId, env);
        source = "api";
      } catch (error) {
        // A revoked key or spent quota should degrade to the public feed, not
        // take the homepage videos down.
        console.error("youtubeFeed: API failed, using channel feed", error);
      }
    }
    if (!videos) videos = await fromRss(channelId);
  } catch (error) {
    console.error("youtubeFeed:", error);
    return json({ ok: false, error: "Could not load YouTube videos right now." }, 502, { "Cache-Control": "no-store" });
  }

  const latest = [...videos].sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt)).slice(0, 12);
  const popular = [...videos].sort((a, b) => b.views - a.views).slice(0, 6);
  return json({ ok: true, source, latest, popular, updatedAt: new Date().toISOString() });
}
