// Cloudflare Worker for the static site and its single lead-capture endpoint.
// Static files bypass this script; only /api/* is routed here (wrangler.jsonc).

const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 5;
const hits = new Map();

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

async function contact(request, env) {
  if (request.method !== "POST") return json({ ok: false, error: "Method not allowed" }, 405, { Allow: "POST" });
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  if (rateLimited(ip)) return json({ ok: false, error: "Too many submissions. Please try again shortly." }, 429);

  let body;
  try { body = await parseBody(request); } catch { return json({ ok: false, error: "Malformed request" }, 400); }
  if (String(body._gotcha || "").trim()) return json({ ok: true });

  const name = String(body.Name || body.name || "").trim();
  const phone = String(body["Phone-Number"] || body.phone || "").trim();
  const email = String(body.Email || body.email || "").trim();
  const message = String(body.Message || body.message || "").trim();
  const preferredDate = String(body.Date || "").trim();
  const formName = String(body._form || "Website form").trim();
  const pageName = String(body._page || "").trim();
  const digits = phone.replace(/\D/g, "");

  if (!name || name.length > 200) return json({ ok: false, error: "Please enter your name." }, 400);
  if (phone && (digits.length < 7 || digits.length > 15)) return json({ ok: false, error: "Please enter a valid phone number." }, 400);
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return json({ ok: false, error: "Please enter a valid email." }, 400);
  if (!phone && !email) return json({ ok: false, error: "Please enter a phone number or email address." }, 400);
  if (!env.RESEND_API_KEY || !env.CONTACT_TO_EMAIL) return json({ ok: false, error: "Form is not configured yet. Please call or message us on WhatsApp." }, 503);

  const rows = [
    ["Name", name],
    ...(phone ? [["Phone", phone]] : []),
    ...(email ? [["Email", email]] : []),
    ...(preferredDate ? [["Preferred date", preferredDate]] : []),
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
        subject: `New website enquiry — ${formName}`,
        html: renderEmail(rows, formName),
        text: rows.map(([label, value]) => `${label}: ${value}`).join("\n"),
      }),
    });
    if (!response.ok) {
      console.error("contact: Resend rejected submission", response.status);
      return json({ ok: false, error: "Could not send right now. Please try again." }, 502);
    }
  } catch (error) {
    console.error("contact: Resend request failed", error);
    return json({ ok: false, error: "Could not send right now. Please try again." }, 502);
  }
  return json({ ok: true });
}

export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname === "/api/contact") return contact(request, env);
    return env.ASSETS.fetch(request);
  },
};

export { contact, renderEmail };
