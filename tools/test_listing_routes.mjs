import assert from "node:assert/strict";
import worker from "../worker.js";

const listings = ["/blog", "/departments", "/bankers-notes", "/services-gujarat"];
const assetRequests = [];
const env = {
  ASSETS: {
    async fetch(request) {
      assetRequests.push(request);
      const path = new URL(request.url).pathname;
      return new Response("listing", {
        status: path.endsWith("/") ? 200 : 307,
        headers: { "Content-Type": "text/html" },
      });
    },
  },
};

for (const path of listings) {
  for (const method of ["GET", "HEAD"]) {
    const response = await worker.fetch(new Request(`https://bankersvascular.com${path}`, { method }), env);
    assert.equal(response.status, 200, `${method} ${path} must bypass the asset redirect`);
    const assetRequest = assetRequests.at(-1);
    assert.equal(new URL(assetRequest.url).pathname, `${path}/`);
    assert.equal(assetRequest.method, method);
  }

  const slash = await worker.fetch(new Request(`https://bankersvascular.com${path}/`), env);
  assert.equal(slash.status, 301, `${path}/ must not be a second indexable copy`);
  assert.equal(slash.headers.get("Location"), `https://bankersvascular.com${path}`);

  const withQuery = await worker.fetch(new Request(`https://bankersvascular.com${path}?source=test`), env);
  assert.equal(withQuery.status, 200);
  assert.equal(new URL(assetRequests.at(-1).url).search, "?source=test");
}

const products = await worker.fetch(new Request("https://bankersvascular.com/products"), env);
assert.equal(products.status, 200);
assert.equal(new URL(assetRequests.at(-1).url).pathname, "/products/");

for (const [path, destination] of [
  ["/knee-pain", "/departments/knee-pain"],
  ["/departments/varicose-vein", "/departments/varicose-veins"],
]) {
  const response = await worker.fetch(new Request(`https://bankersvascular.com${path}`), env);
  assert.equal(response.status, 301);
  assert.equal(response.headers.get("Location"), `https://bankersvascular.com${destination}`);
}

for (const origin of ["http://bankersvascular.com", "https://www.bankersvascular.com"]) {
  const response = await worker.fetch(new Request(`${origin}/blog`), env);
  assert.equal(response.status, 301);
  assert.equal(response.headers.get("Location"), "https://bankersvascular.com/blog");
}

const unrelatedSlash = await worker.fetch(new Request("https://bankersvascular.com/departments/knee-pain/"), env);
assert.equal(unrelatedSlash.status, 200);
assert.equal(new URL(assetRequests.at(-1).url).pathname, "/departments/knee-pain/");

console.log("canonical listing Worker routes passed (four listings, variants, legacy redirects, origin redirects)");
