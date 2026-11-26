const ACCOUNT_MANAGEMENT_API = "https://mybusinessaccountmanagement.googleapis.com/v1";
const BUSINESS_INFORMATION_API = "https://mybusinessbusinessinformation.googleapis.com/v1";
const REVIEWS_API = "https://mybusiness.googleapis.com/v4";
const OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token";
const BUSINESS_MANAGE_SCOPE = "https://www.googleapis.com/auth/business.manage";
const CACHE_KEY = "google-reviews-feed-v1";
const CACHE_TTL_SECONDS = 30 * 24 * 60 * 60;
export const SYNC_INTERVAL_MINUTES = 30;

// These are matching rules for the two known Bankers branches, not Google
// location IDs. IDs are always discovered from the authorized GBP account and
// are only accepted after the returned address matches these branch rules.
export const BRANCHES = [
  {
    key: "ahmedabad",
    label: "Ahmedabad · Satellite",
    city: "Ahmedabad",
    postalCode: "380015",
    addressSignals: [["anand", "nagar"], ["satellite"], ["rjp", "house"]],
  },
  {
    key: "vadodara",
    label: "Vadodara · Akota",
    city: "Vadodara",
    postalCode: "390007",
    addressSignals: [["akota"], ["ignite", "complex"], ["agrawal", "cars"]],
  },
];

const LOCATION_READ_MASK = "name,title,storefrontAddress,metadata";

function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...headers,
    },
  });
}

function normalizeText(value) {
  return String(value ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function addressParts(location) {
  const address = location?.storefrontAddress || location?.address || {};
  return [
    location?.title,
    location?.locationName,
    ...asArray(address.addressLines),
    address.locality,
    address.administrativeArea,
    address.postalCode,
    address.regionCode,
  ].filter(Boolean);
}

export function locationAddressText(location) {
  return addressParts(location).join(", ");
}

function addressMatches(location, branch) {
  const normalized = normalizeText(addressParts(location).join(" "));
  const city = normalizeText(branch.city);
  const postalCode = normalizeText(branch.postalCode);
  const hasCity = normalized.includes(city);
  const hasPostalCode = normalized.includes(postalCode);
  const hasAddressSignal = branch.addressSignals.some((signal) => (
    signal.every((part) => normalized.includes(normalizeText(part)))
  ));
  return hasCity && hasPostalCode && hasAddressSignal;
}

function locationId(locationName) {
  const value = String(locationName || "");
  return value.startsWith("locations/") ? value.slice("locations/".length) : "";
}

function accountId(accountName) {
  const value = String(accountName || "");
  return value.startsWith("accounts/") ? value.slice("accounts/".length) : "";
}

function mapsUrlFromLocation(location) {
  const metadata = location?.metadata || {};
  const value = metadata.mapsUri || metadata.mapsUrl || metadata.mapsURL || "";
  if (!value) return "";
  try {
    const url = new URL(value);
    const hostname = url.hostname.toLowerCase();
    const isGoogleHost = hostname === "google.com" || hostname.endsWith(".google.com");
    if (url.protocol !== "https:" || !isGoogleHost) return "";
    return url.toString();
  } catch {
    return "";
  }
}

function placeIdFromLocation(location) {
  const metadata = location?.metadata || {};
  return metadata.placeId || metadata.place_id || "";
}

function branchLocation(branch, location) {
  const locationName = String(location.name || "");
  const id = locationId(locationName);
  const accountName = String(location.accountName || "");
  const account = accountId(accountName);
  const mapsUrl = mapsUrlFromLocation(location);
  if (!id || !account || !mapsUrl) return null;
  return {
    key: branch.key,
    label: branch.label,
    accountName,
    accountId: account,
    locationName,
    locationId: id,
    address: locationAddressText(location),
    placeId: placeIdFromLocation(location),
    mapsUrl,
  };
}

class GoogleReviewsError extends Error {
  constructor(message, status = 502) {
    super(message);
    this.name = "GoogleReviewsError";
    this.status = status;
  }
}

async function readResponseBody(response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text.slice(0, 200) };
  }
}

async function googleJson(fetchImpl, url, accessToken, init = {}) {
  const response = await fetchImpl(url, {
    ...init,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(init.headers || {}),
    },
  });
  const body = await readResponseBody(response);
  if (!response.ok) {
    throw new GoogleReviewsError(`Google Business Profile API returned ${response.status}`, response.status);
  }
  return body;
}

async function accessToken(env, fetchImpl) {
  if (env.GOOGLE_BUSINESS_PROFILE_ACCESS_TOKEN) {
    return env.GOOGLE_BUSINESS_PROFILE_ACCESS_TOKEN;
  }

  const clientId = env.GOOGLE_BUSINESS_PROFILE_CLIENT_ID;
  const clientSecret = env.GOOGLE_BUSINESS_PROFILE_CLIENT_SECRET;
  const refreshToken = env.GOOGLE_BUSINESS_PROFILE_REFRESH_TOKEN;
  if (!clientId || !clientSecret || !refreshToken) {
    throw new GoogleReviewsError("Google Business Profile OAuth credentials are not configured", 503);
  }

  const response = await fetchImpl(OAUTH_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      refresh_token: refreshToken,
      grant_type: "refresh_token",
      scope: BUSINESS_MANAGE_SCOPE,
    }).toString(),
  });
  const body = await readResponseBody(response);
  if (!response.ok || !body.access_token) {
    throw new GoogleReviewsError(`Google OAuth token refresh returned ${response.status}`, response.status || 502);
  }
  return body.access_token;
}

async function listAccounts(fetchImpl, token) {
  const accounts = [];
  let pageToken = "";
  do {
    const url = new URL(`${ACCOUNT_MANAGEMENT_API}/accounts`);
    url.searchParams.set("pageSize", "100");
    if (pageToken) url.searchParams.set("pageToken", pageToken);
    const body = await googleJson(fetchImpl, url, token);
    accounts.push(...asArray(body.accounts));
    pageToken = body.nextPageToken || "";
  } while (pageToken);
  return accounts;
}

async function listLocations(fetchImpl, token, account) {
  const accountName = String(account.name || "");
  if (!accountName.startsWith("accounts/")) return [];
  const locations = [];
  let pageToken = "";
  do {
    const url = new URL(`${BUSINESS_INFORMATION_API}/${accountName}/locations`);
    url.searchParams.set("readMask", LOCATION_READ_MASK);
    url.searchParams.set("pageSize", "100");
    if (pageToken) url.searchParams.set("pageToken", pageToken);
    const body = await googleJson(fetchImpl, url, token);
    locations.push(...asArray(body.locations).map((location) => ({
      ...location,
      accountName,
    })));
    pageToken = body.nextPageToken || "";
  } while (pageToken);
  return locations;
}

export async function resolveAuthorizedLocations(fetchImpl, token) {
  const accounts = await listAccounts(fetchImpl, token);
  if (!accounts.length) throw new GoogleReviewsError("The authorized Google account has no Business Profile accounts", 404);

  const allLocations = new Map();
  for (const account of accounts) {
    const locations = await listLocations(fetchImpl, token, account);
    for (const location of locations) {
      if (location.name && !allLocations.has(location.name)) allLocations.set(location.name, location);
    }
  }

  const resolved = {};
  for (const branch of BRANCHES) {
    const matches = [...allLocations.values()].filter((location) => addressMatches(location, branch));
    if (matches.length !== 1) {
      throw new GoogleReviewsError(
        `${branch.label} location could not be uniquely verified from the authorized account (${matches.length} address matches)`,
        409,
      );
    }
    const resolvedLocation = branchLocation(branch, matches[0]);
    if (!resolvedLocation) {
      throw new GoogleReviewsError(`${branch.label} is missing a verified Maps URL or location ID`, 409);
    }
    resolved[branch.key] = resolvedLocation;
  }
  return resolved;
}

async function listReviews(fetchImpl, token, location) {
  const reviews = [];
  let pageToken = "";
  do {
    const url = new URL(`${REVIEWS_API}/${location.accountName}/locations/${location.locationId}/reviews`);
    url.searchParams.set("pageSize", "50");
    url.searchParams.set("orderBy", "updateTime desc");
    if (pageToken) url.searchParams.set("pageToken", pageToken);
    const body = await googleJson(fetchImpl, url, token);
    reviews.push(...asArray(body.reviews));
    pageToken = body.nextPageToken || "";
  } while (pageToken);
  return reviews;
}

function ratingNumber(value) {
  if (typeof value === "number") return value;
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return numeric;
  return {
    ONE: 1,
    TWO: 2,
    THREE: 3,
    FOUR: 4,
    FIVE: 5,
  }[String(value || "").toUpperCase()] || 0;
}

function timestamp(value) {
  const parsed = Date.parse(value || "");
  return Number.isFinite(parsed) ? parsed : 0;
}

export function normalizeReview(review, location) {
  if (ratingNumber(review?.starRating) !== 5) return null;
  const reviewName = String(review?.name || "");
  const id = String(review?.reviewId || reviewName.split("/").pop() || "");
  if (!id) return null;
  const author = String(review?.reviewer?.displayName || "Google reviewer").trim() || "Google reviewer";
  const comment = String(review?.comment || "").trim();
  return {
    id,
    locationId: location.locationId,
    branch: location.key,
    branchLabel: location.label,
    author,
    profilePhotoUrl: String(review?.reviewer?.profilePhotoUrl || "") || null,
    rating: 5,
    comment: comment || null,
    createdAt: review?.createTime || review?.updateTime || null,
    updatedAt: review?.updateTime || review?.createTime || null,
    reviewUrl: location.mapsUrl,
  };
}

function deduplicateReviews(reviews) {
  const unique = new Map();
  for (const review of reviews) {
    const key = `${review.locationId}:${review.id}`;
    const previous = unique.get(key);
    if (!previous || timestamp(review.updatedAt) >= timestamp(previous.updatedAt)) unique.set(key, review);
  }
  return [...unique.values()].sort((a, b) => (
    timestamp(b.createdAt || b.updatedAt) - timestamp(a.createdAt || a.updatedAt)
  ));
}

function publicLocation(location) {
  return {
    key: location.key,
    label: location.label,
    locationId: location.locationId,
    address: location.address,
    placeId: location.placeId || null,
    mapsUrl: location.mapsUrl,
  };
}

async function writeFeed(env, feed) {
  if (!env.GOOGLE_REVIEWS_CACHE || typeof env.GOOGLE_REVIEWS_CACHE.put !== "function") {
    throw new GoogleReviewsError("GOOGLE_REVIEWS_CACHE KV binding is not configured", 503);
  }
  await env.GOOGLE_REVIEWS_CACHE.put(CACHE_KEY, JSON.stringify(feed), {
    expirationTtl: CACHE_TTL_SECONDS,
  });
}

async function readFeed(env) {
  if (!env.GOOGLE_REVIEWS_CACHE || typeof env.GOOGLE_REVIEWS_CACHE.get !== "function") return null;
  const value = await env.GOOGLE_REVIEWS_CACHE.get(CACHE_KEY);
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

export async function syncGoogleReviews(env, options = {}) {
  const fetchImpl = options.fetchImpl || fetch;
  const now = options.now || (() => new Date());
  try {
    const token = await accessToken(env, fetchImpl);
    const locations = await resolveAuthorizedLocations(fetchImpl, token);
    const fetched = await Promise.all(BRANCHES.map(async (branch) => ({
      branch,
      location: locations[branch.key],
      reviews: await listReviews(fetchImpl, token, locations[branch.key]),
    })));
    const normalized = fetched.flatMap(({ location, reviews }) => (
      reviews.map((review) => normalizeReview(review, location)).filter(Boolean)
    ));
    const feed = {
      version: 1,
      source: "google-business-profile",
      syncedAt: now().toISOString(),
      refreshIntervalMinutes: SYNC_INTERVAL_MINUTES,
      locations: BRANCHES.map((branch) => publicLocation(locations[branch.key])),
      reviews: deduplicateReviews(normalized),
    };
    await writeFeed(env, feed);
    return {
      ok: true,
      feed,
      counts: Object.fromEntries(fetched.map(({ branch, reviews }) => [branch.key, reviews.length])),
    };
  } catch (error) {
    // Do not write an empty or partial feed. The previously successful cache
    // remains available until a complete reconciliation succeeds.
    console.error("syncGoogleReviews:", error);
    return {
      ok: false,
      preserved: true,
      error: error instanceof GoogleReviewsError ? error.message : "Google review sync failed",
    };
  }
}

export async function googleReviewsFeed(request, env) {
  if (request.method !== "GET") {
    return json({ ok: false, error: "Method not allowed" }, 405, { Allow: "GET" });
  }
  try {
    const feed = await readFeed(env);
    if (!feed) {
      return json({ ok: false, error: "Google review feed is not ready yet.", reviews: [], locations: [] }, 503, {
        "Cache-Control": "no-store",
      });
    }
    return json({ ok: true, ...feed }, 200, {
      "Cache-Control": "public, max-age=300, s-maxage=1800, stale-while-revalidate=1800",
    });
  } catch (error) {
    console.error("googleReviewsFeed:", error);
    return json({ ok: false, error: "Could not load Google reviews right now.", reviews: [], locations: [] }, 502, {
      "Cache-Control": "no-store",
    });
  }
}

export { CACHE_KEY, CACHE_TTL_SECONDS, BUSINESS_MANAGE_SCOPE };
