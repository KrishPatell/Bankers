(() => {
  const popular = document.querySelector("#youtube-popular");
  const latest = document.querySelector("#youtube-latest");
  const formatViews = (value) => new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(value);
  const formatDate = (value) => new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(value));
  const card = (video, isPopular) => `
    <article class="youtube-card">
      <a href="${video.url}" target="_blank" rel="noopener"><img src="${video.thumbnail}" alt="${video.title.replace(/"/g, "&quot;")}" loading="lazy"></a>
      <div class="youtube-card-body">
        ${isPopular ? '<span class="youtube-badge">Popular</span>' : ""}
        <h3><a href="${video.url}" target="_blank" rel="noopener">${video.title}</a></h3>
        <p class="youtube-meta">${formatViews(video.views)} views · ${formatDate(video.publishedAt)}</p>
      </div>
    </article>`;
  const render = (node, videos, isPopular) => { node.innerHTML = videos.length ? videos.map((video) => card(video, isPopular)).join("") : '<p class="youtube-status">No videos found.</p>'; };
  fetch("/api/youtube-feed").then((response) => response.json()).then((data) => {
    if (!data.ok) throw new Error(data.error || "Unable to load videos");
    render(popular, data.popular, true); render(latest, data.latest, false);
  }).catch((error) => {
    popular.innerHTML = latest.innerHTML = `<p class="youtube-status youtube-error">${error.message}</p>`;
  });
})();
