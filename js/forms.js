/* Drives the site's lead forms against /api/contact.
 *
 * Webflow ships a `.w-form-done` and `.w-form-fail` sibling for every form but
 * relies on its own hosted script to toggle them. This reuses those existing
 * blocks so success and error states keep the original design, and it never
 * shows success unless the server actually accepted the submission. */
(function () {
  "use strict";

  function siblings(form) {
    var wrap = form.closest(".w-form") || form.parentNode;
    return {
      done: wrap ? wrap.querySelector(".w-form-done") : null,
      fail: wrap ? wrap.querySelector(".w-form-fail") : null,
    };
  }

  function show(el) {
    if (el) el.style.display = "block";
  }
  function hide(el) {
    if (el) el.style.display = "none";
  }

  function failWith(form, message) {
    var s = siblings(form);
    hide(s.done);
    if (s.fail) {
      var target = s.fail.querySelector("div") || s.fail;
      if (message) target.textContent = message;
      show(s.fail);
    } else if (message) {
      window.alert(message);
    }
  }

  function submitButtons(form) {
    return Array.prototype.slice.call(
      form.querySelectorAll('input[type="submit"], button[type="submit"]')
    );
  }

  function onSubmit(event) {
    var form = event.target;
    if (!form || form.tagName !== "FORM") return;
    if (form.getAttribute("action") !== "/api/contact") return;

    event.preventDefault();
    event.stopPropagation();

    var s = siblings(form);
    hide(s.done);
    hide(s.fail);

    var payload = {};
    new FormData(form).forEach(function (value, key) {
      payload[key] = typeof value === "string" ? value : "";
    });
    payload._form = form.getAttribute("data-form-name") || "Website form";
    payload._page = form.getAttribute("data-form-page") || document.title;

    var buttons = submitButtons(form);
    buttons.forEach(function (b) {
      b.dataset.originalValue = b.value || b.textContent;
      var waiting = b.getAttribute("data-wait") || "Please wait...";
      if (b.tagName === "INPUT") b.value = waiting;
      else b.textContent = waiting;
      b.disabled = true;
    });

    function restore() {
      buttons.forEach(function (b) {
        var original = b.dataset.originalValue;
        if (original !== undefined) {
          if (b.tagName === "INPUT") b.value = original;
          else b.textContent = original;
        }
        b.disabled = false;
      });
    }

    fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        return res
          .json()
          .catch(function () {
            return { ok: res.ok };
          })
          .then(function (data) {
            return { res: res, data: data };
          });
      })
      .then(function (out) {
        restore();
        if (out.res.ok && out.data && out.data.ok) {
          form.style.display = "none";
          show(siblings(form).done);
          form.reset();
        } else {
          failWith(
            form,
            (out.data && out.data.error) ||
              "Something went wrong. Please call us or message on WhatsApp."
          );
        }
      })
      .catch(function () {
        restore();
        failWith(
          form,
          "Network error. Please call us or message on WhatsApp."
        );
      });
  }

  document.addEventListener("submit", onSubmit, true);
})();
