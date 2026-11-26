import { youtubeFeed } from "./api/youtube.js";
import { googleReviewsFeed, syncGoogleReviews } from "./api/google-reviews.js";
import {
  APPOINTMENT_CITIES,
  APPOINTMENT_DISEASES,
  claimRequest,
  indianMobileDigits,
  isAppointmentPayload,
  isChecked,
  isFutureOrToday,
  releaseRequest,
} from "./api/appointment-config.js";

// Cloudflare Worker for the static site and its single lead-capture endpoint.
// It runs before static assets so the canonical-origin redirect applies to every
// public URL, including sitemap.xml and robots.txt.

const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 5;
const hits = new Map();
const appointmentRequests = new Map();
const LEGACY_REDIRECTS = {
  "/departments/platelet-rich-plasma": "/treatment/platelet-rich-plasma",
  "/departments/varicose-vein": "/departments/varicose-veins",
  "/varicose-vein": "/varicose-veins/ahmedabad",
  "/home": "/",
  "/dr-mohal-banker": "/our-doctors/dr-mohal-banker",
  "/varicose-veins": "/departments/varicose-veins",
  "/author/drmohal": "/blog-author/dr-mohal",
  "/blog-categories/health-care": "/blog-category/health-care",
  "/blog/10-early-warning-signs-of-peripheral-artery-disease-pad-you-should-never-ignore": "/blog/10-early-signs-of-peripheral-artery-disease-pad-you-shouldn-t-ignore",
  "/varicose-vein-treatment-ahmedabad-india": "/varicose-veins/ahmedabad",
  "/diseases/varicose-vein/glue-therapy-for-varicose-veins": "/treatment/venaseal-glue-embolization",
  "/our-doctors/dr-chandres-bharada": "/our-doctors/dr-chandresh-bharada",
  "/knee-pain": "/departments/knee-pain",
  "/tennis-elbow": "/departments/tennis-elbow",
  "/msk-embolization": "/treatment/msk-embolization",
  "/benign-prostatic-hyperplasia": "/departments/prostate",
  "/heel-pain-2": "/departments/heel-pain",
  "/frozen-shoulder": "/departments/frozen-shoulder",
  "/dr-rozil-gandhi": "/our-doctors/dr-rozil-gandhi",
  "/blog/venous-veins-and-thrombus-": "/blog/venous-veins-and-thrombus",
  "/blog/what-is-genicular-artery-embolisation-a-game-changer-for-knee-pain-in-older-adults": "/blog/gae-for-elderly-patients",
  "/blog/before-you-replace-your-knee-read-this-how-gae-is-changing-knee-pain-treatment": "/blog/gae-vs-knee-replacement-which-one-is-right-for-you",
  "/blog/knee-pain-": "/departments/knee-pain",
};

// These indexable listings are emitted as <folder>/index.html, but their
// sitemap and canonical URLs intentionally omit the trailing slash.
const CANONICAL_DIRECTORY_LISTINGS = new Set([
  "/blog", "/departments", "/bankers-notes", "/services-gujarat",
]);

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
));

function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...headers },
  });
}

function rateLimited(ip) {
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((time) => now - time < WINDOW_MS);
  recent.push(now);
  hits.set(ip, recent);
  if (hits.size > 5000) hits.clear();
  return recent.length > MAX_PER_WINDOW;
}

function renderEmail(rows, formName) {
  const rowHtml = rows.map(([label, value]) => `
    <tr><td style="padding:12px 16px;border-bottom:1px solid #e6edf0;color:#58717d;font:600 12px/18px Arial,sans-serif;letter-spacing:.04em;text-transform:uppercase;vertical-align:top;width:132px">${esc(label)}</td><td style="padding:12px 16px;border-bottom:1px solid #e6edf0;color:#152b36;font:400 15px/22px Arial,sans-serif;word-break:break-word">${esc(value)}</td></tr>`).join("");
  return `<!doctype html><html><body style="margin:0;padding:24px;background:#f2f7f8"><div style="max-width:640px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(15,49,63,.10)"><div style="padding:28px 32px;background:#24586b;color:#fff"><div style="font:700 14px/20px Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#bde4e3">Bankers Vascular Centre</div><h1 style="margin:8px 0 0;font:700 26px/34px Arial,sans-serif">New website enquiry</h1></div><div style="padding:28px 32px 32px"><p style="margin:0 0 20px;color:#58717d;font:400 15px/22px Arial,sans-serif">A visitor submitted the <strong style="color:#152b36">${esc(formName)}</strong>.</p><table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="border:1px solid #e6edf0;border-radius:10px;border-spacing:0;overflow:hidden">${rowHtml}</table><p style="margin:22px 0 0;color:#7a9099;font:400 12px/18px Arial,sans-serif">Sent from bankersvascular.com</p></div></div></body></html>`;
}

async function parseBody(request) {
  const type = request.headers.get("content-type") || "";
  if (type.includes("application/json")) return await request.json();
  return Object.fromEntries(await request.formData());
}

async function appointmentConfig(request, env) {
  if (!env.ASSETS) return null;
  try {
    const url = new URL("/data/appointment-config.json", request.url);
    const response = await env.ASSETS.fetch(new Request(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    }));
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

async function contact(request, env) {
  if (request.method !== "POST") return json({ ok: false, error: "Method not allowed" }, 405, { Allow: "POST" });
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  if (rateLimited(ip)) return json({ ok: false, error: "Too many submissions. Please try again shortly." }, 429);

  let body;
  try { body = await parseBody(request); } catch { return json({ ok: false, error: "Malformed request" }, 400); }
  if (String(body._gotcha || "").trim()) return json({ ok: true });

  const name = String(body.Name || body.name || "").trim();
  const phone = String(body["Phone-Number"] || body.phone || body.mobile || "").trim();
  const city = String(body.City || body.city || "").trim();
  const otherCity = String(body["Other-City"] || body.otherCity || "").trim();
  const disease = String(body.Disease || body.disease || "").trim();
  const email = String(body.Email || body.email || "").trim();
  const message = String(body.Message || body.message || "").trim();
  const preferredDate = String(body.Date || "").trim();
  const preferredTime = String(body["Appointment-Time"] || body.appointmentTime || "").trim();
  const requestCallback = isChecked(body["Request-Callback"] || body.requestCallback);
  const consent = isChecked(body.Consent || body.consent);
  const isAppointment = isAppointmentPayload(body);
  const configuredAppointments = isAppointment ? await appointmentConfig(request, env) : null;
  const requestId = String(body._request_id || request.headers.get("Idempotency-Key") || "").trim();
  const formName = String(body._form || "Website form").trim();
  const pageName = String(body._page || "").trim();
  const digits = phone.replace(/\D/g, "");
  const indianDigits = indianMobileDigits(phone);

  if (!name || name.length > 200) return json({ ok: false, error: "Please enter your name." }, 400);
  if (isAppointment && !/^[6-9]\d{9}$/.test(indianDigits)) {
    return json({ ok: false, error: "Please enter a valid 10-digit Indian mobile number." }, 400);
  }
  if (!isAppointment && phone && (digits.length < 7 || digits.length > 15)) return json({ ok: false, error: "Please enter a valid phone number." }, 400);
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return json({ ok: false, error: "Please enter a valid email." }, 400);
  if (!isAppointment && !phone && !email) return json({ ok: false, error: "Please enter a phone number or email address." }, 400);
  if (isAppointment) {
    if (!APPOINTMENT_CITIES.includes(city)) return json({ ok: false, error: "Please select a valid city." }, 400);
    if (city === "Other City" && (otherCity.length < 2 || otherCity.length > 100)) {
      return json({ ok: false, error: "Please enter the city you would like to visit." }, 400);
    }
    if (!APPOINTMENT_DISEASES.includes(disease)) return json({ ok: false, error: "Please select a valid health condition." }, 400);
    if (preferredDate && !isFutureOrToday(preferredDate)) return json({ ok: false, error: "Please choose today or a future appointment date." }, 400);
    if (preferredDate && configuredAppointments) {
      const dates = configuredAppointments.schedules?.[city]?.dates || [];
      if (!dates.includes(preferredDate)) {
        return json({ ok: false, error: "Please choose a published OPD date for the selected city." }, 400);
      }
    }
    if (!preferredDate && !requestCallback) return json({ ok: false, error: "Please select an appointment date or request a callback." }, 400);
    if (!consent) return json({ ok: false, error: "Please accept the contact consent to continue." }, 400);
    if (preferredTime.length > 100 || message.length > 5000) return json({ ok: false, error: "Please shorten the appointment details and try again." }, 400);
  }
  if (!env.RESEND_API_KEY || !env.CONTACT_TO_EMAIL) return json({ ok: false, error: "Form is not configured yet. Please call or message us on WhatsApp." }, 503);

  if (isAppointment && claimRequest(appointmentRequests, requestId)) {
    return json({ ok: true, duplicate: true });
  }

  const rows = [
    ["Name", name],
    ...(phone ? [["Phone", phone]] : []),
    ...(city ? [["City", city]] : []),
    ...(otherCity ? [["Other city", otherCity]] : []),
    ...(disease ? [["Disease / Treatment", disease]] : []),
    ...(email ? [["Email", email]] : []),
    ...(preferredDate ? [["Preferred date", preferredDate]] : []),
    ...(preferredTime ? [["Preferred time", preferredTime]] : []),
    ...(requestCallback ? [["Callback requested", "Yes"]] : []),
    ...(isAppointment ? [["Contact consent", "Yes"]] : []),
    ...(message ? [["Message", message]] : []),
    ["Form", formName],
    ...(pageName ? [["Page", pageName]] : []),
  ];
  try {
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: env.CONTACT_FROM_EMAIL || "Bankers Vascular Website <onboarding@resend.dev>",
        to: env.CONTACT_TO_EMAIL.split(",").map((value) => value.trim()).filter(Boolean),
        reply_to: email || undefined,
        subject: `${isAppointment ? "New appointment request" : "New website enquiry"} — ${formName}`,
        html: renderEmail(rows, formName),
        text: rows.map(([label, value]) => `${label}: ${value}`).join("\n"),
      }),
    });
    if (!response.ok) {
      if (isAppointment) releaseRequest(appointmentRequests, requestId);
      console.error("contact: Resend rejected submission", response.status);
      return json({ ok: false, error: "Could not send right now. Please try again." }, 502);
    }
  } catch (error) {
    if (isAppointment) releaseRequest(appointmentRequests, requestId);
    console.error("contact: Resend request failed", error);
    return json({ ok: false, error: "Could not send right now. Please try again." }, 502);
  }
  return json({ ok: true });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    // Resolve verified legacy paths before origin normalisation so host aliases
    // reach their canonical destination in one permanent redirect.
    const legacyDestination = LEGACY_REDIRECTS[url.pathname.replace(/\/$/, "")];
    if (legacyDestination) {
      url.protocol = "https:";
      url.hostname = "bankersvascular.com";
      url.pathname = legacyDestination;
      return Response.redirect(url.toString(), 301);
    }
    // One canonical public origin prevents HTTP/www duplicate indexing. Keep
    // the path and query exactly as requested so legacy deep links remain safe.
    if (url.protocol !== "https:" || url.hostname !== "bankersvascular.com") {
      url.protocol = "https:";
      url.hostname = "bankersvascular.com";
      return Response.redirect(url.toString(), 301);
    }
    if (url.pathname === "/api/youtube-feed") return youtubeFeed(request, env);
    if (url.pathname === "/api/google-reviews") return googleReviewsFeed(request, env);
    if (url.pathname === "/api/contact") return contact(request, env);
    if (url.pathname.endsWith("/") && CANONICAL_DIRECTORY_LISTINGS.has(url.pathname.slice(0, -1))) {
      url.pathname = url.pathname.slice(0, -1);
      return Response.redirect(url.toString(), 301);
    }
    return env.ASSETS.fetch(request);
  },
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(syncGoogleReviews(env));
  },
};

export { contact, renderEmail };
