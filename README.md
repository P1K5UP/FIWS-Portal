# FIWS – Formula Imperial Worldwide Series

Static website: standings, results, calendar, entries, rules, application portal, status page and admin panel. Hosted on GitHub Pages with Supabase Auth, Postgres and Storage for shared persistence.

## Run / deploy
- Open `index.html` directly, or serve the folder (GitHub Pages: Settings → Pages → deploy from `main`, root).
- `index.html` is self-contained: the workbook is embedded in it.

## Update standings
1. Replace `data/Formula_Imperial_Worldwide_Series.xlsx` and run `python3 build.py`, **or**
2. Drag the new `.xlsx` onto Admin → Standings data → Publish (stored in that browser only).

## Logo
Add `assets/fiws-logo.png` and `assets/fitc-logo.png` (they switch with the selected series), or upload them in Admin → Logos. Admin uploads are sanitized/rasterized and stored in Supabase Storage. Neutral white/black pixels adapt to light/dark theme while other colours and alpha are retained.

## Team colours
Teams and entries come from the workbook. Colours default to an automatic palette; administrators can change them in Admin → Team colours. Overrides are stored in Supabase and shared across devices.

## Configure
- `LEAGUE_EMAIL` near the top of the script in `src/index.template.html`: enables the "Email to league staff" button after an application.
- Rebuild with `python3 build.py` after any change to `src/`.

## Security notes
Supabase Auth verifies applicant and staff email addresses. PostgreSQL Row Level Security scopes applicant reads to their own records and restricts administrative actions to accounts with the trusted `app_metadata.fiws_role=admin` claim. Never put a secret/service-role key in the browser. Application submission uses a Supabase Edge Function with HMACed IP throttling and a per-account database limit. Public assets are kept in a separate public Storage bucket; applicant data is never stored there.

## Workbook format
Each sheet holds season blocks side by side. Row 2 has the season titles, row 5 the section titles (ENTRIES, CALENDAR, STANDINGS (RACE BY RACE), STANDINGS (POINTS)), row 7 the column headers. Standings are cumulative points per round.

## Applications and status (no server needed)
1. Set `LEAGUE_EMAIL` so applicants can email their application (it contains a JSON block). Applicants can also copy it from the receipt.
2. Admin → Applications → Import applications: paste the email text or JSON. Review, accept or reject, add a note.
3. Admin → Applications → Export status file. Save it as `data/status.json` and push. Applicants check Status with their code + email; the file only holds hashed codes, the decision and a note.
Applicants also see decisions on the device where they applied.

## Link previews (Discord, Slack, X, WhatsApp...)
`index.html` carries Open Graph and Twitter Card tags, a 1200x630 preview image (`assets/og-image.png`), a theme colour (the Discord embed stripe), a favicon, a web manifest and structured data. The image URL must be absolute, so it is built from `SITE_URL` (default `https://p1k5up.github.io/fiws-portal/`).
If the address changes: `SITE_URL=https://your.address/ python3 build.py`, then push.
Discord and others cache previews. After pushing, refresh the cache by posting the link with `?v=2` on the end, or with the Facebook Sharing Debugger / X Card Validator.
