// No network or API calls: execute the real Worker with a filesystem asset binding.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import worker from "../worker.js";

const root = fileURLToPath(new URL("../", import.meta.url));
const dist = path.join(root, "dist");
const origin = "https://bankersvascular.com";
const config = JSON.parse(fs.readFileSync(path.join(root, "wrangler.jsonc"), "utf8"));
assert.equal(config.assets.html_handling, "drop-trailing-slash");
assert.equal(config.assets.run_worker_first, true);

function assetExists(urlPath) {
  const rel = urlPath === "/" ? "index.html" : urlPath.slice(1);
  return [rel, `${rel}.html`, `${rel}/index.html`].some((name) => {
    const file = path.resolve(dist, name);
    return file.startsWith(dist + path.sep) && fs.existsSync(file) && fs.statSync(file).isFile();
  });
}

const filesystemAssets = {
  ASSETS: {
    async fetch(request) {
      return new Response("local asset", {
        status: assetExists(new URL(request.url).pathname) ? 200 : 404,
      });
    },
  },
};

for (const [source, destination] of [
  ["/departments/platelet-rich-plasma", "/treatment/platelet-rich-plasma"],
  ["/departments/varicose-vein", "/departments/varicose-veins"],
]) {
  for (const method of ["GET", "HEAD"]) {
    let consultedAssets = false;
    const response = await worker.fetch(new Request(origin + source, { method }), {
      ASSETS: { fetch() { consultedAssets = true; throw new Error("Expected Worker-owned redirect"); } },
    });
    assert.equal(consultedAssets, false);
    assert.equal(response.status, 301, source);
    assert.equal(response.headers.get("Location"), origin + destination, source);
    assert.notEqual(source, destination);
    assert.ok(assetExists(destination), `${destination} must exist in dist`);
    const target = await worker.fetch(new Request(response.headers.get("Location"), { method }), filesystemAssets);
    assert.equal(target.status, 200, `${source} must land in one hop`);
    assert.equal(target.headers.get("Location"), null, "no redirect chain/loop");
  }
}

// These aliases are owned by Cloudflare's asset HTML handling, not worker.js.
// Prove delegation and config here; smoke.py checks their actual edge responses.
for (const [source, destination] of [["/blog.html", "/blog"], ["/index.html", "/"]]) {
  let delegatedPath;
  const response = await worker.fetch(new Request(origin + source), {
    ASSETS: { async fetch(request) {
      delegatedPath = new URL(request.url).pathname;
      return new Response("asset binding sentinel", { status: 418 });
    } },
  });
  assert.equal(delegatedPath, source);
  assert.equal(response.status, 418, "Worker must preserve the asset binding response");
  assert.ok(assetExists(destination), destination);
}

console.log(JSON.stringify({ worker_redirects: 2, asset_delegations: 2 }));
