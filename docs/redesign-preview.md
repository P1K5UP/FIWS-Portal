# FIWS redesign preview and preservation contract

## Local preview (uses the already allowed backend origin)

The backend explicitly allows `http://localhost:8000`. Use that exact host and port for the preview; do not use `127.0.0.1`, open the file with `file://`, or choose a different port unless the Edge Function origin allowlists are deliberately updated and reviewed.

### From a downloaded GitHub Actions preview artifact

1. Open the redesign pull request and select its latest successful **Validate FIWS portal** workflow run.
2. Download the artifact named `fiws-preview-pr-<number>` and extract it.
3. Open a terminal in the extracted preview directory (the directory containing `index.html`).
4. Run:

```sh
python3 -m http.server 8000
```

5. Open `http://localhost:8000/` in the browser.

The artifact contains the self-contained generated site plus its manifest, assets and workbook data. It is isolated from the production Pages deployment and is not merged into `main`.

### From a local checkout of the redesign branch

```sh
git checkout redesign/fiws-premium-ui-overhaul
python3 build.py
python3 -m http.server 8000
```

Then open `http://localhost:8000/`.

## Why the preview is local

The Supabase Edge Functions currently allow only these browser origins:

- `https://p1k5up.github.io`
- `http://localhost:8000`

A preview on another host is rejected before application logic runs and appears as a browser fetch/CORS error. The preview process therefore uses the existing allowed local origin and does not need a production CORS change. Do not broaden the allowlist to wildcard origins.

A shareable hosted preview needs an additional stable origin and a separately reviewed/deployed allowlist change in both Edge Functions. The hosting integration considered for that path was not connected, so this branch uses the reliable local preview instead.

## Preservation contract

The redesign may change presentation and interaction polish, but must preserve:

- Home, Standings, Results, Calendar, Entries, Rules, Apply and Status views.
- Admin authentication, MFA, permissions, session handling and staff workflows.
- Application submission, reference-code status lookup and privacy safeguards.
- Workbook parsing and publication, shared settings, logos and team colours.
- Driver/constructor standings, leaderboard replay and position cues, round history, filters, search and historical data.
- Responsive navigation, including the existing mobile bottom dock.
- Light/dark themes, keyboard navigation, reduced-motion support and accessible labels.

The workbook remains the source of truth. Do not hardcode individual driver, constructor, team or standings corrections. Keep `src/index.template.html` and generated `index.html` synchronized.
