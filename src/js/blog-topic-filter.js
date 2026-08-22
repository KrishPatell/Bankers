(function () {
  "use strict";

  var filter = document.querySelector("[data-blog-topic-filter]");
  if (!filter) return;

  var buttons = Array.prototype.slice.call(
    filter.querySelectorAll("[data-blog-topic]")
  );
  var cards = Array.prototype.slice.call(
    document.querySelectorAll(".blog-archive-item[data-blog-topics]")
  );
  var emptyState = document.querySelector("[data-blog-topic-empty]");

  function setTopic(topic, updateUrl) {
    var visible = 0;
    cards.forEach(function (card) {
      var topics = (card.getAttribute("data-blog-topics") || "").split(/\s+/);
      var matches = topic === "all" || topics.indexOf(topic) !== -1;
      card.hidden = !matches;
      if (matches) visible += 1;
    });

    buttons.forEach(function (button) {
      var active = button.getAttribute("data-blog-topic") === topic;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    if (emptyState) emptyState.hidden = visible !== 0;

    if (updateUrl && window.history && window.history.replaceState) {
      var url = new URL(window.location.href);
      if (topic === "all") url.searchParams.delete("topic");
      else url.searchParams.set("topic", topic);
      window.history.replaceState({}, "", url.pathname + url.search + url.hash);
    }
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      setTopic(button.getAttribute("data-blog-topic"), true);
    });
  });

  var requestedTopic = new URLSearchParams(window.location.search).get("topic");
  var validTopic = buttons.some(function (button) {
    return button.getAttribute("data-blog-topic") === requestedTopic;
  });
  setTopic(validTopic ? requestedTopic : "all", false);
}());
