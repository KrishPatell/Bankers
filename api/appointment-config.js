// Server-side allowlists for the appointment form. The client-facing schedule
// dates live in src/data/appointment-config.json so the marketing team can
// update active OPD locations and dates without changing form logic.
export const APPOINTMENT_CITIES = Object.freeze([
  "Ahmedabad",
  "Vadodara",
  "Rajkot",
  "Surat",
  "Jamnagar",
  "Bhavnagar",
  "Mehsana",
  "Anand",
  "Gandhinagar",
  "Surendranagar",
  "Bharuch",
  "Junagadh",
  "Himatnagar",
  "Palanpur",
  "Nadiad",
  "Other City",
]);

export const APPOINTMENT_DISEASES = Object.freeze([
  "Knee Pain",
  "Varicose Veins",
  "Prostate Enlargement",
  "Piles",
  "Heel Pain",
  "Frozen Shoulder",
  "Breast Fibroadenoma",
  "Obesity",
  "Hair Fall",
  "Lymphedema",
  "Tennis Elbow / Golfer’s Elbow",
  "Vascular Malformation",
  "Carpal Tunnel Syndrome",
  "Other Health Condition",
]);

export function isAppointmentPayload(body) {
  return String(body?._appointment || "").toLowerCase() === "true";
}

export function isChecked(value) {
  return ["1", "true", "on", "yes"].includes(String(value || "").toLowerCase());
}

export function indianMobileDigits(value) {
  const text = String(value || "").trim();
  if (!/^(?:\+91[\s-]?|91[\s-]?)?[6-9]\d{9}$/.test(text)) return "";
  const digits = text.replace(/\D/g, "");
  if (digits.length === 12 && digits.startsWith("91")) return digits.slice(2);
  return digits;
}

export function isFutureOrToday(value) {
  const text = String(value || "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
  const [year, month, day] = text.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return false;
  const todayParts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date()).reduce((result, part) => {
    if (part.type !== "literal") result[part.type] = part.value;
    return result;
  }, {});
  return text >= `${todayParts.year}-${todayParts.month}-${todayParts.day}`;
}

export function claimRequest(requests, id, now = Date.now(), windowMs = 600000) {
  const key = String(id || "").trim();
  if (!key || key.length > 128) return false;
  for (const [stored, timestamp] of requests) {
    if (now - timestamp >= windowMs) requests.delete(stored);
  }
  if (requests.has(key)) return true;
  requests.set(key, now);
  if (requests.size > 10000) requests.clear();
  return false;
}

export function releaseRequest(requests, id) {
  const key = String(id || "").trim();
  if (key) requests.delete(key);
}
