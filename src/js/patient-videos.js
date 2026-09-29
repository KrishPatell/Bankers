// Home "Patient Experiences" carousel. The template ships the last hand-picked
// videos as a fallback; this swaps in the channel's newest uploads from the
// Worker feed, and loads a YouTube player only when a visitor presses play.
(() => {
  const root = document.querySelector("[data-patient-videos]");
  if (!root) return;
  const track = root.querySelector("[data-video-track]");
  const prev = root.querySelector("[data-video-prev]");
  const next = root.querySelector("[data-video-next]");
  const LIMIT = 12;

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
  ));
  const formatDate = (value) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(date);
  };

  const card = (video) => {
    const title = esc(video.title);
    const date = formatDate(video.publishedAt);
    return `
      <article class="patient-video-card">
        <button type="button" class="patient-video-play" data-video-id="${esc(video.id)}" data-video-title="${title}" aria-label="Play video: ${title}">
          <img src="https://i.ytimg.com/vi/${esc(video.id)}/hqdefault.jpg" loading="lazy" width="480" height="360" alt="" class="patient-video-thumb">
          <span class="patient-video-icon" aria-hidden="true"></span>
        </button>
        <h3 class="patient-video-title">${title}</h3>
        ${date ? `<p class="patient-video-date">${date}</p>` : ""}
      </article>`;
  };

  const updateNav = () => {
    const max = track.scrollWidth - track.clientWidth;
    root.classList.toggle("is-static", max <= 2);
    prev.disabled = track.scrollLeft <= 2;
    next.disabled = track.scrollLeft >= max - 2;
  };

  const step = (direction) => {
    const first = track.querySelector(".patient-video-card");
    const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
    const width = first ? first.getBoundingClientRect().width + gap : track.clientWidth;
    // Page by whole cards so the snap point always lands on a card edge.
    const cards = Math.max(1, Math.floor((track.clientWidth + gap) / width));
    track.scrollBy({ left: direction * cards * width, behavior: "smooth" });
  };

  prev.addEventListener("click", () => step(-1));
  next.addEventListener("click", () => step(1));
  let frame = 0;
  track.addEventListener("scroll", () => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(updateNav);
  }, { passive: true });
  window.addEventListener("resize", updateNav);

  track.addEventListener("click", (event) => {
    const button = event.target.closest(".patient-video-play");
    if (!button) return;
    const iframe = document.createElement("iframe");
    iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(button.dataset.videoId)}?autoplay=1&rel=0`;
    iframe.title = button.dataset.videoTitle || "YouTube video";
    iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
    iframe.allowFullscreen = true;
    iframe.className = "patient-video-frame";
    button.replaceWith(iframe);
    iframe.focus();
  });

  updateNav();

  fetch("/api/youtube-feed")
    .then((response) => response.json())
    .then((data) => {
      const videos = (data.ok && Array.isArray(data.latest) ? data.latest : [])
        .filter((video) => /^[\w-]{11}$/.test(video.id || ""))
        .slice(0, LIMIT);
      // Never replace a playing fallback video mid-watch.
      if (!videos.length || track.querySelector(".patient-video-frame")) return;
      track.innerHTML = videos.map(card).join("");
      track.scrollLeft = 0;
      updateNav();
    })
    .catch(() => {});
})();
