# Bankers Vascular website knowledge base

This is the working reference for the Bankers Vascular Centre website. Read it
before changing content, templates, styles, CMS data, or deployment settings.

## What this repository is

- This is a static site generated from a Webflow export plus CMS CSV exports.
- `src/` contains the visual source templates, CSS, JavaScript, fonts, and
  static assets.
- `cms/` contains the exported Webflow collections; it is the source of truth
  for collection content.
- `tools/` turns the templates and CSV rows into the deployable site.
- `dist/` is generated output. Never edit it directly.
- `api/contact.js` is the Vercel serverless lead-form endpoint.
- Vercel builds from the repository root and deploys `dist/`.

The project is deliberately structured so the unbound Webflow export cannot be
deployed accidentally. The root must not contain a deployable `index.html`.

## First principles and non-negotiable rules

1. Preserve public URLs, canonical metadata, redirects, sitemap behaviour,
   CMS publishing rules, and `/api/contact` unless a task explicitly changes
   them.
2. Keep a Webflow template's `data-wf-page`, Webflow classes, `data-w-id`
   attributes, and `src/js/webflow.js` aligned. Webflow interactions rely on
   them; changing IDs can leave animated sections invisible.
3. Prefer editing the source template in `src/`, CSS in `src/css/`, or the
   generator configuration in `tools/wfconfig.py`. Never hand-edit `dist/`.
4. Do not replace the latest exported CSS with older CSS just to recover a
   component. The current Webflow export is the visual source of truth.
5. CMS fields can contain very long titles and rich text. Every new component
   must tolerate wrapping, missing optional images, and narrow screens.
6. Do not publish Draft or Archived CMS rows. The one deliberate exception is
   Dr. Mohal Banker, documented below.
7. Keep `claude.md` local/untracked. It is excluded in `.git/info/exclude`.

## Local development and verification

```bash
# Full build; downloads only genuinely missing CMS images.
python3 tools/build.py

# Fast rebuild; reuse the existing CMS asset cache.
python3 tools/build.py --skip-assets

# Structural production checks against dist/.
python3 tools/verify.py

# Serve dist/ locally, with the same clean URL/redirect rules as Vercel.
python3 tools/serve.py 3111

# Optional local smoke test, once the server is running.
python3 tools/smoke.py http://127.0.0.1:3111
```

Equivalent npm commands: `npm run build`, `npm run build:fast`, `npm run
verify`, and `npm run serve`.

After every content, template, or style change:

1. Build with the appropriate command.
2. Run `python3 tools/verify.py`.
3. Test the affected page at desktop, tablet, and mobile widths.
4. Check the matching list page, detail page, navigation dropdown, form, and
   any related-item cards.
5. Before production release, run `python3 tools/smoke.py <live URL>`.

`tools/serve.py` is the correct local host. It serves `dist/`, not the raw
templates. A raw `src/index.html` preview will show Webflow collection
placeholders and is not a valid preview.

## Deployment

- Remote: `https://github.com/Thorfin69/Bankers`
- Production branch: `main`
- Host: Vercel
- Vercel build command: `python tools/build.py`
- Vercel output directory: `dist`
- Vercel dashboard root directory: repository root (leave it empty; never set
  it to `dist`).

Required Vercel environment variables for forms:

| Variable | Purpose |
| --- | --- |
| `RESEND_API_KEY` | Resend API credential |
| `CONTACT_TO_EMAIL` | Recipient(s), comma separated |
| `CONTACT_FROM_EMAIL` | Optional verified sender; otherwise Resend onboarding sender |

Without the first two variables, the API intentionally returns 503 and the
site displays its form error state rather than falsely accepting a lead.

## Architecture and ownership

| Path | Owns |
| --- | --- |
| `src/*.html` | Static pages and CMS detail/list templates |
| `src/css/normalize.css` | Normalisation |
| `src/css/webflow.css` | Webflow base styles |
| `src/css/bankersvascular-419ec5b7a6b1caef19c5ab2.webflow.css` | Primary visual system and responsive overrides |
| `src/js/webflow.js` | Webflow interactions, navs, sliders, scroll reveals |
| `src/js/forms.js` | Client-side form submission to `/api/contact` |
| `src/images/` | Static export assets |
| `src/images/cms/` | Raw Webflow image cache; ignored, not committed |
| `src/images/cms-opt/` | Optimised WebP CMS assets; committed and deployed |
| `cms/*.csv` | Webflow CMS exports |
| `tools/wfconfig.py` | Collection schemas, field bindings, page lists, nav lists |
| `tools/cmsdata.py` | CSV loading, publish filtering, joins, sorting, URLs |
| `tools/build.py` | Render pipeline, metadata, links, forms, sitemap, static copy |
| `tools/assets.py` | Asset localisation and image optimisation |
| `tools/verify.py` | Build acceptance checks |
| `tools/smoke.py` | Running/live deployment checks |
| `vercel.json` | Clean URLs, redirects, security/cache headers, build config |
| `api/contact.js` | Lead-delivery endpoint |

## Current source pages

### Public static pages

| Source file | Public URL | Role |
| --- | --- | --- |
| `index.html` | `/` | Home: hero, testimonials, conditions, treatments, team, recent blogs |
| `about-banker-vascular-center.html` | `/about-banker-vascular-center` | About the clinic |
| `contact-us.html` | `/contact-us` | Contact details, lead form, doctor listing |
| `training.html` | `/training` | Training information |
| `interview-of-patients-after-g-a-e-procedure.html` | `/interview-of-patients-after-g-a-e-procedure` | Patient result/interview page |
| `bng-conference-november-2024.html` | `/bng-conference-november-2024` | Conference page with doctors |
| `bng-con-2025.html` | `/bng-con-2025` | Conference page with doctors |
| `cancellation-refund-policy.html` | `/cancellation-refund-policy` | Policy |
| `privacy-policy.html` | `/privacy-policy` | Policy |
| `401.html` | `/401` | Utility page, excluded from sitemap |
| `404.html` | `/404` | Utility page, excluded from sitemap |

### Public CMS listing pages

| Source file | Generated URL | Collection | Notes |
| --- | --- | --- | --- |
| `blog.html` | `/blog`, `/blog/page/N` | Blogs | 100 items per page |
| `departments.html` | `/departments` | Departments | Ordered by `Sorting` |
| `products.html` | `/products` | Products | Published + `Active == true` only |

These use directory output (`blog/index.html`, `departments/index.html`,
`products/index.html`) because `cleanUrls` makes a file and a same-name CMS
folder ambiguous.

### CMS detail templates

| Template | Generated URL pattern | Collection |
| --- | --- | --- |
| `detail_blog.html` | `/blog/<slug>` | Blogs |
| `detail_blog-author.html` | `/blog-author/<slug>` | Blog Authors |
| `detail_blog-categories.html` | `/blog-category/<slug>` | Blog Categories |
| `detail_departments.html` | `/departments/<slug>` | Departments |
| `detail_treatment.html` | `/treatment/<slug>` | Treatments |
| `detail_varicose-veins.html` | `/varicose-veins/<slug>` | Varicose Veins |
| `detail_non-surgical-knee-pain.html` | `/non-surgical-knee-pain/<slug>` | Non-Surgical Knee Pains |
| `detail_our-doctors.html` | `/our-doctors/<slug>` | Our Doctors |

`detail_products.html`, `detail_accordions.html`, `detail_app-bankers-opd.html`,
and `insurance-departments/untitled.html` are intentionally unpublished. They
are incomplete/unbound Webflow pages, not safe page starters.

## CMS collections and page contracts

Every collection CSV has the standard Webflow columns: `Name`, `Slug`, IDs,
`Archived`, `Draft`, and timestamps. The fields below are the fields this site
actually consumes.

| Collection | Primary fields | Appears in |
| --- | --- | --- |
| Blogs | `Blog Thumbnail`, `Main Image`, `Short Details`, `Main Details`, `Category`, `Author`, `time` | Blog list, blog detail, home latest posts, author/category lists |
| Blog Authors | `Bio`, `Picture`, social profile URLs | Author detail and blog attribution |
| Blog Categories | `Name` | Category detail and blog join |
| Departments | `Meta Title`, `Meta Description`, `Main Headline`, `Department Icon`, `Department Short Details`, `Department Details`, `background`, `Sorting` | Department list/detail, nav, related treatment cards |
| Treatments | `Main Headline`, `Department Icon`, `Department Short Details`, `Department Details`, `background`, `Sorting`, meta fields | Treatment detail, nav, related treatments |
| Varicose Veins | Icon, short/details/background, meta fields, `Sorting` | Dedicated detail family |
| Non-Surgical Knee Pains | Icon, short/details/background, meta fields, `Sorting` | Dedicated detail family |
| Our Doctors | `Doctor Designation`, thumbnail/detail images, bio/speciality/experience/awards, `Order` | Home, contact, event pages, nav, doctor details |
| Products | `Image`, `Price (INR)`, `Subtitle`, `Anchor Slug`, `Active` | Products list |
| Testimonials | `Sort Order`, `BG Image`, `Subtext`, `Short Description`, `YT` | Home testimonial cards |

### Publishing rules

```text
Published = Archived is not true
            AND (Draft is not true OR item is explicitly force-published)
Products  = Published AND Active is true
```

The sole force-published item is `our-doctors/dr-mohal-banker`; he is the
lead doctor and must remain visible despite his exported Draft flag. The rule
lives in `tools/cmsdata.py`, not in a template.

Do not "fix" an unpublished reference in markup. The generator resolves joins
to only published records and removes empty UI instead of making broken links.

### Sort and relationship rules

- Doctors: numeric `Order`.
- Departments and Treatments: numeric `Sorting`.
- Testimonials: numeric `Sort Order`.
- Products: alphabetical `Name`.
- Blogs: newest parsed `time`, then `Created On` when needed.
- Blog author and category references use the respective slug fields. An
  unpublished author/category produces no linked author/category UI.
- Treatment detail pages list up to five sibling treatments in the related
  articles area; dead static pagination is removed.

### Binding rules that prevent broken UI

- A CMS `<img>` receives a local optimised asset URL, no `srcset`, and an alt
  value based on the item name.
- Missing optional images remove the image or its wrapper; never leave an empty
  `src` or Webflow stock placeholder.
- Department/treatment related cards use `feature-image` bound to
  `Department Icon`; remove it if no icon exists.
- Blog main images prefer `Main Image`, then `Blog Thumbnail`.
- Doctor cards prefer `Doctor Thumbnail`, then `Doctor Details Image`.
- Rich text is injected only into designated rich-text containers; do not
  escape it into plain text fields.
- Product cards omit absent product images. They show price formatted in INR.
- Testimonial card headings use `Subtext`, not the currently unreliable
  Webflow `Name` values.

The authoritative element-class-to-field mapping is `tools/wfconfig.py`.
When adding a CMS binding, add it there, preserve the cloned Webflow collection
item structure, and add corresponding verification if the new field is vital.

## Global navigation, footer, and shared behaviour

- Every page gets CMS-powered dropdowns for doctors, departments, and
  treatments. Expected published counts are 9, 12, and 9 respectively.
- Header navigation, footer, language control, mobile menu, dropdowns, sliders,
  WhatsApp button, and scroll effects are Webflow behaviour. Preserve their
  classes and `data-w-*` attributes.
- The common footer includes contact details, social links, opening hours, and
  legal/quick links. Fix a shared link in source templates/generator behaviour,
  not in generated output.
- The site uses Satoshi and General Sans local font files. Do not introduce a
  network font dependency unless it is an explicit design requirement.

## Responsive design rules

The latest Webflow export owns base layout, padding, spacing, breakpoints, and
interactions. Add compact overrides at the end of the primary CSS file only when
needed to preserve CMS content safely.

Always test at least:

- Desktop: 1440px or wider.
- Tablet: roughly 768–991px.
- Mobile: 375–480px.

### Long content and cards

- Titles, descriptions, CMS rich text, breadcrumbs, and nav labels must wrap
  without horizontal overflow.
- Never crop long CMS descriptions purely to force all cards to a uniform
  height unless the design specifically calls for clamping.
- For extremely long department descriptions, use a full-width/row card rather
  than a narrow grid card. The first eight department cards remain compact;
  later long-form cards span the grid so their content stays readable.
- Keep department icons optional. No icon must mean no image element, not a
  placeholder.

### Home doctor/team section

The `team-member-section` is CMS-driven by `.doctor-archive-list`.

- On desktop/tablet it is a horizontally scrollable grid of stable cards.
- On mobile it is intentionally a horizontal carousel: one 320px-ish card is
  readable at a time with the next card available by horizontal swipe.
- The image wrapper has a deterministic height and the image uses
  `object-fit: contain`; doctor photos must not overlap each other.
- The Webflow image animation overlay is hidden for this section, and doctor
  image/name/designation visibility is forced after interaction initialisation.
- Do not return this list to a shrinking flex layout. Flex-shrunk 350px items
  plus fixed-width inner cards caused the original overlapping-photo bug.

### Breadcrumbs

Blog breadcrumbs use the dedicated classes:

- `.blog-breadcrumb-section`
- `.blog-breadcrumb-wrapper`
- `.blog-breadcrumb-trail`

They are left aligned, allowed to wrap safely, and the trailing descriptive
breadcrumb is line-clamped on mobile. Do not place a full blog excerpt into a
single non-wrapping breadcrumb line. Check long post titles and descriptions at
mobile width whenever changing this area.

### Images and visual checks

- Background image cards must receive a real `background-image` URL; a grey
  Webflow placeholder means the CMS binding or asset resolution is wrong.
- Check images at their actual rendered crop, not just that their URLs load.
- Home testimonial cards bind `BG Image`. All four content-background images
  must render rather than repeating the placeholder.
- For doctor cards, check each source photo is visible and not covered by an
  animation overlay.

## Forms and leads

Every public lead/appointment/contact form is normalised during the build to:

- `method="post"` and `action="/api/contact"`;
- standard field names (`Name`, `Phone-Number`, `Email`, `Date`, `Message`);
- a real submit control, even where the Webflow export supplied a styled anchor;
- a honeypot (`_gotcha`), success block, and failure block;
- `data-form-name` and `data-form-page` metadata.

`src/js/forms.js` intercepts submission, posts JSON, disables buttons while
waiting, shows the existing Webflow success/failure blocks, and only shows
success for an `{ ok: true }` API response.

`api/contact.js` validates name, phone, and optional email; rate limits to five
submissions per IP per minute; ignores honeypot submissions; and sends email
through Resend. Preserve this behaviour on all new lead forms.

When adding a form, use a normal visible form field layout with a submit button;
then build and inspect the generated HTML to confirm it was wired. Test both a
valid submission path (where credentials are available) and client/server
failure states.

## How to add or scale a content page

### Add a CMS-backed collection/page family

1. Export/add the Webflow collection CSV in `cms/`, keeping the filename
   pattern `... - <Collection Name> - <id>.csv`.
2. Create/export a detail template into `src/` if the collection needs detail
   pages. Keep its Webflow IDs/classes intact.
3. Add the collection to `COLLECTIONS` in `tools/wfconfig.py`, including the
   CSV label, URL folder, template, metadata fields, and element bindings.
4. Add list/card bindings to `ITEM_BINDINGS`, then use the list on the desired
   static page through `PAGE_LISTS` or `DETAIL_LISTS`.
5. Add a nav list only if it is truly a global navigation taxonomy.
6. Confirm publish/active rules in `tools/cmsdata.py` and create redirects for
   any legacy URLs in `vercel.json`.
7. Build, verify, test multiple rows (long title, short title, no image,
   draft/archived row), and inspect `/sitemap.xml`.

### Add a standalone/static page

1. Start with the closest existing public source page, not an excluded CMS
   shell.
2. Give it a distinct Webflow page ID only through an actual Webflow export;
   do not manually copy a random `data-wf-page` value.
3. Add its internal links to shared navigation/footer as required.
4. If it should appear in the sitemap, do not add it to `NOINDEX_PAGES`.
5. Add an intentional redirect if it replaces an indexed URL.
6. Build and test desktop/tablet/mobile, all internal links, and any form.

### Add CMS content safely

1. Create/update the row in Webflow, including a unique stable slug, title,
   SEO fields, publication status, and image alt-friendly name.
2. Re-export the corresponding CSV to `cms/`.
3. Run a full build if new image URLs were added; use `--skip-assets` only
   when no new assets are needed.
4. Check the listing, detail page, relevant homepage block, nav, sitemap, and
   related content.
5. Commit CSV changes and any new files in `src/images/cms-opt/`.

Do not normalise historic slugs just because they look awkward. They are public
indexed URLs, including trailing hyphens and repeated-hyphen slugs.

## Build and verification contract

`tools/verify.py` is expected to enforce, at minimum:

- generated HTML page count and sitemap count;
- all published CMS URLs exist;
- drafts/archives are excluded;
- no `No items found`, `w-dyn-bind-empty`, empty image `src`, or unresolved
  internal links;
- expected navigation population (9 doctors, 12 departments, 9 treatments);
- lead forms use `/api/contact` and retain success/failure/honeypot behaviour;
- no raw root `index.html` deploy trap.

Current expected production build: 350 HTML pages and 348 sitemap URLs. Update
this reference and tests intentionally if a real product decision changes that
contract.

## Asset policy

- Static images, fonts, PDFs, and JavaScript live under `src/` and are copied
  to `dist/`.
- CMS images are cached under `src/images/cms/` and optimised to WebP under
  `src/images/cms-opt/` at quality 90. The optimised directory is committed.
- A clean checkout should build without downloading the historic CMS image set.
- If a new image cannot be retrieved, the generator can retain its Webflow CDN
  URL and record it in `tools/asset-report.txt`; investigate rather than making
  a broken local placeholder.
- Do not change an image filename extension without changing the bytes to match
  it. Hosting uses the extension to infer MIME type.

## Redirects, SEO, and sitemap

- Canonical base: `https://bankersvascular.com`.
- `cleanUrls: true` and `trailingSlash: false` are part of the URL contract.
- Redirects in `vercel.json` protect old `.html`, raw detail-template, and
  known legacy URLs. Preserve them when refactoring.
- Detail page title, description, OG image, and canonical output are populated
  from the `title`, `desc`, and `og_image` declarations in `tools/wfconfig.py`.
- Do not ship a CMS item with missing essential SEO data without an intentional
  fallback.

## Known content debt (not generator failures)

- Blog author `dr-mohal` still has placeholder bio copy about a fictional
  "Dr. Richard Alan".
- Testimonial `Name` values are Webflow stock names. Cards correctly use
  `Subtext`, but real patient-name labels should replace the source data.
- Static blog cards include `Director - BnG vascular)` with a stray parenthesis.
- There is a draft duplicate doctor row `dr-chandres-bharada`; the published
  `dr-chandresh-bharada` remains the only live record.
- The Varicose Veins department name is intentionally a very long SEO label in
  the Diseases dropdown. Shorten CMS `Name` only if product/SEO approves it.
- Most product rows have no image; cards intentionally omit the image rather
  than show a placeholder.
- A third-party preload integration is still present in the Webflow export and
  exposes a Mapbox key in page source. Do not remove it without confirming the
  integration is unused; rotate the key if it is retired.

## Change checklist

Before considering a change complete:

- [ ] Changed source, config, or CSV—not `dist/`.
- [ ] Preserved Webflow classes/interaction identifiers.
- [ ] Checked long and missing CMS values.
- [ ] Checked desktop, tablet, and mobile layouts.
- [ ] Checked nav, footer, breadcrumbs, related content, and images.
- [ ] Checked form behaviour if the page contains a form.
- [ ] Ran build and `tools/verify.py`.
- [ ] Ran a local smoke test or targeted local page checks.
- [ ] Ran live smoke test after deployment.
- [ ] Updated this document when a durable architectural/page rule changed.
