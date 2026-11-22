# FIWS – Formula Imperial Worldwide Series

Static website: standings, results, calendar, entries, rules, application portal, status page and admin panel. Hosted on GitHub Pages with Supabase Auth, Postgres and Storage for shared persistence.

## Run / deploy
- Open `index.html` directly, or serve the folder (GitHub Pages: Settings → Pages → deploy from `main`, root).
- `index.html` is self-contained: the workbook is embedded in it.

## Update standings
1. Replace `data/Formula_Imperial_Worldwide_Series.xlsx` and run `python3 build.py`, **or**
2. Sign in as an administrator and publish the new `.xlsx` from Admin → Standings data. It is stored in Supabase Storage and becomes the shared workbook.

## Logo
Add `assets/fiws-logo.png` and `assets/fitc-logo.png` (they switch with the selected series), or upload them in Admin → Logos. Admin uploads are sanitized/rasterized and stored in Supabase Storage. Neutral white/black pixels adapt to light/dark theme while other colours and alpha are retained.

## Team colours
Teams and entries come from the workbook. Colours default to an automatic palette; administrators can change them in Admin → Team colours. Overrides are stored in Supabase and shared across devices.

## Configure
- Set the Supabase Site URL and allowed redirect URL to `https://p1k5up.github.io/fiws-portal/` in Authentication → URL Configuration.
- Applicant applications/status currently continue to use Supabase email verification; configure SMTP only if you need reliable applicant verification emails at scale.
- Administrator login is being moved to a separate username/password + mandatory authenticator MFA system. It does not use email. The initial Owner is provisioned with the one-time server-side bootstrap documented in `docs/ADMIN_SECURITY_DESIGN.md`.
- Rebuild with `python3 build.py` after any change to `src/`.

## Security notes
Supabase Auth currently verifies applicant email addresses only. Custom administrator authentication uses server-side Argon2id password hashes, mandatory TOTP MFA, opaque revocable sessions, one-time recovery codes, and rank checks in the `fiws-admin` Edge Function. Administrator database writes are not authorized by browser claims; the custom admin tables are inaccessible to anon/authenticated clients. Applicant rows remain scoped by PostgreSQL RLS to their owner. Never put a secret/service-role key in the browser. Application submission uses a Supabase Edge Function with HMACed IP throttling and a per-account database limit. Public assets are kept in a separate public Storage bucket; applicant data is never stored there. The custom admin feature branch remains under end-to-end testing and is not production-ready until its secrets are configured and the PR is reviewed.

## Workbook format
Each sheet holds season blocks side by side. Row 2 has the season titles, row 5 the section titles (ENTRIES, CALENDAR, STANDINGS (RACE BY RACE), STANDINGS (POINTS)), row 7 the column headers. Standings are cumulative points per round.

## Applications and status
1. Applicants submit using a verified email sign-in link. Their records are stored centrally in Supabase and are visible only to that applicant and authorised staff.
2. Applicants can sign in from any device to see their application status and staff note.
3. Staff review applications from Admin → Applications. Decisions are stored centrally and reflected in the applicant's status view.

Legacy localStorage applications are not automatically migrated. Export them from the old browser and only import them after each record has been matched to a verified applicant identity; an automated safe legacy-import workflow is not yet provided.

## Link previews (Discord, Slack, X, WhatsApp...)
`index.html` carries Open Graph and Twitter Card tags, a 1200x630 preview image (`assets/og-image.png`), a theme colour (the Discord embed stripe), a favicon, a web manifest and structured data. The image URL must be absolute, so it is built from `SITE_URL` (default `https://p1k5up.github.io/fiws-portal/`).
If the address changes: `SITE_URL=https://your.address/ python3 build.py`, then push.
Discord and others cache previews. After pushing, refresh the cache by posting the link with `?v=2` on the end, or with the Facebook Sharing Debugger / X Card Validator.
