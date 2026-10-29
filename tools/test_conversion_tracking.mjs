import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const helper = fs.readFileSync(path.join(root, "src/js/enquiry-tracking.js"), "utf8");
const forms = fs.readFileSync(path.join(root, "src/js/forms.js"), "utf8");
const ga4 = "G-KJGLGHF9XR";
const adsLead = "AW-337269747/Ka9bCKe4k4UDEPOn6aAB";
const adsPhone = "AW-337269747/kBaGCJj1zYEYEPOn6aAB";
let passed = 0;

function runtime({ analytics = "available", duplicate = false } = {}) {
  const listeners = {};
  const calls = [];
  const requests = [];
  const responses = [];
  const document = {
    baseURI: "https://bankersvascular.com/contact-us",
    title: "Contact Us",
    addEventListener(type, listener) {
      (listeners[type] ||= []).push(listener);
    },
  };
  const context = vm.createContext({
    document, URL, WeakSet,
    location: { pathname: "/contact-us", search: "?email=private@example.invalid", hash: "#private" },
    FormData: class {
      constructor(form) { this.values = form.values; }
      forEach(fn) { Object.entries(this.values).forEach(([key, value]) => fn(value, key)); }
    },
    fetch(url, options) {
      requests.push({ url, ...options });
      assert.equal(url, "/api/contact"); // Never send a real enquiry or analytics request.
      const next = responses.shift();
      assert.ok(next, "test must supply a response");
      return typeof next === "function" ? next() : Promise.resolve(next);
    },
    alert() { throw new Error("Unexpected alert"); },
  });
  context.window = context;
  if (analytics !== "missing") {
    context.gtag = (...args) => {
      if (analytics === "throws") throw new Error("Analytics unavailable");
      calls.push(JSON.parse(JSON.stringify(args)));
    };
  }
  vm.runInContext(helper, context);
  vm.runInContext(forms, context);
  if (duplicate) {
    vm.runInContext(helper, context);
    vm.runInContext(forms, context);
  }
  return { context, listeners, calls, requests, responses };
}

function form() {
  const done = { style: { display: "none" } };
  const error = { textContent: "" };
  const fail = { style: { display: "none" }, querySelector: () => error };
  const wrap = { querySelector: (selector) => selector === ".w-form-done" ? done : fail };
  const button = {
    tagName: "BUTTON", textContent: "Submit", disabled: false, dataset: {},
    getAttribute: () => "Please wait...",
  };
  const attributes = { action: "/api/contact", "data-form-name": "Contact", "data-form-page": "Contact page" };
  return {
    tagName: "FORM", style: {}, done, fail, error, button, resetCount: 0,
    values: { Name: "Test Patient", "Phone-Number": "+919999999999", Email: "private@example.invalid", Message: "private medical details", _gotcha: "" },
    getAttribute: (name) => attributes[name],
    closest: (selector) => selector === ".w-form" ? wrap : selector === ".contact-form-wrapper" ? wrap : null,
    querySelectorAll: () => [button],
    reset() { this.resetCount++; },
  };
}

const response = (http = true, data = { ok: true }) => ({ ok: http, json: () => Promise.resolve(data) });
const settle = async () => { for (let i = 0; i < 5; i++) await new Promise(setImmediate); };
function submit(r, f) {
  const event = { target: f, preventDefault() {}, stopPropagation() {} };
  for (const listener of r.listeners.submit) listener(event);
}
function click(r, href, overrides = {}) {
  const link = { getAttribute: () => href, closest: () => null };
  // A nested image/text span resolves to its owning anchor, as on the real CTAs.
  const event = { target: { closest: () => link }, isTrusted: true, button: 0, defaultPrevented: false, ...overrides };
  for (const listener of r.listeners.click) listener(event);
  assert.equal(event.defaultPrevented, Boolean(overrides.defaultPrevented), "tracking must not cancel navigation");
  return event;
}
function expectedLead(count = 1) {
  return Array.from({ length: count }, () => [
    ["event", "generate_lead", { send_to: ga4, form_location: "contact_section", page_path: "/contact-us" }],
    ["event", "conversion", { send_to: adsLead }],
  ]).flat();
}
function checkPrivacy(calls) {
  for (const [, name, parameters] of calls) {
    const allowed = name === "conversion" ? ["send_to"] : name === "generate_lead" ? ["send_to", "form_location", "page_path"] : ["send_to", "page_path", "link_location"];
    assert.deepEqual(Object.keys(parameters).sort(), allowed.sort());
  }
  assert.doesNotMatch(JSON.stringify(calls), /Test Patient|9999999999|private|Message|Email|Phone-Number|\?|#/);
}
async function test(name, fn) {
  await fn();
  console.log(`PASS ${name}`);
  passed++;
}

await test("page load and repeated script inclusion emit no conversions and register once", () => {
  const r = runtime({ duplicate: true });
  assert.equal(r.listeners.click.length, 1);
  assert.equal(r.listeners.submit.length, 1);
  assert.deepEqual(r.calls, []);
});

for (const [name, reply] of [
  ["failed HTTP with ok:true", response(false)],
  ["API rejection", response(true, { ok: false, error: "Rejected" })],
  ["truthy string is not explicit acceptance", response(true, { ok: "true" })],
  ["missing ok", response(true, {})],
  ["null JSON", response(true, null)],
  ["unparseable HTTP-success JSON", { ok: true, json: () => Promise.reject(new Error("Invalid JSON")) }],
  ["network error", () => Promise.reject(new Error("Offline"))],
]) {
  await test(`${name}: no lead events; error UI and buttons restored`, async () => {
    const r = runtime(); const f = form(); r.responses.push(reply);
    submit(r, f); await settle();
    assert.deepEqual(r.calls, []);
    assert.equal(f.fail.style.display, "block");
    assert.equal(f.done.style.display, "none");
    assert.equal(f.button.disabled, false);
    assert.equal(f.resetCount, 0);
  });
}

await test("one server-accepted enquiry produces exactly one GA4/Ads pair", async () => {
  const r = runtime({ duplicate: true }); const f = form(); r.responses.push(response());
  submit(r, f); await settle();
  assert.deepEqual(r.calls, expectedLead());
  assert.equal(f.style.display, "none");
  assert.equal(f.done.style.display, "block");
  assert.equal(f.resetCount, 1);
  assert.equal(f.button.disabled, false);
  const payload = JSON.parse(r.requests[0].body);
  assert.deepEqual(payload, { ...f.values, _form: "Contact", _page: "Contact page" });
  assert.equal(r.requests[0].method, "POST");
  checkPrivacy(r.calls);
});

await test("pending submission and duplicate success callbacks cannot double count", async () => {
  const r = runtime(); const f = form(); let accept;
  r.responses.push(() => new Promise((resolve) => { accept = resolve; }));
  submit(r, f); submit(r, f);
  assert.equal(r.requests.length, 1);
  assert.deepEqual(r.calls, []);
  accept(response()); await settle();
  assert.deepEqual(r.calls, expectedLead());
  const token = {};
  r.context.BankersEnquiryTracking.formSuccess(f, token);
  r.context.BankersEnquiryTracking.formSuccess(f, token);
  assert.deepEqual(r.calls, expectedLead(2));
});

await test("two distinct successful submissions produce two event pairs", async () => {
  const r = runtime(); const f = form();
  for (let i = 0; i < 2; i++) { r.responses.push(response()); submit(r, f); await settle(); }
  assert.equal(r.requests.length, 2);
  assert.deepEqual(r.calls, expectedLead(2));
});

await test("honeypot acknowledgement is not counted as a patient lead", async () => {
  const r = runtime(); const f = form(); f.values._gotcha = "bot";
  r.responses.push(response()); submit(r, f); await settle();
  assert.deepEqual(r.calls, []);
});

await test("valid telephone click produces one phone event and existing Ads conversion", () => {
  const r = runtime({ duplicate: true });
  const event = click(r, "tel:+91\u202d99099-03449\u202c");
  for (const listener of r.listeners.click) listener(event);
  assert.deepEqual(r.calls, [
    ["event", "phone_click", { send_to: ga4, page_path: "/contact-us", link_location: "page" }],
    ["event", "conversion", { send_to: adsPhone }],
  ]);
  checkPrivacy(r.calls);
});

await test("WhatsApp destinations produce GA4 only, once per genuine click", () => {
  const r = runtime();
  for (const host of ["wa.me", "api.whatsapp.com", "whatsapp.com", "www.whatsapp.com", "web.whatsapp.com"]) {
    click(r, `https://${host}/send?phone=919999999999&text=private`);
  }
  assert.equal(r.calls.length, 5);
  for (const call of r.calls) assert.deepEqual(call, ["event", "whatsapp_click", { send_to: ga4, page_path: "/contact-us", link_location: "page" }]);
  checkPrivacy(r.calls);
});

await test("invalid telephone, unrelated/spoofed URLs, synthetic and cancelled clicks emit nothing", () => {
  const r = runtime();
  for (const href of ["tel:", "tel:not-a-number", "tel:+919099-08428", "https://whatsapp.com.example.invalid/send", "https://example.invalid/whatsapp.com", "/contact-us", "#", "javascript:alert(1)"]) click(r, href);
  click(r, "tel:+919909903449", { isTrusted: false });
  click(r, "tel:+919909903449", { defaultPrevented: true });
  click(r, "tel:+919909903449", { button: 2 });
  assert.deepEqual(r.calls, []);
});

for (const analytics of ["missing", "throws"]) {
  await test(`${analytics} analytics cannot break successful forms or navigation`, async () => {
    const r = runtime({ analytics }); const f = form(); r.responses.push(response());
    submit(r, f); await settle();
    assert.equal(f.done.style.display, "block");
    assert.equal(f.button.disabled, false);
    click(r, "tel:+919909903449");
    click(r, "https://wa.me/919909903449");
  });
}

function files(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    return entry.isDirectory() ? files(full) : [full];
  });
}

await test("all source templates have no legacy page-load conversion dispatches", () => {
  for (const file of files(path.join(root, "src")).filter((f) => f.endsWith(".html"))) {
    assert.doesNotMatch(fs.readFileSync(file, "utf8"), /Ka9bCKe4k4UDEPOn6aAB|kBaGCJj1zYEYEPOn6aAB|C1sMCO25hv0YEPOn6aAB|contact_us|ads_conversion_Contact_Us_1/, file);
  }
});

// --runtime-only permits behavior checks while a full production build is running.
// The default command always checks the complete generated output too.
if (!process.argv.includes("--runtime-only")) await test("every generated page keeps standard tags and executes zero inline enquiry events", () => {
  const pages = files(path.join(root, "dist")).filter((f) => f.endsWith(".html"));
  assert.equal(pages.length, 440);
  for (const file of pages) {
    const html = fs.readFileSync(file, "utf8");
    assert.equal((html.match(/src="\/js\/enquiry-tracking\.js"/g) || []).length, 1, file);
    assert.equal((html.match(/gtag\('config', 'G-KJGLGHF9XR'\)/g) || []).length, 1, file);
    assert.equal((html.match(/gtag\('config', 'AW-337269747'\)/g) || []).length, 1, file);
    assert.ok(html.includes("GTM-W87P4FV5"), file);
    assert.doesNotMatch(html, /1994474461275883|4646870475584513|fbevents\.js|\bfbq\s*\(|facebook\.com\/tr/, file);
    assert.doesNotMatch(html, /Ka9bCKe4k4UDEPOn6aAB|kBaGCJj1zYEYEPOn6aAB|C1sMCO25hv0YEPOn6aAB|contact_us|ads_conversion_Contact_Us_1/, file);
    if (html.includes('/js/forms.js')) assert.ok(html.indexOf('/js/enquiry-tracking.js') < html.indexOf('/js/forms.js'), file);
    const context = vm.createContext({ dataLayer: [] }); context.window = context;
    for (const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
      if (/\bgtag\s*\(/.test(match[1])) vm.runInContext(match[1], context);
    }
    assert.equal(context.dataLayer.filter((args) => args[0] === "event").length, 0, file);
  }
  console.log(`Checked all ${pages.length} generated pages`);
});

console.log(`${passed} conversion tracking regression checks passed; no external requests sent.`);
