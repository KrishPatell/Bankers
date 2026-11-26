(() => {
  // Each row contains the reviewer, an original excerpt, and the known rating.
  // The supplied owner replies identify two reviews as 5-star.
  // null leaves the stars hidden until the individual rating is confirmed.
  const reviews = [
    ["chirag mali", "I would sincerely like to thank Dr. Mohal Banker for his excellent treatment, guidance, and care throughout the process.", 5],
    ["sangeetha rangarajan", "We had a really positive experience at the hospital while my mother was being treated for varicose veins.", null],
    ["Justina Shaduka", "Our experience with Bankers Vascular Hospital has been one of the best medical journeys we have ever had.", null],
    ["vihar shah", "I had a very positive experience at the hospital for my varicose vein treatment.", null],
    ["Bhavik Patel", "Excellent hospital with outstanding medical care, hospitality, and facilities.", null],
    ["Unicorn Engineers", "My brother recently underwent varicose vein ulcer surgery at Banker’s Vascular Hospital, and our overall experience was very good.", 5],
    ["Ashutosh Upadhyay", "The team is caring and dedicated to providing the best treatment and support to me.", null],
    ["deep patel", "Everything went smoothly, and the doctors and hospital staff were very supportive and caring throughout the treatment.", null],
    ["mitesh patel", "From the very beginning until the end of my treatment, Mitali Rathod supported and helped us every step of the way.", null],
    ["Chef Rajendra Bisht", "I recently underwent varicose veins treatment at Banker Vascular Hospital, and I am extremely satisfied with my experience.", null],
    ["V M", "We recently visited Dr. Mohal Banker for my mother's varicose veins surgery, and once again our experience was excellent.", null],
    ["daksha Patel", "From the moment I stepped through the doors, everyone was helpful, supportive and friendly.", null],
    ["Parth patel", "The doctors were highly professional, caring, and explained everything clearly.", null],
    ["Jiyal Patel", "The doctor listened carefully to my concerns and explained my condition and treatment options in a simple and understandable way.", null],
    ["Geeta Gusain", "I would like to sincerely thank you Banker Vascular Hospital Dr. Mohal banker and mitali rathod for my husband’s varicose veins treatment.", null],
    ["Vandana Bhavsar", "The doctor explained everything clearly and made me feel comfortable throughout the treatment. The staff was also very supportive.", null],
    ["Sandip Patel", "The Insurance Department was very helpful and made the claim process smooth and hassle-free.", null],
    ["Hansa Vaja", "The doctor was excellent, and the staff were also very kind, supportive, and professional.", null],
    ["Denish Panchani", "Dr. Mohal Banker is not only highly skilled and experienced but also very humble, caring, and reassuring throughout the entire treatment process.", null]
  ];

  function setup(root) {
    if (root.dataset.bvcReviewsReady === "true") return;
    root.dataset.bvcReviewsReady = "true";

    const stage = root.querySelector("[data-stage]");
    const controls = root.querySelector("[data-controls]");
    const left = root.querySelector(".bvc-gr-left");
    const active = root.querySelector(".bvc-gr-active");
    const right = root.querySelector(".bvc-gr-right");
    const stars = root.querySelector("[data-stars]");
    const position = root.querySelector("[data-position]");
    const status = root.querySelector("[data-status]");
    const play = root.querySelector("[data-play]");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    let index = 0;
    let playing = false;
    let visible = !("IntersectionObserver" in window);
    let timer;
    let motion;
    let startTouch;

    const reviewAt = (offset) =>
      reviews[(index + offset + reviews.length) % reviews.length];

    function fillCard(card, [author, quote]) {
      card.querySelector("[data-quote]").textContent = `“${quote}”`;
      card.querySelector("[data-author]").textContent = author;
    }

    function render(direction = 0, announce = false) {
      const current = reviewAt(0);
      fillCard(left, reviewAt(-1));
      fillCard(active, current);
      fillCard(right, reviewAt(1));
      position.textContent = `${index + 1} / ${reviews.length}`;

      stars.replaceChildren();
      stars.hidden = current[2] !== 5;

      if (!stars.hidden) {
        for (let number = 0; number < 5; number += 1) {
          const star = document.createElement("span");
          star.textContent = "★";
          star.setAttribute("aria-hidden", "true");
          stars.append(star);

          if (!reducedMotion.matches && star.animate) {
            star.animate(
              [
                { opacity: .25, transform: "scale(.8)" },
                { opacity: 1, transform: "scale(1)" }
              ],
              { duration: 300, delay: 120 + number * 95, fill: "backwards" }
            );
          }
        }
      }

      motion?.cancel();
      if (direction && !reducedMotion.matches && active.animate) {
        motion = active.animate(
          [
            { transform: `translateX(${direction * 32}px) scale(.96)`, opacity: .55 },
            { transform: "translateX(0) scale(1)", opacity: 1 }
          ],
          { duration: 450, easing: "cubic-bezier(.2,.76,.25,1)" }
        );
      }

      if (announce) {
        const rating = current[2] === 5 ? " 5 out of 5 stars." : "";
        status.textContent =
          `Review ${index + 1} of ${reviews.length}. ${current[0]}.${rating} ${current[1]}`;
      }
    }

    function move(direction, announce) {
      index = (index + direction + reviews.length) % reviews.length;
      render(direction, announce);
      syncAutoplay();
    }

    function syncAutoplay() {
      clearTimeout(timer);
      play.hidden = reducedMotion.matches;
      play.textContent = playing ? "Pause" : "Play";
      play.setAttribute("aria-label", playing ? "Pause automatic reviews" : "Play automatic reviews");

      if (
        playing && visible && !document.hidden && !reducedMotion.matches &&
        !stage.matches(":hover") && !root.contains(document.activeElement)
      ) {
        timer = setTimeout(() => move(1, false), 6500);
      }
    }

    root.querySelector("[data-previous]").addEventListener("click", () => move(-1, true));
    root.querySelector("[data-next]").addEventListener("click", () => move(1, true));

    play.addEventListener("click", () => {
      playing = !playing;
      syncAutoplay();
    });

    controls.addEventListener("keydown", (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      move(event.key === "ArrowRight" ? 1 : -1, true);
    });

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

      if (Math.abs(x) > 45 && Math.abs(x) > Math.abs(y) * 1.3) {
        move(x < 0 ? 1 : -1, true);
      }
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
        stars.querySelectorAll("span").forEach((star) => {
          star.getAnimations?.().forEach((animation) => animation.cancel());
        });
      }
      syncAutoplay();
    });

    stage.hidden = false;
    controls.hidden = false;
    render();
    syncAutoplay();
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
