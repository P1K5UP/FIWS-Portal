# FIWS Portal

The public portal for the Formula Imperial Worldwide Series (FIWS). The site is a static, responsive single-page application with a workbook-backed championship model and a Supabase-powered shared administration/application backend.

**Production:** https://fiws.devs.surf/

## Project layout

- `src/index.template.html` — canonical application template, styles, markup and browser logic.
- `index.html` — generated GitHub Pages entry point. Do not hand-edit independently of the template.
- `build.py` — embeds the bundled workbook and generates the canonical URL, favicon, robots file and sitemap.
- `data/Formula_Imperial_Worldwide_Series.xlsx` — bundled workbook fallback and source data.
- `assets/` — local brand, PWA and social-preview assets.
- `supabase/functions/fiws-admin/` — custom administrator authentication, MFA, account management, settings and staff workflows.
- `supabase/functions/submit-application/` — public application submission and reference-code status lookup.
- `supabase/config.toml` — explicit per-function JWT verification settings matching production.
- `supabase/functions/bootstrap-fiws-admins/` — retired compatibility endpoint; intentionally returns HTTP 410.
- `supabase/migrations/` — database schema and policy history.
- `tests/` — Python regression tests for frontend contracts, migration history, asset integrity and administrator security; `tests/browser/` contains Playwright browser checks.
- `.github/workflows/validate.yml` — build, static checks, tests, Edge Function checks and Pages deployment preparation.

## Local development

Requirements: Python 3, Node.js, and Deno for the complete validation suite.

```sh
python3 build.py
python3 -m http.server 8000
```

Open http://localhost:8000/. The local origin is included in the Edge Function development allowlists.

To build with another public base URL:

```sh
SITE_URL=https://example.com/ python3 build.py
```

The default build expects exactly one `.xlsx` file in `data/`. Pass a workbook path explicitly to `build.py` when testing another workbook.

## Validation

```sh
python3 -m unittest discover -s tests -v
python3 -c "import re,pathlib; s=pathlib.Path('src/index.template.html').read_text(); m=re.search(r'<script>(.*?)</script>', s, re.S); pathlib.Path('/tmp/fiws-inline.js').write_text(m.group(1))"
node --check /tmp/fiws-inline.js
deno check --no-lock --config supabase/functions/fiws-admin/deno.json supabase/functions/fiws-admin/index.ts
deno check --no-lock --config supabase/functions/submit-application/deno.json supabase/functions/submit-application/index.ts
deno check --no-lock --config supabase/functions/bootstrap-fiws-admins/deno.json supabase/functions/bootstrap-fiws-admins/index.ts
npm install --no-save --package-lock=false --no-audit --no-fund
npx playwright install --with-deps chromium
npx playwright test
```

The GitHub Actions workflow performs the generated-site build, metadata/asset checks, Python regression tests, Chromium browser interactions, a critical axe accessibility scan, responsive overflow checks, JavaScript syntax validation, Edge Function type checks and a production-workbook parser smoke test. Playwright and axe are pinned development-only test dependencies; they are not part of the deployed site bundle.

## Deployment model

Changes should be made on a feature branch and submitted as a pull request. The PR workflow rebuilds the site and checks that committed generated files are synchronized. Merging to `main` triggers validation and GitHub Pages deployment; the workflow also commits generated Pages files when needed.

Do not edit `index.html` without making the corresponding template change. A clean build should reproduce the committed generated page.

## Supabase operations

The browser only uses the publishable key. The service-role key and all FIWS secrets belong exclusively in Supabase Edge Function secrets.

The custom administrator system uses Argon2id password hashes, one-time TOTP verification, hashed session/recovery tokens, server-side authorization and privacy-preserving breached-password screening. Password checks send only a five-character SHA-1 hash prefix to the Pwned Passwords range API; the raw password and full hash remain inside the Edge Function. The application service uses reference codes rather than requiring applicants to create Supabase Auth accounts.

**Migration safety:** the repository now contains SQL for all 24 production migration versions plus one idempotent pending local grant migration. Two restored production migrations were reconstructed from read-only catalog evidence rather than recovered byte-for-byte. See [the migration reconciliation record](docs/MIGRATION_RECONCILIATION.md) and [the project audit](docs/PROJECT_AUDIT.md). Do not run `supabase db push` against production until the reconstructed SQL has been validated against a disposable Supabase branch/database and the resulting schema diff reviewed.

## Operational notes

- The workbook is embedded into the generated static page as a bundled fallback; shared workbook, team colours and logos can be published through the administrator interface.
- Accepted/rejected applications are automatically deleted 24 hours after the decision by the scheduled database job.
- The legacy `bootstrap-fiws-admins` Edge Function is intentionally retired. New administrator bootstrap/recovery flows live in `fiws-admin`.
- The site has no npm application build dependency; third-party browser libraries are loaded as pinned CDN scripts. The SheetJS 0.20.3 script includes SHA-384 Subresource Integrity, and Playwright/axe are used only for CI tests.
