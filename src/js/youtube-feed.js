(() => {
  const CHANNEL_URL = "https://www.youtube.com/@bankersvascular";
  const latest = document.querySelector("#youtube-latest");
  const shorts = document.querySelector("#youtube-shorts");
  const popular = document.querySelector("#youtube-popular");
  const staleStatus = document.querySelector("#youtube-stale-status");
  const menuToggle = document.querySelector("#youtube-menu-toggle");
  const menu = document.querySelector("#youtube-site-nav");

  if (menuToggle && menu) {
    menuToggle.addEventListener("click", () => {
      const open = menu.classList.toggle("is-open");
      menuToggle.setAttribute("aria-expanded", String(open));
      const label = menuToggle.querySelector(".sr-only");
      if (label) label.textContent = open ? "Close menu" : "Open menu";
    });
  }

  const nodes = [latest, shorts, popular].filter(Boolean);
  if (!nodes.length) return;

  function clear(node) {
    node.replaceChildren();
  }

  function showLoading(node, short = false) {
    clear(node);
    node.dataset.state = "loading";
    for (let index = 0; index < 3; index += 1) {
      const skeleton = document.createElement("div");
      skeleton.className = `youtube-skeleton${short ? " youtube-skeleton--short" : ""}`;
      skeleton.setAttribute("aria-hidden", "true");
      node.append(skeleton);
    }
  }

  function channelLink() {
    const link = document.createElement("a");
    link.className = "youtube-status-link";
    link.href = CHANNEL_URL;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Visit our YouTube channel";
    return link;
  }

  function showMessage(node, message, isError = false, retry = false) {
    clear(node);
    node.dataset.state = isError ? "error" : "empty";
    const status = document.createElement("p");
    status.className = `youtube-status${isError ? " youtube-error" : ""}`;
    status.append(document.createTextNode(message));
    if (isError) status.append(channelLink());
    if (retry) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "youtube-retry";
      button.textContent = "Try again";
      button.addEventListener("click", load);
      status.append(document.createElement("br"), button);
    }
    node.append(status);
  }

  function formatViews(value) {
    const count = Number(value);
    if (!Number.isFinite(count) || count < 0) return "0";
    return new Intl.NumberFormat("en-IN", {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(count);
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Date unavailable";
    return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(date);
  }

  function safeVideoUrl(video) {
    const candidate = typeof video.url === "string" ? video.url : "";
    try {
      const url = new URL(candidate);
      if (url.protocol === "https:" && url.hostname === "www.youtube.com"
          && (url.pathname === "/watch" || url.pathname.startsWith("/shorts/"))) {
        return url.toString();
      }
    } catch {
      // Fall through to a safe URL derived from the API's video ID.
    }
    const id = typeof video.id === "string" ? video.id : "";
    return id ? `https://www.youtube.com/watch?v=${encodeURIComponent(id)}` : CHANNEL_URL;
  }

  function safeThumbnailUrl(video) {
    const candidate = typeof video?.thumbnail === "string" ? video.thumbnail : "";
    try {
      const url = new URL(candidate);
      if (url.protocol === "https:" && (url.hostname === "i.ytimg.com"
          || url.hostname.endsWith(".ytimg.com"))) return url.toString();
    } catch {
      // Malformed API data is ignored instead of becoming an empty image src.
    }
    return "";
  }

  function createCard(video, isShort, isPopular) {
    const article = document.createElement("article");
    article.className = `youtube-card${isShort ? " youtube-card--short" : ""}`;
    const link = document.createElement("a");
    link.className = "youtube-card-link";
    link.href = safeVideoUrl(video);
    link.target = "_blank";
    link.rel = "noopener noreferrer";

    const image = document.createElement("img");
    image.className = "youtube-card-media";
    image.src = safeThumbnailUrl(video);
    image.alt = typeof video.title === "string" && video.title.trim()
      ? video.title
      : "Bankers Vascular YouTube video";
    image.loading = "lazy";
    image.decoding = "async";
    image.width = isShort ? 180 : 480;
    image.height = isShort ? 320 : 270;
    link.append(image);

    const body = document.createElement("span");
    body.className = "youtube-card-body";
    if (isPopular) {
      const badge = document.createElement("span");
      badge.className = "youtube-badge";
      badge.textContent = "Popular";
      body.append(badge);
    }
    const title = document.createElement("span");
    title.className = "youtube-card-title";
    title.textContent = typeof video.title === "string" ? video.title : "Untitled video";
    const meta = document.createElement("span");
    meta.className = "youtube-card-meta";
    meta.textContent = `${formatViews(video.viewCount)} views · ${formatDate(video.publishedAt)}`;
    body.append(title, meta);
    link.append(body);
    article.append(link);
    return article;
  }

  function render(node, videos, isShort = false, isPopular = false) {
    clear(node);
    node.dataset.state = "ready";
    const usableVideos = Array.isArray(videos)
      ? videos.filter((video) => video && safeThumbnailUrl(video))
      : [];
    if (!usableVideos.length) {
      showMessage(node, "No videos are available in this section yet.");
      return;
    }
    const fragment = document.createDocumentFragment();
    usableVideos.forEach((video) => fragment.append(createCard(video, isShort, isPopular)));
    node.append(fragment);
  }

  function showError() {
    nodes.forEach((node) => showMessage(
      node,
      "Videos are temporarily unavailable.",
      true,
      true,
    ));
  }

  async function load() {
    nodes.forEach((node) => showLoading(node, node === shorts));
    if (staleStatus) staleStatus.hidden = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10_000);
    try {
      const response = await fetch("/api/youtube-feed", {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("Malformed feed response");
      }
      if (!response.ok || data?.ok !== true) throw new Error(data?.error || "Feed unavailable");
      render(latest, data.latest);
      render(shorts, data.shorts, true);
      render(popular, data.popular, false, true);
      if (staleStatus && data.stale && data.updatedAt) {
        staleStatus.textContent = `Showing the latest saved update from ${formatDate(data.updatedAt)}.`;
        staleStatus.hidden = false;
      }
    } catch {
      showError();
    } finally {
      window.clearTimeout(timeout);
    }
  }

  load();
})();
