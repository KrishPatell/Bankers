// Form endpoint for every lead form on the site (appointment, contact,
// newsletter). The Webflow export left all of them as method="get" with no
// action, so submissions were silently dropped once the site left Webflow.
//
// Required env vars (Vercel project settings):
//   RESEND_API_KEY   - https://resend.com API key
//   CONTACT_TO_EMAIL - where enquiries are delivered
//   CONTACT_FROM_EMAIL (optional) - verified sender, defaults to onboarding@resend.dev
//
// Without RESEND_API_KEY the endpoint returns 503 so the form shows its error
// state. It must never answer 200 without having delivered the enquiry.

const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 5;
const hits = new Map();

function rateLimited(ip) {
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((t) => now - t < WINDOW_MS);
  recent.push(now);
  hits.set(ip, recent);
  if (hits.size > 5000) hits.clear(); // bound memory on a warm lambda
  return recent.length > MAX_PER_WINDOW;
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));

async function readBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  const raw = await new Promise((resolve, reject) => {
    let d = "";
    req.on("data", (c) => {
      d += c;
      if (d.length > 100_000) reject(new Error("payload too large"));
    });
    req.on("end", () => resolve(d));
    req.on("error", reject);
  });
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return Object.fromEntries(new URLSearchParams(raw));
  }
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  }

  const ip =
    (req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
  if (rateLimited(ip)) {
    return res
      .status(429)
      .json({ ok: false, error: "Too many submissions. Please try again shortly." });
  }

  let body;
  try {
    body = await readBody(req);
  } catch {
    return res.status(400).json({ ok: false, error: "Malformed request" });
  }

  // Honeypot: a real person never fills a field they cannot see.
  if (String(body._gotcha || "").trim()) {
    return res.status(200).json({ ok: true });
  }

  const name = String(body.Name || body.name || "").trim();
  const phone = String(body["Phone-Number"] || body.phone || "").trim();
  const email = String(body.Email || body.email || "").trim();
  const message = String(body.Message || body.message || "").trim();
  const preferredDate = String(body.Date || "").trim();
  const formName = String(body._form || "Website form").trim();
  const pageName = String(body._page || "").trim();

  if (!name || name.length > 200) {
    return res.status(400).json({ ok: false, error: "Please enter your name." });
  }
  const digits = phone.replace(/\D/g, "");
  if (digits.length < 7 || digits.length > 15) {
    return res
      .status(400)
      .json({ ok: false, error: "Please enter a valid phone number." });
  }
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
    return res.status(400).json({ ok: false, error: "Please enter a valid email." });
  }

  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.CONTACT_TO_EMAIL;
  if (!apiKey || !to) {
    console.error("contact: RESEND_API_KEY or CONTACT_TO_EMAIL is not configured");
    return res.status(503).json({
      ok: false,
      error: "Form is not configured yet. Please call or message us on WhatsApp.",
    });
  }

  const rows = [
    ["Name", name],
    ["Phone", phone],
    ["Email", email || "-"],
    ["Preferred date", preferredDate || "-"],
    ["Message", message || "-"],
    ["Form", formName],
    ["Page", pageName || "-"],
  ];

  try {
    const resp = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: process.env.CONTACT_FROM_EMAIL || "onboarding@resend.dev",
        to: to.split(",").map((s) => s.trim()).filter(Boolean),
        reply_to: email || undefined,
        subject: `${formName} - ${name} (${phone})`,
        html:
          `<h2>New enquiry from bankersvascular.com</h2><table cellpadding="6">` +
          rows
            .map(
              ([k, v]) =>
                `<tr><td><strong>${esc(k)}</strong></td><td>${esc(v)}</td></tr>`
            )
            .join("") +
          `</table>`,
        text: rows.map(([k, v]) => `${k}: ${v}`).join("\n"),
      }),
    });

    if (!resp.ok) {
      const detail = await resp.text();
      console.error("contact: resend failed", resp.status, detail);
      return res
        .status(502)
        .json({ ok: false, error: "Could not send right now. Please try again." });
    }
  } catch (err) {
    console.error("contact: resend threw", err);
    return res
      .status(502)
      .json({ ok: false, error: "Could not send right now. Please try again." });
  }

  return res.status(200).json({ ok: true });
}
