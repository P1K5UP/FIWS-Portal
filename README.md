# FIWS – Formula Imperial Worldwide Series

Static website: standings, results, calendar, entries, rules, application portal, status page and admin panel. No server, no tracking, no cookies.

## Run / deploy
- Open `index.html` directly, or serve the folder (GitHub Pages: Settings → Pages → deploy from `main`, root).
- `index.html` is self-contained: the workbook is embedded in it.

## Update standings
1. Replace `data/Formula_Imperial_Worldwide_Series.xlsx` and run `python3 build.py`, **or**
2. Drag the new `.xlsx` onto Admin → Standings data → Publish (stored in that browser only).

## Logo
Add `assets/fiws-logo.png`, or upload it in Admin → Logo.

## Team colours
Teams and entries come from the workbook. Colours default to an automatic palette; change them in Admin → Team colours (this device) or put them in `TEAM_COLORS` in `src/index.template.html` and rebuild (everyone).

## Configure
- `LEAGUE_EMAIL` near the top of the script in `src/index.template.html`: enables the "Email to league staff" button after an application.
- Rebuild with `python3 build.py` after any change to `src/`.

## Security notes
A static site has no server-side access control. The admin passcode (PBKDF2, 600k rounds, lockout with backoff, 20-minute idle timeout) protects the review panel on one device only. Applications are stored in the applicant's browser; use a backend or form service to collect them centrally. A Content-Security-Policy meta tag limits scripts to the page and cdnjs.

## Workbook format
Each sheet holds season blocks side by side. Row 2 has the season titles, row 5 the section titles (ENTRIES, CALENDAR, STANDINGS (RACE BY RACE), STANDINGS (POINTS)), row 7 the column headers. Standings are cumulative points per round.
