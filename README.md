# FIWS – Formula Imperial Worldwide Series

FIWS is a static league portal hosted on GitHub Pages, with Supabase providing shared application, administration, workbook, logo and settings storage.

## Local development

Run commands from the repository root:

```sh
python3 build.py
python3 -m http.server 8000
```

Open `http://localhost:8000/`. Use `http://localhost:8000/#admin` for the administrator panel. Do not open the HTML file with `file://`: browser-origin checks prevent the Supabase functions from accepting that origin.

The editable website source is `src/index.template.html`. `index.html` is the generated, self-contained GitHub Pages file. Rebuild after changing the template or the source workbook. The build embeds `data/Formula_Imperial_Worldwide_Series.xlsx` and writes the canonical site URL into the generated metadata, robots file and sitemap.

## Development and release

- Work on `feat/shared-supabase-backend`; CI validates pull requests and builds an isolated preview artifact.
- The production site is published from `main` by GitHub Pages. Changes on the feature branch do not update the public site.
- Review the pull request and its passing GitHub Actions checks before release. Merge/publish only with explicit release approval.
- Supabase Edge Functions and database migrations are deployed separately from GitHub Pages. A frontend merge does not deploy backend code.

## Updating league data and branding

- **Standings:** replace `data/Formula_Imperial_Worldwide_Series.xlsx` and run `python3 build.py` for a source-controlled workbook update, or sign in and publish the workbook through Admin → Standings data for a shared live update.
- **Logos:** upload FIWS/FITC logos through Admin → Logos. Uploads are sanitized/rasterized and stored in Supabase Storage.
- **Team colours:** update Admin → Team colours. Season-specific overrides are shared through Supabase.
- **Shared settings:** publish through the administrator panel; do not edit production database tables directly unless following an approved migration or recovery procedure.

## Applications and status

Applicants do not create accounts and are not sent verification or status emails. The application form collects an email address only so league staff can contact the applicant.

After a successful submission, the applicant receives a private reference code in the format `FIWS-` followed by 26 hexadecimal characters. Keep or copy this code: it is the credential required to check status. If the applicant chooses the necessary-cookie option, the latest code is remembered in a first-party cookie on that browser for up to one year. The cookie is optional; the code can always be entered manually. Only the latest code is remembered on a device.

Status lookup reveals only the applicant name, application type, series, decision and staff note. It does not expose the contact email or full application. Staff review applications in Admin → Applications.

Accepted and rejected applications are automatically deleted 24 hours after the decision (the scheduled cleanup runs every five minutes, so deletion may occur up to five minutes after that threshold). Applicants should save any information they need before that retention period expires. Deleting an application cannot remotely erase a cookie on another device; a stale code is cleared when that device next checks it.

Legacy applications that existed only in an old browser are not automatically imported. Do not assume they are present in the shared database.

## Administrator access

Staff sign in with their provisioned username and password, then complete mandatory authenticator-app TOTP MFA. There is no email-based administrator login. Session tokens are held in page memory rather than persistent browser storage, so reloading the page requires signing in again. Recovery codes are shown once and must be stored securely.

Ranks and permissions are enforced by the `fiws-admin` Edge Function, not by hiding controls in the browser. Never put a Supabase service-role key, bootstrap secret, MFA encryption key, rate-limit pepper or owner-recovery secret in this repository, website code, or chat. Server secrets belong only in Supabase Edge Function secrets.

## Backend and deployment

The production Supabase project is configured separately from GitHub Pages. The active `fiws-admin` and `submit-application` functions use server-side service credentials. The application endpoint is public by design but applies origin validation, input validation and network rate limiting; it does not permit direct browser access to application rows.

The legacy `bootstrap-fiws-admins` function remains a separate operational item and should be reviewed for retirement only after confirming no legacy access path is needed. Do not disable or delete production functions, change secrets, or apply ad-hoc SQL as part of a frontend-only release.

See [Backend operations](docs/supabase-backend-setup.md) and [Administrator security design](docs/ADMIN_SECURITY_DESIGN.md) for the current operating model and safeguards.

## Workbook format

Each sheet holds season blocks side by side. Row 2 has the season titles, row 5 the section titles (ENTRIES, CALENDAR, STANDINGS (RACE BY RACE), STANDINGS (POINTS)), and row 7 the column headers. Standings are cumulative points per round.

## Link previews

The generated `index.html` contains Open Graph and Twitter Card metadata and uses `assets/og-image.png` (1200×630). `build.py` derives the absolute image URL, canonical site URL, robots.txt and sitemap.xml from `SITE_URL` (default `https://p1k5up.github.io/fiws-portal/`). If the public address changes, rebuild with the new URL, for example:

```sh
SITE_URL=https://your.address/ python3 build.py
```

Social platforms cache link previews; allow time for cache refresh after publishing.
