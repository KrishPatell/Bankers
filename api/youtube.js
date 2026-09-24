const API_BASE = "https://www.googleapis.com/youtube/v3";

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
  const response = await fetch(`${API_BASE}/${url}&key=${encodeURIComponent(env.YOUTUBE_API_KEY)}`);
  if (!response.ok) throw new Error(`YouTube API returned ${response.status}`);
  return response.json();
}

export async function youtubeFeed(request, env) {
  if (!env.YOUTUBE_API_KEY || !env.YOUTUBE_CHANNEL_ID) {
    return json({ ok: false, error: "YouTube sync is not configured yet." }, 503);
  }

  try {
    const channel = await yt(`channels?part=contentDetails&id=${encodeURIComponent(env.YOUTUBE_CHANNEL_ID)}`, env);
    const uploads = channel.items?.[0]?.contentDetails?.relatedPlaylists?.uploads;
    if (!uploads) return json({ ok: false, error: "YouTube channel was not found." }, 404);

    const playlist = await yt(`playlistItems?part=snippet,contentDetails&playlistId=${encodeURIComponent(uploads)}&maxResults=50`, env);
    const ids = (playlist.items || []).map((item) => item.contentDetails?.videoId).filter(Boolean);
    if (!ids.length) return json({ ok: true, latest: [], popular: [], updatedAt: new Date().toISOString() });

    const details = await yt(`videos?part=snippet,statistics,contentDetails&id=${ids.join(",")}`, env);
    const videos = (details.items || []).map(cleanVideo);
    const latest = [...videos].sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt)).slice(0, 12);
    const popular = [...videos].sort((a, b) => b.views - a.views).slice(0, 6);

    return json({ ok: true, latest, popular, updatedAt: new Date().toISOString() });
  } catch (error) {
    console.error("youtubeFeed:", error);
    return json({ ok: false, error: "Could not load YouTube videos right now." }, 502);
  }
}
