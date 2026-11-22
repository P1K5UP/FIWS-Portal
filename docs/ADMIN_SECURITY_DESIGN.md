# FIWS administrator security and operations

## Current status

The custom administrator system is implemented on `feat/shared-supabase-backend` and deployed separately to the production Supabase project. The Owner account has been provisioned, signed in, and enrolled in authenticator-app MFA. The administrator panel and its normal features have been exercised by the site owner.

The website pull request remains open and unmerged. GitHub Pages production still publishes from `main`; this feature branch does not publish the website. Edge Function deployments and database migrations are separate from the GitHub Pages release.

This document describes the current system and the remaining verification gates. A passing GitHub Actions workflow does not replace live integration, security, or real-device testing.

## Administrator ranks

- **Owner:** manage administrator accounts and ranks, perform account recovery, and use all administrative features.
- **Administrator:** manage applications, published workbook, logos, team colours, normal portal settings and staff logbook entries.
- **Moderator:** review applications and contribute to the staff logbook. Cannot manage staff accounts, ranks or security configuration.
- There is no Steward website role.

Authorization is checked server-side in `fiws-admin`; hiding a browser control is never treated as an authorization boundary. Database procedures also validate privileged operations.

## Authentication and session design

- Staff use a provisioned username and password. There is no public staff registration or email-based administrator login.
- Passwords are hashed server-side with Argon2id (19 MiB memory, two iterations, one lane). Passwords and hashes are never returned to the browser.
- TOTP authenticator-app MFA is mandatory. TOTP secrets are encrypted server-side using AES-GCM and the stable `FIWS_TOTP_ENCRYPTION_KEY`.
- Login throttling is enforced atomically by normalized username and network source. Password and MFA failures receive progressive throttling; credential errors are intentionally generic.
- Sessions use random opaque bearer tokens. Only SHA-256 hashes are stored in Postgres; server-side expiry and revocation are enforced. The absolute session lifetime is eight hours.
- The browser holds the opaque session token in page memory only, not localStorage or sessionStorage. Reloading the page requires a new sign-in. This is intentional.
- Recovery codes are generated once, shown once, stored as hashes and individually consumed. Owner recovery uses a separate one-time server-side secret.

## Applicant workflow

Applicants do not create Supabase Auth accounts and do not receive verification or status emails. The email field is contact information for league staff only.

The public `submit-application` function generates a reference code containing 13 cryptographically random bytes (104 bits), displayed as `FIWS-` plus 26 uppercase hexadecimal characters. The code is the credential for status lookup. The latest code may be remembered in a first-party cookie after the visitor chooses the necessary-cookie option; manual entry always remains available.

The status endpoint returns only the applicant name, application type, series, status and staff note. It does not return the contact email or full application payload. Application table access is restricted to the server-side service role; public submission and lookup are mediated by the rate-limited Edge Function.

Accepted and rejected applications are deleted by a Postgres `pg_cron` job once they are at least 24 hours past `decided_at`. The job runs every five minutes, so deletion can occur up to five minutes after the 24-hour point. Resetting an application to pending must clear its decision timestamp.

## Server-side functions and secrets

The active website API functions are:

- `fiws-admin`: custom admin authentication, MFA, session validation, rank-checked staff operations and shared admin data.
- `submit-application`: public application submission and reference-code status lookup.

Both functions validate the request Origin against the exact allowlist:
- `https://p1k5up.github.io`
- `http://localhost:8000`

The service-role key is read only from the Edge Function environment. The following secrets are also server-side only:

- `FIWS_BOOTSTRAP_SECRET`
- `FIWS_TOTP_ENCRYPTION_KEY`
- `FIWS_RATE_LIMIT_PEPPER`
- `FIWS_OWNER_RECOVERY_SECRET`

Never commit these values, place them in website code, include them in a browser request, or send them in chat. The TOTP encryption key must remain stable; losing it makes existing authenticator secrets undecryptable. The bootstrap and owner-recovery secrets are sensitive one-time capabilities and should be removed/rotated when their documented use is complete.

The legacy `bootstrap-fiws-admins` function remains active as a separate older deployment. It is not part of the normal custom-admin login flow. Review its remaining need and access controls before deliberately retiring it; do not remove it as an incidental frontend change.

## Database and migrations

The migrations in `supabase/migrations/` cover the shared backend, storage, application validation and rate limits, custom admin accounts/sessions/MFA/recovery/logbook/audit, atomic privileged operations, service-role settings access, reference-code applications, service-role-only application table access, and scheduled application cleanup.

These production migrations have already been applied. Treat existing migration files as immutable history. For future schema changes, add a new timestamped migration, review its grants/RLS/security-definer behavior, test it against a non-production project where possible, and obtain approval before applying it to production.

Custom administrator tables deny direct access to `anon` and `authenticated` roles. Application rows are similarly unavailable to browser roles. Service-role access is used only from the Edge Functions. Public Storage is reserved for public site assets such as logos and published workbooks; never put applicant or administrator data there.

## Operational verification before public rollout

The following checks remain separate from CI and should be completed before the website is merged/published:

1. Exercise every rank against both allowed and denied actions, including account creation, rank changes, disable/re-enable, password reset, session revocation and logbook permissions.
2. Exercise MFA enrollment, TOTP replay resistance, login throttling, recovery-code consumption and the one-time Owner recovery procedure using controlled test accounts.
3. Run a controlled applicant lifecycle: submit, retain/copy code, check status, accept/reject, reset to pending, delete manually, and verify scheduled 24-hour cleanup. Do not use real applicant data for test submissions.
4. Review the still-active legacy `bootstrap-fiws-admins` function and deliberately decide whether to retain or retire it.
5. Confirm database backup and restore arrangements and that the 24-hour post-decision application retention meets league requirements.
6. Test the released site on real iOS and Android devices, including the fixed bottom navigation, safe-area spacing, keyboard behavior, forms, tables and admin panel.

The owner has confirmed the Discord widget and admin features render/work. The latest GitHub Actions run has passed the build, Edge Function type checks, regression tests and inline JavaScript syntax check. Physical-device testing and the broader controlled end-to-end checks above have not been claimed as complete.

## Release boundaries

- Website source changes stay on `feat/shared-supabase-backend` until the pull request is reviewed and release approval is given.
- GitHub Pages publishes from `main`; a feature-branch commit does not update the public site.
- Deploying an Edge Function or applying a database migration is a separate production action. Do not infer approval for backend deployment from approval to merge frontend code.
- Never merge, publish, disable a production function, rotate secrets or apply an ad-hoc production SQL change without explicit authorization.
