# unboxlearning.in

Static marketing site for UnboxEd. 14 pages plus a 404, no framework, no build dependencies beyond Python.

## Edit and build

- Pages live in `src/pages/` as HTML fragments with a small header (title, description, nav). Solution pages are in `src/pages/solutions/`.
- The shared header, menu, footer and SEO tags are in `build.py`, so a change there updates every page.
- Styles: `src/assets/site.css`. Scripts (mobile menu, demo games, contact form): `src/assets/site.js`.

```
python build.py --check
```

This writes the finished site to `public/` and fails if any internal link or anchor is broken.

Preview locally:

```
python -m http.server 5195 --directory public
```

## Before going live

1. **Contact details**: the business email (preeti.agrawal@lightbulblabs.tech) and phone (+91 70048 47355) are set as `EMAIL` and `PHONE` in `build.py` and `CONTACT_EMAIL` in `src/assets/site.js`.
2. **Contact form**: by default it opens the visitor's email app. To receive submissions directly, create a free Formspree form and paste its URL into `FORM_ENDPOINT` at the top of `src/assets/site.js`, then rebuild.
3. **Legal pages**: `privacy.html` and `terms.html` are plain-language starting points. Have them reviewed before launch.

## Deploy to Vercel

```
cd public
vercel --prod
```

Then in the Vercel dashboard: Project → Settings → Domains → add `unboxlearning.in` and `www.unboxlearning.in`.

At your domain registrar, set the DNS records Vercel shows. Usually:

| Type  | Name | Value                  |
|-------|------|------------------------|
| A     | @    | 76.76.21.21            |
| CNAME | www  | cname.vercel-dns.com   |

HTTPS is issued automatically once DNS resolves (minutes to a few hours).
