import { execFile } from "node:child_process";
import { appendFile, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { promisify } from "node:util";
import { pathToFileURL } from "node:url";
import {
  BRANCHES,
  CACHE_KEY,
  CACHE_TTL_SECONDS,
  syncGoogleReviews,
} from "../api/google-reviews.js";

const execFileAsync = promisify(execFile);
const WRANGLER_PACKAGE = process.env.WRANGLER_PACKAGE || "wrangler@latest";

class CaptureKV {
  constructor() {
    this.value = null;
    this.options = null;
  }

  async put(key, value, options) {
    if (key !== CACHE_KEY) throw new Error(`Unexpected review cache key: ${key}`);
    this.value = value;
    this.options = options;
  }
}

function credentialSet(env, branchKey = "") {
  const suffix = branchKey ? `_${branchKey.toUpperCase()}` : "";
  const accessToken = env[`GOOGLE_BUSINESS_PROFILE${suffix}_ACCESS_TOKEN`];
  const clientId = env[`GOOGLE_BUSINESS_PROFILE${suffix}_CLIENT_ID`];
  const clientSecret = env[`GOOGLE_BUSINESS_PROFILE${suffix}_CLIENT_SECRET`];
  const refreshToken = env[`GOOGLE_BUSINESS_PROFILE${suffix}_REFRESH_TOKEN`];
  return Boolean(accessToken || (clientId && clientSecret && refreshToken));
}

function assertGoogleCredentials(env) {
  if (credentialSet(env) || BRANCHES.every((branch) => credentialSet(env, branch.key))) return;
  throw new Error(
    "Google Business Profile credentials are missing. Configure the generic OAuth trio "
    + "or complete credential sets for both branch-specific authorizations.",
  );
}

function assertCloudflareCredentials(env) {
  const missing = [
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_KV_NAMESPACE_ID",
  ].filter((name) => !env[name]);
  if (missing.length) throw new Error(`Cloudflare secrets are missing: ${missing.join(", ")}`);
}

function verifyFeed(feed) {
  if (!feed || feed.version !== 1 || feed.source !== "google-business-profile") {
    throw new Error("Sync did not produce a valid Google Business Profile feed");
  }
  if (!Array.isArray(feed.locations) || !Array.isArray(feed.reviews)) {
    throw new Error("Sync produced an incomplete Google review feed");
  }
  for (const branch of BRANCHES) {
    const location = feed.locations.find((candidate) => candidate.key === branch.key);
    if (!location?.locationId || !location.mapsUrl || !location.address) {
      throw new Error(`${branch.label} location ID, address, or Maps URL was not verified`);
    }
  }
  if (feed.reviews.some((review) => review.rating !== 5)) {
    throw new Error("Sync produced a non-five-star review");
  }
}

async function writeSummary(feed, mode) {
  const summaryPath = process.env.GITHUB_STEP_SUMMARY;
  if (!summaryPath) return;
  const locationLines = feed.locations.map((location) => (
    `- ${location.label}: location ID \`${location.locationId}\`; address verified as ${location.address}`
  ));
  const summary = [
    "## Google Reviews sync",
    "",
    `- Mode: ${mode}`,
    `- Synced at: ${feed.syncedAt}`,
    `- Eligible five-star reviews: ${feed.reviews.length}`,
    `- Cache key: \`${CACHE_KEY}\``,
    ...locationLines,
    "",
  ].join("\n");
  await appendFile(summaryPath, summary, "utf8");
}

async function runWrangler(args, env) {
  const executable = process.platform === "win32" ? "npx.cmd" : "npx";
  const result = await execFileAsync(
    executable,
    ["--yes", WRANGLER_PACKAGE, ...args],
    {
      env: {
        ...env,
        CLOUDFLARE_API_TOKEN: env.CLOUDFLARE_API_TOKEN,
        CLOUDFLARE_ACCOUNT_ID: env.CLOUDFLARE_ACCOUNT_ID,
      },
      maxBuffer: 1024 * 1024,
    },
  );
  return result.stdout;
}

async function publishFeed(feed, env) {
  assertCloudflareCredentials(env);
  const directory = await mkdtemp(join(tmpdir(), "bankers-google-reviews-"));
  const payloadPath = join(directory, `${basename(CACHE_KEY)}.json`);
  try {
    await writeFile(payloadPath, JSON.stringify(feed), "utf8");
    await runWrangler([
      "kv",
      "key",
      "put",
      CACHE_KEY,
      "--namespace-id",
      env.CLOUDFLARE_KV_NAMESPACE_ID,
      "--remote",
      "--path",
      payloadPath,
      "--expiration-ttl",
      String(CACHE_TTL_SECONDS),
    ], env);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

export async function syncAndPublish(env = process.env, { dryRun = false } = {}) {
  assertGoogleCredentials(env);
  const capture = new CaptureKV();
  const result = await syncGoogleReviews({
    ...env,
    GOOGLE_REVIEWS_CACHE: capture,
  });
  if (!result.ok || !capture.value) {
    throw new Error(result.error || "Google review sync failed");
  }

  const feed = JSON.parse(capture.value);
  verifyFeed(feed);
  if (!dryRun) await publishFeed(feed, env);
  await writeSummary(feed, dryRun ? "dry-run; KV write skipped" : "published to production KV");
  return { feed, cacheOptions: capture.options, published: !dryRun };
}

async function main() {
  const args = new Set(process.argv.slice(2));
  if (args.has("--help")) {
    console.log("Usage: node scripts/sync-google-reviews.mjs [--dry-run]");
    return;
  }
  const dryRun = args.has("--dry-run");
  const result = await syncAndPublish(process.env, { dryRun });
  const mode = result.published ? "published to production KV" : "dry-run; KV write skipped";
  console.log(`Google Reviews sync complete: ${result.feed.reviews.length} eligible reviews; ${mode}.`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(`Google Reviews sync failed: ${error.message}`);
    process.exitCode = 1;
  });
}
