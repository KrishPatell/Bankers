# Bankers Vascular — build & deploy

This repo holds the **Webflow static export** in `src/` (the source templates)
plus a generator that fills it with the CMS data from `cms/*.csv` and writes a
deployable site into `dist/`.

```
src/     the untouched Webflow export — templates, css, js, images, fonts
cms/     the CSV collection exports
tools/   the generator and its checks
api/     the form endpoint (Vercel reads this from the repo root)
dist/    generated; gitignored; what actually gets served
```

**Never edit `dist/` by hand** — it is deleted and rebuilt on every run. Edit the
templates in `src/`, or the config in `tools/wfconfig.py`.

The export deliberately lives in `src/` and **not** at the repository root. A
root containing a ready-looking `index.html` is a trap: point a host at it and it
will serve the *unbound* templates — empty collection lists, "No items found."
on every section — and the deploy will look successful. That is exactly what
happened once (see below). With the export under `src/`, that misconfiguration
404s instead. `tools/verify.py` fails the build if an `index.html` ever
reappears at the root.

## Build

```bash
python tools/build.py                 # full build, downloads CMS images on first run
python tools/build.py --skip-assets   # fast rebuild (~20s), reuses src/images/cms/
python tools/verify.py                # production checks; exits non-zero on failure
python tools/serve.py 3111            # preview dist/ the way Vercel serves it
```

Or via npm: `npm run build` / `build:fast` / `verify` / `serve`.

Requires Python 3.8+ and no third-party packages.

`tools/serve.py` applies the `vercel.json` rules that decide whether a URL
resolves — `cleanUrls`, `trailingSlash`, and the redirect table — so a page that
works there works on Vercel. It does not execute `api/contact.js`; use
`vercel dev` (needs an authenticated Vercel account) to exercise the form
endpoint locally.

The first build downloads ~1,466 CMS images into `src/images/cms/` (a few hundred MB).
They are cached, so later builds reuse them and take a few seconds. Any image
that fails to download keeps its original Webflow CDN URL and is listed in
`tools/asset-report.txt`.

## Deploy

Vercel builds this project **from the repo root** — push to `main` and it
deploys itself. `vercel.json` tells it everything it needs:

```jsonc
"buildCommand": "python3 tools/build.py",   // Python 3 is on Vercel's build image
"outputDirectory": "dist"                   // where the generated site lands
```

### Vercel project settings

`vercel.json` overrides the dashboard for Build Command and Output Directory, but
**Root Directory is dashboard-only and cannot be set from `vercel.json`**. Get
these right:

| Setting | Value |
|---|---|
| Root Directory | **empty** (the repository root) — *not* `dist` |
| Build Command | blank — `vercel.json` supplies `python3 tools/build.py` |
| Output Directory | blank — `vercel.json` supplies `dist` |
| Install Command | blank |

If any field was overridden in the dashboard, clear the override so
`vercel.json` governs. Do **not** set Root Directory to `dist`: it is gitignored
so it is not in the checkout, and `api/`, `package.json` and `vercel.json` all
live at the repository root — pointing Vercel at `dist` loses the form endpoint.

### After every deploy, run the smoke test

```bash
python tools/smoke.py https://your-deployment.vercel.app
```

`tools/verify.py` inspects `dist/` on disk and **cannot** catch a deployment that
publishes the wrong directory — it passed all its checks while production was
serving the raw export. `smoke.py` fetches the live URL and asserts the built
site is what is being served: 9 doctors, 12 departments, zero "No items found",
the CMS item pages reachable, pagination and redirects working, and
`/api/contact` deployed. Treat a deploy as unverified until it passes.

```bash
npx vercel            # preview deploy
npx vercel --prod     # production
```

### Every deploy re-downloads the CMS images

There is no build cache for `src/images/cms/`, so each CI build fetches all ~1,466
assets from Webflow's CDN again. In practice that takes about 15 seconds from
Vercel's build region. If the CDN throttles (it answers **403**, not 429, when it
decides you are asking too fast), `tools/assets.py` retries with backoff and then
falls back to leaving that image on the CDN URL — so a bad patch degrades a few
images to remote loads rather than failing the deploy.

### Required environment variables

The contact/appointment forms POST to `/api/contact`, which emails submissions
via [Resend](https://resend.com). Set these in the Vercel project:

| Variable | Required | Purpose |
|---|---|---|
| `RESEND_API_KEY` | yes | Resend API key |
| `CONTACT_TO_EMAIL` | yes | Where enquiries are delivered (comma-separate for several) |
| `CONTACT_FROM_EMAIL` | no | Verified sender; defaults to `onboarding@resend.dev` |

**Until `RESEND_API_KEY` and `CONTACT_TO_EMAIL` are set, the endpoint returns
503 and each form shows its error message.** That is deliberate: a form must
never show "thank you" for an enquiry that was not delivered. Set them before
launch.

## How the generator works

| File | Role |
|---|---|
| `tools/build.py` | orchestration: shell pass, detail pass, sitemap, static copy |
| `tools/wfconfig.py` | **the file you will usually edit** — collections, field → CSS-class bindings, page lists |
| `tools/cmsdata.py` | CSV loading, publish rules, author/category joins |
| `tools/assets.py` | CMS asset localisation and repair of the export's broken image refs |
| `tools/wfhtml.py` | balanced-tag HTML surgery (no parser dependency) |
| `tools/verify.py` | post-build production checks |

A Webflow export ships every collection list as a single empty placeholder item.
The generator **clones that placeholder** and fills it by CSS class, which is why
all the Webflow classes, `data-w-id` attributes and scroll animations keep
working. Generated pages deliberately reuse their template's `data-wf-page` id —
`webflow.js` keys its interaction data off that, and many elements start at
`opacity:0`, so a mismatch would leave sections invisible.

## Publish rules

```
publish = Archived != true AND (Draft != true OR slug in FORCE_PUBLISH)
FORCE_PUBLISH = { "our-doctors": ["dr-mohal-banker"] }
Products also require Active == true
```

`dr-mohal-banker` is flagged Draft in the export but is live today and is the
lead doctor, so he is force-published. To change any of this, edit
`FORCE_PUBLISH` in `tools/cmsdata.py`.

Excluded items get no page **and** no list entry anywhere, so there are no
orphan links. `tools/verify.py` enforces this.

## Updating content

1. Re-export the collections from Webflow into `cms/` (keep the
   `... - <Collection Name> - <id>.csv` filename pattern — the loader matches on
   the collection name).
2. `python tools/build.py --skip-assets` for a fast rebuild, or plain
   `python tools/build.py` if new images were added.
3. `python tools/verify.py`
4. `npx vercel --prod`

## URL structure

Matches the live site so existing indexed links keep working:

| Collection | URL |
|---|---|
| Blogs | `/blog/<slug>` (listing at `/blog`, then `/blog/page/2`, `/blog/page/3`) |
| Blog Authors | `/blog-author/<slug>` |
| Blog Categories | `/blog-category/<slug>` |
| Departments | `/departments/<slug>` (listing at `/departments`) |
| Treatments | `/treatment/<slug>` |
| Our Doctors | `/our-doctors/<slug>` |
| Varicose Veins | `/varicose-veins/<slug>` |
| Non-Surgical Knee Pains | `/non-surgical-knee-pain/<slug>` |
| Products | `/products` (list only — Webflow has no detail template for it) |

`blog`, `departments` and `products` ship as `<folder>/index.html` rather than
`<folder>.html`, because serving both `blog.html` and `blog/<slug>.html` is
ambiguous under `cleanUrls`. `verify.py` fails the build if that collision ever
comes back.

Slugs are preserved **exactly** as they are in the CSVs, including awkward ones
like `knee-pain-` (trailing hyphen) and the 23 slugs containing `---`. They are
indexed URLs; normalising them would break live traffic.

## Image weight — worth addressing before launch

Localising the CMS images means the site no longer depends on Webflow's CDN, but
it also means it no longer benefits from Webflow's automatic image resizing. Two
consequences:

- Some CMS uploads are genuinely large — the biggest are **4–5 MB PNGs**.
- The generator drops `srcset` from CMS images, because the responsive variants
  Webflow generated (`…-p-500.png`, `…-p-800.png`) live on its CDN, not here. So
  a phone now downloads the full-size original.

This does not break anything, and every page renders correctly, but it will hurt
Largest Contentful Paint on image-heavy pages. Nothing was silently changed to
mask it. Two ways to fix, in order of effort:

1. **Vercel Image Optimization** — add an `images` block to `vercel.json` and
   route CMS `<img src>` through `/_vercel/image?url=…&w=…&q=…`. Config plus a
   small change in `Binder._one`; keeps one copy of each original.
2. **Pre-compress at build time** — add a Pillow pass in `tools/assets.py` to
   re-encode anything over ~300 KB and emit `-p-500` / `-p-800` variants plus a
   real `srcset`. Adds a dependency but produces a fully static, fast site.

## Known content issues

These are data problems, not build problems. The generator surfaces them rather
than silently papering over them:

- **Blog author `dr-mohal`** — the Bio is unedited Webflow placeholder text about
  a fictional *"Dr. Richard Alan"*. Visible at `/blog-author/dr-mohal`.
- **Testimonial names** — all four Testimonials rows still carry Webflow's stock
  item names (`Brown Building`, `City at Night`, `Mirrored Image`,
  `Open Sesame`) while the review bodies are genuine patient quotes. The build
  renders the `Subtext` label instead of the stock name; real names need to come
  from the clinic.
- **`Director - BnG vascular)`** — stray closing parenthesis in the static text
  under every blog card.
- **Duplicate doctor records** — `dr-chandresh-bharada` (published) and
  `dr-chandres-bharada` (draft). The draft is excluded so nothing duplicates
  live, but the CMS should be tidied.
- **Varicose Veins department name** — the Diseases dropdown label is the full
  SEO string *"Varicose Veins Treatment in Ahmedabad | Laser & VenaSeal Glue
  Treatment (No Surgery)"*. This matches the live site exactly; shorten the
  `Name` field if a tidier menu is wanted.
- **Products images** — only 2 of 19 products have an image, so 17 cards render
  without one (rather than showing Webflow's grey placeholder).

## Two third-party scripts left in place

Both still return 200, so they were kept rather than guessed at. Worth a decision
before launch:

- **`preloading_script-0.0.2.js`** on all 350 pages — a Webflow app integration
  that carries `data-ncf_api_key` and a **`data-mapbox_api_key` in the page
  source**. If the app is no longer used, remove the tag (and rotate that Mapbox
  key, since it has been publicly visible). Nothing on the site appears to depend
  on it, but it was left alone because its purpose could not be confirmed.
- **`drag-drop.json`** on 2 pages — a Lottie animation still hosted on
  `uploads-ssl.webflow.com`.

## What was fixed beyond filling in the CMS

Recorded here because these were pre-existing bugs in the export (and in some
cases on the live site), not things the CMS fill introduced:

- **The contact form could not be submitted.** Its only button was
  `<a href="#" class="outline-button">Send Message</a>`, an anchor with no submit
  behaviour, and the form had no `<input type="submit">` at all. Affected the
  department, treatment, varicose-veins, knee-pain and interview pages. Now a
  real `<button type="submit">` with the same classes.
- **Field names were inconsistent** across the site (`Name` / `Name-2` /
  `name-2` / `name-3` for one field) and the phone input on 13 pages was named
  `email-2` while being `type="tel"`. Normalised to one contract.
- **~20 dead links to `medicio.webflow.io`** — the Webflow template's demo site —
  shipped inside a hidden nav block on every page. Removed. These are still live
  on the production site today.
- **Dead template markup removed.** `fancy-columns-wrap-copy` carried Webflow's
  "Item Heading / Subtitle / eros dolor interdum nulla…" lorem ipsum, and
  `staff-collection` had an empty item template. Both are `display: none` in the
  CSS, so this was dead DOM and indexable text rather than anything visible —
  worth removing, but it was not a visible bug.
- **Dead links repaired**: the mobile and footer brand logos, the locale
  switcher, and the footer "Training" link all pointed at `#` despite their
  targets existing.
- **19 broken image references** — 10 from a hyphen-vs-space filename mismatch in
  the export, 9 absent entirely (including `favicon.png`, referenced by every
  page). Recovered from the CDN where possible; 2 lost conference photos had
  their `<img>` tags removed rather than left broken.
- **Three CMS links that would 404 in production** — `/departments/platelet-rich-plasma`
  (the Departments copy is a draft; the published one is under `/treatment/`) and
  two `varicose-vein` singular typos. Handled with 301s in `vercel.json`.
