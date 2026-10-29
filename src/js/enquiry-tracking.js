/* Website-owned enquiry events. Never pass form values or link destinations. */
(function () {
  "use strict";
  if (window.BankersEnquiryTracking) return;

  var ga4 = "G-KJGLGHF9XR";
  var lead = "AW-337269747/Ka9bCKe4k4UDEPOn6aAB";
  var phone = "AW-337269747/kBaGCJj1zYEYEPOn6aAB";
  var submissions = new WeakSet();
  var clicks = new WeakSet();

  function send(name, parameters) {
    try {
      if (typeof window.gtag === "function") {
        window.gtag("event", name, parameters);
      }
    } catch (_) {
      // Analytics must never interrupt forms or navigation.
    }
  }

  function locationOf(element) {
    if (element.closest("footer")) return "footer";
    if (element.closest("header, nav")) return "navigation";
    if (element.closest(".ms-chat-wrapper")) return "chat_widget";
    if (element.closest(".contact-form-wrapper")) return "contact_section";
    if (element.closest(".appointment-form-wrapper, .appointment-form-block")) {
      return "appointment_section";
    }
    return "page";
  }

  function formSuccess(form, submission) {
    if (!form || !submission || typeof submission !== "object") return;
    if (submissions.has(submission)) return;
    submissions.add(submission);
    send("generate_lead", {
      send_to: ga4,
      form_location: locationOf(form),
      page_path: window.location.pathname,
    });
    send("conversion", { send_to: lead });
  }

  function validTelephone(href) {
    if (!/^tel:/i.test(href)) return false;
    try {
      var number = decodeURIComponent(href.slice(4)).split(";")[0]
        .replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, "").trim();
      if (!/^\+?[\d().\s-]+$/.test(number)) return false;
      var digits = number.replace(/\D/g, "");
      if (/^\+91/.test(number) && digits.length !== 12) return false;
      return digits.length >= 7 && digits.length <= 15;
    } catch (_) {
      return false;
    }
  }

  function whatsapp(href) {
    try {
      var url = new URL(href, document.baseURI);
      return (url.protocol === "https:" || url.protocol === "http:") &&
        ["wa.me", "api.whatsapp.com", "whatsapp.com", "www.whatsapp.com",
          "web.whatsapp.com"].indexOf(url.hostname.toLowerCase()) !== -1;
    } catch (_) {
      return false;
    }
  }

  function onClick(event) {
    if (event.isTrusted === false || event.defaultPrevented) return;
    if (event.button !== undefined && event.button !== 0) return;
    if (clicks.has(event)) return;
    var target = event.target;
    if (target && !target.closest) target = target.parentElement;
    var link = target && target.closest("a[href]");
    if (!link) return;
    var href = (link.getAttribute("href") || "").trim();
    var isPhone = validTelephone(href);
    if (!isPhone && !whatsapp(href)) return;
    clicks.add(event);
    send(isPhone ? "phone_click" : "whatsapp_click", {
      send_to: ga4,
      page_path: window.location.pathname,
      link_location: locationOf(link),
    });
    if (isPhone) send("conversion", { send_to: phone });
  }

  window.BankersEnquiryTracking = { formSuccess: formSuccess };
  document.addEventListener("click", onClick);
})();
