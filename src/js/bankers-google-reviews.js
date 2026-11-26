(() => {
  function formatReviewAge(value) {
    const timestamp = Date.parse(value || "");
    const elapsed = Date.now() - timestamp;
    if (!Number.isFinite(timestamp)) return "Google review";
    if (elapsed < 60 * 1000) return "Just now";

    const units = [
      ["year", 365 * 24 * 60 * 60 * 1000],
      ["month", 30 * 24 * 60 * 60 * 1000],
      ["week", 7 * 24 * 60 * 60 * 1000],
      ["day", 24 * 60 * 60 * 1000],
      ["hour", 60 * 60 * 1000],
      ["minute", 60 * 1000],
    ];
    const [unit, duration] = units.find(([, size]) => elapsed >= size) || units[units.length - 1];
    const amount = Math.floor(elapsed / duration);
    return `${amount} ${unit}${amount === 1 ? "" : "s"} ago`;
  }

  function initials(name) {
    return String(name || "Google reviewer").trim().charAt(0).toUpperCase() || "G";
  }

  async function fetchFeed() {
    const response = await fetch("/api/google-reviews", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`Google review feed returned ${response.status}`);
    const feed = await response.json();
    if (!feed.ok || !Array.isArray(feed.reviews) || !feed.reviews.length) {
      throw new Error("Google review feed is empty");
    }
    return feed;
  }

  function setup(root) {
    if (root.dataset.bvcReviewsReady === "true") return;
    root.dataset.bvcReviewsReady = "true";

    const stage = root.querySelector("[data-stage]");
    const extraLeft = root.querySelector(".bvc-gr-extra-left");
    const left = root.querySelector(".bvc-gr-left");
    const active = root.querySelector(".bvc-gr-active");
    const right = root.querySelector(".bvc-gr-right");
    const extraRight = root.querySelector(".bvc-gr-extra-right");
    const status = root.querySelector("[data-status]");
    const branchLinks = root.querySelector("[data-branch-links]");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    let reviews = [];
    let index = 0;
    let playing = !reducedMotion.matches;
    let visible = !("IntersectionObserver" in window);
    let timer;
    let motion;
    let startTouch;

    function reviewAt(offset) {
      if (!reviews.length) return null;
      return reviews[(index + offset + reviews.length) % reviews.length];
    }

    function fillCard(card, review) {
      if (!card) return;
      card.hidden = !review;
      if (!review) {
        card.removeAttribute("href");
        return;
      }

      card.href = review.reviewUrl || "#";
      card.setAttribute("aria-label", `Read ${review.author || "reviewer"}'s review on Google`);
      card.querySelector("[data-quote]").textContent = review.comment ? `“${review.comment}”` : "";
      card.querySelector("[data-quote]").hidden = !review.comment;
      const ratingOnly = card.querySelector("[data-rating-only]");
      ratingOnly.hidden = Boolean(review.comment);
      card.querySelector("[data-author]").textContent = review.author || "Google reviewer";
      card.querySelector("[data-avatar]").textContent = initials(review.author);
      const dateElement = card.querySelector("[data-date]");
      dateElement.textContent = formatReviewAge(review.createdAt || review.updatedAt);
      card.querySelector("[data-location]").textContent = review.branchLabel || "Bankers Vascular Centre";

      const stars = card.querySelector("[data-stars]");
      stars.replaceChildren();
      stars.hidden = false;
      for (let number = 0; number < 5; number += 1) {
        const star = document.createElement("span");
        star.textContent = "★";
        star.setAttribute("aria-hidden", "true");
        stars.append(star);

        if (!reducedMotion.matches && star.animate) {
          star.animate(
            [
              { opacity: .25, transform: "scale(.8)" },
              { opacity: 1, transform: "scale(1)" },
            ],
            { duration: 300, delay: 120 + number * 95, fill: "backwards" },
          );
        }
      }
    }

    function render(direction = 0, announce = false) {
      const current = reviewAt(0);
      fillCard(extraLeft, reviewAt(-2));
      fillCard(left, reviewAt(-1));
      fillCard(active, current);
      fillCard(right, reviewAt(1));
      fillCard(extraRight, reviewAt(2));
      motion?.cancel();

      if (direction && !reducedMotion.matches && active.animate) {
        motion = active.animate(
          [
            { transform: `translateY(${direction * 8}px)`, opacity: .72 },
            { transform: "translateY(0)", opacity: 1 },
          ],
          { duration: 300, easing: "cubic-bezier(.2,.76,.25,1)" },
        );
      }

      if (announce && current) {
        const description = current.comment ? ` ${current.comment}` : " No written comment.";
        status.textContent = `Review ${index + 1} of ${reviews.length}. ${current.author}. 5 out of 5 stars.${description}`;
      }
    }

    function move(direction, announce) {
      if (reviews.length < 2) return;
      index = (index + direction + reviews.length) % reviews.length;
      render(direction, announce);
      syncAutoplay();
    }

    function syncAutoplay() {
      clearTimeout(timer);
      if (
        playing && visible && !document.hidden && !reducedMotion.matches &&
        !stage.matches(":hover") && !root.contains(document.activeElement)
      ) {
        timer = setTimeout(() => move(1, false), 6500);
      }
    }

    function renderBranchLinks(locations) {
      const links = (Array.isArray(locations) ? locations : []).filter((location) => location?.mapsUrl);
      branchLinks.replaceChildren();
      links.forEach((location) => {
        const link = document.createElement("a");
        link.className = "bvc-gr-link";
        link.href = location.mapsUrl;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = `View ${location.label || "branch"} on Google ↗`;
        branchLinks.append(link);
      });
      branchLinks.hidden = !links.length;
    }

    function init(feed) {
      reviews = feed.reviews.filter((review) => review && review.rating === 5 && review.reviewUrl);
      if (!reviews.length) return;
      renderBranchLinks(feed.locations);
      stage.hidden = false;
      root.hidden = false;
      render();
      syncAutoplay();
    }

    root.addEventListener("focusin", syncAutoplay);
    root.addEventListener("focusout", () => setTimeout(syncAutoplay, 0));
    stage.addEventListener("mouseenter", syncAutoplay);
    stage.addEventListener("mouseleave", syncAutoplay);
    document.addEventListener("visibilitychange", syncAutoplay);

    stage.addEventListener("touchstart", (event) => {
      startTouch = event.touches.length === 1 ? event.touches[0] : null;
    }, { passive: true });

    stage.addEventListener("touchend", (event) => {
      if (!startTouch) return;
      const point = event.changedTouches[0];
      const x = point.clientX - startTouch.clientX;
      const y = point.clientY - startTouch.clientY;
      startTouch = null;
      if (Math.abs(x) > 45 && Math.abs(x) > Math.abs(y) * 1.3) move(x < 0 ? 1 : -1, true);
    }, { passive: true });

    stage.addEventListener("touchcancel", () => { startTouch = null; });

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
        syncAutoplay();
      });
      observer.observe(root);
    }

    reducedMotion.addEventListener("change", () => {
      if (reducedMotion.matches) {
        playing = false;
        motion?.cancel();
        root.querySelectorAll("[data-stars] span").forEach((star) => {
          star.getAnimations?.().forEach((animation) => animation.cancel());
        });
      } else {
        playing = true;
      }
      syncAutoplay();
    });

    fetchFeed().then(init).catch(() => {
      // Keep the section hidden until a complete, server-synced feed exists.
      root.hidden = true;
    });
  }

  function init() {
    document.querySelectorAll(".bvc-google-reviews").forEach(setup);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
