# Bankers Vascular blog publishing workflow

## Future request contract

The requester supplies only:

1. a complete `.docx` article;
2. its intended featured/thumbnail image; and
3. `Author: Dr. [name]`.

The requested action is: `Publish this blog.` The publish operator must use the
repository tool below, inspect its output, build locally, and obtain the usual
deployment approval separately. This workflow does **not** deploy by itself.

## Bankers Notes (Dr. Mohal Banker only)

`/bankers-notes` is Dr. Mohal Banker's personal article archive. It uses the
same Blog CMS collection and article layout as `/blog`, but displays only posts
authored by Dr. Mohal Banker. Publish a note using `--bankers-notes`; this
fixes the author automatically so another doctor's article cannot enter this
archive by mistake.

```powershell
& $BV_PYTHON tools/publish_blog.py <article.docx> <thumbnail-image> --bankers-notes
```

## Guardrails

- Read the complete DOCX. Its first meaningful paragraph is the post title;
  retain all article text. Never summarize, rewrite, or add medical claims.
- Convert title, headings, paragraphs, ordered/bullet lists and tables to rich
  HTML. The resulting article has exactly one H1. Later Word Heading 1 values
  are preserved as H2.
- Derive a lowercase hyphenated slug from the title. Stop on an existing title
  or slug; never overwrite a post or image.
- Use the supplied thumbnail as both `Blog Thumbnail` and `Main Image`. Copy it
  under `src/images/blog/<slug>.<extension>` without changing its bytes. It is
  rendered only on blog listing cards (including `/blog`) with the blog title
  as its alt text. Never render this thumbnail on an individual article page:
  there, the page title is followed directly by the article content. Do not
  render an on-page author/date/featured-media block before the content.
  `Main Image` remains available solely for canonical Open Graph/Twitter,
  BlogPosting schema, and social sharing metadata.
- Resolve the supplied name to a published Blog Author first, then to a
  published `/our-doctors/` profile. Do not create a doctor or author profile.
  A doctor-only match is linked through that existing doctor profile.
- Generate `Meta Title`, `Meta Description`, canonical URL, OG title,
  description and image from the source fields. The build emits the canonical,
  Open Graph/Twitter tags, sitemap entry, BlogPosting schema, and linked author
  schema from those fields.
- Add only natural internal links to text already in the article. Link only
  verified, published Bankers Vascular treatment, department, and relevant
  existing blog routes; never invent a URL or add a link merely to repeat a
  keyword. Link a doctor profile only when the existing article text makes that
  profile naturally useful. The initial topic rules cover heel pain, knee/GAE,
  varicose veins, PAE, piles/HAE, and hair/PRP only where matching pages exist.
- Do not place clickable external medical links in article body text. If the
  requester explicitly asks for authoritative references, put them in a
  separate `References` section as plain, non-clickable citations. Never add
  competitors, commercial blogs, or unverified sources.
- Preserve the existing templates, components, header/footer, CSS and Webflow
  behaviour. The Blogs CSV automatically populates `/blog`, the home blog area,
  related posts and the blog detail template.

## Operator command

Use the bundled Python runtime when running locally:

```powershell
$BV_PYTHON = 'C:\Users\Bvh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $BV_PYTHON tools/publish_blog.py <article.docx> <thumbnail-image> --author 'Dr. Name' --dry-run
& $BV_PYTHON tools/publish_blog.py <article.docx> <thumbnail-image> --author 'Dr. Name'
& $BV_PYTHON tools/build.py
& $BV_PYTHON tools/verify.py
```

Before releasing, inspect the generated `/blog/<slug>` page at desktop, tablet,
and mobile widths; confirm the title/one-H1 rule, direct title-to-content flow
(with no on-page featured image or author/date block), rich text, `/blog`
thumbnail card and alt text, internal/external links, home card,
canonical/OG/schema, and sitemap. No production deployment occurs without an
explicit release request.
