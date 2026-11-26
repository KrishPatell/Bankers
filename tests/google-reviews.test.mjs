import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  CACHE_KEY,
  googleReviewsFeed,
  syncGoogleReviews,
} from "../api/google-reviews.js";

const fixture = JSON.parse(await readFile(new URL("./fixtures/google-reviews.json", import.meta.url), "utf8"));

function response(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

class MemoryKV {
  constructor() {
    this.values = new Map();
    this.putOptions = [];
  }

  async get(key) {
    return this.values.get(key) || null;
  }

  async put(key, value, options) {
    this.values.set(key, value);
    this.putOptions.push(options);
  }
}

function makeFetch(state) {
  return async (input, init = {}) => {
    const url = new URL(String(input));
    const authorization = init.headers?.Authorization || init.headers?.authorization || "";
    const token = authorization.replace(/^Bearer\s+/i, "");
    if (authorization) {
      state.tokens ||= new Set();
      state.tokens.add(token);
    }
    if (url.hostname === "mybusinessaccountmanagement.googleapis.com" && url.pathname === "/v1/accounts") {
      return response({ accounts: structuredClone(fixture.accounts) });
    }
    if (url.hostname === "mybusinessbusinessinformation.googleapis.com" && url.pathname === "/v1/accounts/100/locations") {
      const locations = state.visibleLocationsByToken?.[token] || fixture.locations;
      return response({ locations: structuredClone(locations) });
    }
    if (url.hostname === "mybusiness.googleapis.com" && url.pathname.endsWith("/reviews")) {
      const locationKey = url.pathname.includes("/ahmedabad-satellite/")
        ? "locations/ahmedabad-satellite"
        : "locations/vadodara-akota";
      if (state.failVadodara && locationKey === "locations/vadodara-akota") return response({ error: "fixture failure" }, 503);
      return response({ reviews: structuredClone(state.reviews[locationKey]) });
    }
    throw new Error(`Unexpected fixture request: ${url}`);
  };
}

function env(cache) {
  return {
    GOOGLE_BUSINESS_PROFILE_ACCESS_TOKEN: "fixture-access-token",
    GOOGLE_REVIEWS_CACHE: cache,
  };
}

test("syncs both verified branch fixtures, keeps only five-star reviews, and deduplicates IDs", async () => {
  const cache = new MemoryKV();
  const state = { reviews: structuredClone(fixture.reviews), failVadodara: false };
  const result = await syncGoogleReviews(env(cache), {
    fetchImpl: makeFetch(state),
    now: () => new Date("2026-11-26T12:00:00Z"),
  });

  assert.equal(result.ok, true);
  assert.deepEqual(result.counts, { ahmedabad: 5, vadodara: 1 });
  assert.equal(result.feed.locations.length, 2);
  assert.equal(result.feed.locations[0].locationId, "ahmedabad-satellite");
  assert.equal(result.feed.locations[1].locationId, "vadodara-akota");
  assert.match(result.feed.locations[0].address, /Ahmedabad/);
  assert.match(result.feed.locations[1].address, /Akota/);
  assert.deepEqual(result.feed.reviews.map((review) => review.id), [
    "vad-five",
    "ahm-newest",
    "ahm-edited",
    "ahm-rating-only",
  ]);
  assert.equal(result.feed.reviews.filter((review) => review.id === "ahm-edited").length, 1);
  assert.equal(result.feed.reviews.some((review) => review.id === "ahm-four"), false);
  assert.equal(result.feed.reviews.find((review) => review.id === "ahm-rating-only").comment, null);
  assert.equal(cache.putOptions[0].expirationTtl, 30 * 24 * 60 * 60);
});

test("applies new and edited reviews and removes a deleted review on the next complete sync", async () => {
  const cache = new MemoryKV();
  const state = { reviews: structuredClone(fixture.reviews), failVadodara: false };
  const first = await syncGoogleReviews(env(cache), { fetchImpl: makeFetch(state) });
  assert.equal(first.ok, true);

  state.reviews["locations/ahmedabad-satellite"] = state.reviews["locations/ahmedabad-satellite"]
    .filter((review) => review.reviewId !== "ahm-rating-only")
    .map((review) => {
      if (review.reviewId === "ahm-edited" && review.updateTime === "2026-11-26T08:00:00Z") {
        return { ...review, comment: "The edited Google review is now visible." };
      }
      if (review.reviewId === "ahm-newest") return { ...review, starRating: "FOUR" };
      return review;
    });
  state.reviews["locations/vadodara-akota"].push({
    reviewId: "vad-new",
    starRating: "FIVE",
    createTime: "2026-11-26T13:00:00Z",
    updateTime: "2026-11-26T13:00:00Z",
    reviewer: { displayName: "New Vadodara Patient" },
    comment: "A new five-star fixture review.",
  });

  const second = await syncGoogleReviews(env(cache), { fetchImpl: makeFetch(state) });
  assert.equal(second.ok, true);
  assert.equal(second.feed.reviews.some((review) => review.id === "ahm-rating-only"), false);
  assert.equal(second.feed.reviews.some((review) => review.id === "ahm-newest"), false);
  assert.equal(second.feed.reviews.find((review) => review.id === "ahm-edited").comment, "The edited Google review is now visible.");
  assert.equal(second.feed.reviews.some((review) => review.id === "vad-new"), true);
});

test("preserves the last complete feed when one branch fails", async () => {
  const cache = new MemoryKV();
  const state = { reviews: structuredClone(fixture.reviews), failVadodara: false };
  const first = await syncGoogleReviews(env(cache), { fetchImpl: makeFetch(state) });
  const previous = await cache.get(CACHE_KEY);
  assert.equal(first.ok, true);

  state.failVadodara = true;
  state.reviews["locations/ahmedabad-satellite"] = [];
  const originalConsoleError = console.error;
  console.error = () => {};
  let failed;
  try {
    failed = await syncGoogleReviews(env(cache), { fetchImpl: makeFetch(state) });
  } finally {
    console.error = originalConsoleError;
  }
  assert.equal(failed.ok, false);
  assert.equal(failed.preserved, true);
  assert.equal(await cache.get(CACHE_KEY), previous);
});

test("serves the cached feed to the homepage API and rejects writes", async () => {
  const cache = new MemoryKV();
  const state = { reviews: structuredClone(fixture.reviews), failVadodara: false };
  await syncGoogleReviews(env(cache), { fetchImpl: makeFetch(state) });

  const getResponse = await googleReviewsFeed(new Request("https://bankersvascular.com/api/google-reviews"), env(cache));
  assert.equal(getResponse.status, 200);
  assert.equal((await getResponse.json()).reviews.length, 4);

  const postResponse = await googleReviewsFeed(new Request("https://bankersvascular.com/api/google-reviews", { method: "POST" }), env(cache));
  assert.equal(postResponse.status, 405);
});

test("supports separate branch authorizations when one account cannot access both locations", async () => {
  const cache = new MemoryKV();
  const state = { reviews: structuredClone(fixture.reviews), failVadodara: false };
  const result = await syncGoogleReviews({
    GOOGLE_BUSINESS_PROFILE_AHMEDABAD_ACCESS_TOKEN: "ahmedabad-fixture-token",
    GOOGLE_BUSINESS_PROFILE_VADODARA_ACCESS_TOKEN: "vadodara-fixture-token",
    GOOGLE_REVIEWS_CACHE: cache,
  }, {
    fetchImpl: makeFetch(state),
  });

  assert.equal(result.ok, true);
  assert.deepEqual([...state.tokens].sort(), ["ahmedabad-fixture-token", "vadodara-fixture-token"]);
  assert.equal(result.feed.locations.length, 2);
  assert.equal(result.feed.reviews.length, 4);
});

test("can combine a generic authorization with a branch-specific authorization", async () => {
  const cache = new MemoryKV();
  const state = {
    reviews: structuredClone(fixture.reviews),
    failVadodara: false,
    visibleLocationsByToken: {
      "limited-generic-token": fixture.locations.filter((location) => location.name === "locations/vadodara-akota"),
    },
  };
  const result = await syncGoogleReviews({
    GOOGLE_BUSINESS_PROFILE_ACCESS_TOKEN: "limited-generic-token",
    GOOGLE_BUSINESS_PROFILE_AHMEDABAD_ACCESS_TOKEN: "ahmedabad-fixture-token",
    GOOGLE_REVIEWS_CACHE: cache,
  }, {
    fetchImpl: makeFetch(state),
  });

  assert.equal(result.ok, true);
  assert.deepEqual([...state.tokens].sort(), ["ahmedabad-fixture-token", "limited-generic-token"]);
  assert.equal(result.feed.locations[0].locationId, "ahmedabad-satellite");
  assert.equal(result.feed.locations[1].locationId, "vadodara-akota");
});
