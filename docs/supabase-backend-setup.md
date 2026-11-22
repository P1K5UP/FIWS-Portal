# Supabase backend operations (FIWS)

FIWS is hosted on GitHub Pages. Supabase provides shared persistence and the server-side API. The frontend and backend have separate release lifecycles.

## Current production model

- The public site is `https://p1k5up.github.io/fiws-portal/`; its browser origin is `https://p1k5up.github.io`.
- The browser contains only the Supabase project URL and publishable/anon key. The service-role key and all other secrets remain in Edge Function environment variables.
- `fiws-admin` provides custom username/password authentication, mandatory TOTP MFA, opaque revocable sessions, rank checks, account management, application moderation, shared settings/assets and staff logbook operations. Its JWT verification is disabled because it validates its own session tokens.
- `submit-application` is a public endpoint for applicant submission and reference-code status lookup. It validates the exact allowed Origin, validates input and applies HMACed network rate limiting. It uses service-role access server-side; browser clients cannot read or write application rows directly.
- Applications do not require applicant Supabase Auth accounts. Contact email is stored for staff follow-up only; no applicant verification or status email is sent.
- The latest application reference code can be stored in a first-party cookie after necessary-cookie consent. Manual code entry remains supported.
- Accepted/rejected applications are scheduled for deletion 24 hours after the decision, with a five-minute cleanup interval.

## Administrator security

Administrator authorization is enforced in the Edge Function and database procedures. The custom admin identity, session, recovery, MFA, audit and logbook tables are not directly accessible to anon/authenticated browser roles. Passwords are Argon2id-hashed server-side; TOTP secrets are encrypted with the server-side `FIWS_TOTP_ENCRYPTION_KEY`; recovery codes are stored as hashes and individually consumed. Session tokens are random and only their SHA-256 hashes are stored server-side.

The website keeps the opaque session token in memory only. A page reload therefore requires a fresh administrator sign-in. This is intentional and avoids persistent browser storage of an admin bearer token.

Never:
- Put the service-role key or any Edge Function secret in HTML, JavaScript, a public repository, GitHub Pages settings, or a browser request.
- Grant browser roles direct access to application rows or custom admin tables.
- Set administrator permissions in user-editable Auth metadata.
- Use production applicant data or secrets in screenshots, test fixtures or support messages.

## Applied database migrations

The repository tracks the migrations used for the shared backend, admin security and reference-code workflow. The later migrations include:
- Custom admin identity, MFA, session, recovery, atomic throttling, bootstrap and account lifecycle procedures.
- Service-role access to the shared `site_settings` API path.
- Reference-code applications and service-role-only application table access.
- Scheduled deletion of accepted/rejected applications after 24 hours.
- Service-role execution permission for the legacy application audit helper used during status updates.

The exact migration files and versions are in `supabase/migrations/`. Production migrations are already applied for the current implementation; do not replay or edit historical migrations to make a new change. Add a new, timestamped migration for any future schema change and review it before applying it to production.

## Edge Functions and operational safeguards

The active frontend API functions are:
- `fiws-admin`
- `submit-application`

Both functions allow the production GitHub Pages origin and the local development origin `http://localhost:8000`. If a legitimate deployment origin changes, update and review the allowlist in both function sources, test preflight and POST requests, then deploy each function separately. Do not broaden the allowlist to arbitrary origins.

The legacy `bootstrap-fiws-admins` function is a separate older deployment. It should be reviewed and retired deliberately after confirming it is no longer required; it is not part of the normal website login flow. Do not remove it automatically during a site release.

Application cleanup is scheduled in Postgres using `pg_cron`. The job runs every five minutes and deletes rows whose status is accepted/rejected and whose `decided_at` is at least 24 hours old. A reset-to-pending operation should clear the decision timestamp; verify that behavior if changing moderation logic.

## Frontend development and release

1. Work on `feat/shared-supabase-backend` and run `python3 build.py`.
2. Serve locally with `python3 -m http.server 8000`; use the local URL rather than `file://`.
3. Validate the relevant applicant and administrator workflows without using real applicant data.
4. Check the GitHub Actions workflow on the pull request. It builds the self-contained site, type-checks both active Edge Functions, runs regression tests and checks inline JavaScript syntax.
5. Review the PR diff and confirm the production branch remains unchanged until release approval.
6. Merge/publish the website only after explicit approval. Backend function deployments and database migrations are separate operations and require their own review/approval.

## Production verification still required before public launch

- Test the complete applicant submit → reference code → status lookup → accepted/rejected → 24-hour cleanup lifecycle with controlled test data.
- Verify all administrator ranks against the permission matrix, including denied actions, session revocation, recovery, MFA replay resistance and owner recovery.
- Confirm the legacy bootstrap function is either deliberately retained with documented controls or safely retired.
- Test the site on real iOS and Android devices and check the fixed mobile navigation, safe-area spacing, forms and keyboard behavior.
- Confirm current backup/restore arrangements and the retention policy meet league requirements.

Do not interpret a passing frontend CI run as proof of live Supabase integration, production security, or physical-device compatibility.

## Storage

The public `fiws-public` bucket is for public website assets such as published workbooks and logos only. Never store applicant personal data, admin records, secrets or private documents in a public bucket. Shared settings store public presentation configuration and pointers, not credentials or applicant payloads.
