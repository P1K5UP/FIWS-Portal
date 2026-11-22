# FIWS administrator security redesign

## Scope and compatibility
This is an additive redesign on the existing FIWS shared-backend branch. It does not delete or rewrite applications, site settings, Storage objects, workbook data, or existing Supabase Auth users. Applicant email verification remains unchanged for now; administrator sign-in is being separated from Supabase Auth so admin login no longer sends email.

## Administrator ranks
- **Owner**: bootstrap authority, create/disable admins, assign ranks, reset other accounts, manage security configuration, and perform all admin operations. At least one owner must always remain.
- **Administrator**: manage applications, published workbook, logos, team colours, and normal portal settings; manage logbook entries.
- **Moderator**: review applications and contribute to the staff logbook. Cannot create/disable staff accounts, change ranks, or alter security configuration.
- There is deliberately no Steward website role.

All authorization is enforced in Edge Functions, never by hiding UI controls. The database tables for custom admin identities are RLS-enabled and inaccessible to anon/authenticated clients.

## Authentication design
- Unique username and password; no public staff registration and no email-based admin login.
- Password hashes use per-account random salts and a server-side, deliberately expensive password KDF. The implementation must use a supported, reviewed implementation and document its parameters; passwords are never returned or logged.
- TOTP authenticator-app MFA is mandatory for every admin. New accounts remain pending until MFA enrollment is confirmed.
- Login throttles by normalized username and network source, uses progressive lockouts, and returns generic credential errors to reduce account enumeration.
- Sessions are random opaque bearer tokens; only SHA-256 token hashes are stored in Postgres. Short absolute and idle expiry, revocation, and rotation are enforced server-side.
- Because the website is hosted on GitHub Pages and the API is on a different site (Supabase), browser third-party-cookie restrictions make cross-site HttpOnly cookies unreliable. The planned browser session is therefore held in sessionStorage (not localStorage) and sent as a bearer token over HTTPS; it is short-lived and is cleared on logout/tab close. Strong CSP and safe DOM handling remain important XSS defenses.
- Recovery codes are generated once, displayed once, stored only as hashes, and individually consumed. A higher-ranked administrator can reset a lower-ranked account. Owner recovery uses a separately configured, one-time server secret and is never exposed to the browser.
- Initial owner bootstrap is a one-time Edge Function operation protected by a server-side secret configured outside Git. It becomes permanently unavailable after successful creation.

## Staff memory and audit
The shared staff logbook supports general notes, handovers, driver/team/application/incident/competition notes, optional related references, pinning, archiving, search, and author/timestamp attribution. Audit entries record administrative security and moderation actions without copying applicant PII or passwords into the audit stream. Logbook and audit reads/writes are rank-checked server-side.

## Database
The migration `20261122173000_fiws_admin_identity_logbook.sql` adds custom admin accounts, sessions, recovery codes, bootstrap state, staff logbook and admin audit tables. It is additive and does not alter existing tables. All custom-admin tables deny direct access to anon/authenticated roles; Edge Functions use server-side service credentials.

## Deployment gates (must all pass before public rollout)
1. Configure strong random Edge Function secrets for bootstrap, TOTP encryption, and recovery; never put them in the repository.
2. Apply the additive migration and verify RLS, grants, constraints, and advisors.
3. Deploy the custom-admin Edge Function only after source review and automated tests for login, TOTP, replay resistance, brute-force throttling, recovery, role escalation, session revocation, CORS and origin checks.
4. Create the initial owner through the one-time bootstrap, enroll MFA, generate and safely store recovery codes.
5. Create the second admin through the owner UI and test every rank against the permission matrix.
6. Move all privileged application/settings/Storage operations behind the Edge Function before removing old admin access.
7. Verify applicant flows separately; applicant email authentication is not being changed in this admin-only redesign.
8. Retire the old email-based admin bootstrap only after the new owner has successfully logged in with MFA and all staff operations pass.
9. Do not merge the PR or change GitHub Pages deployment until end-to-end tests pass.

## Explicitly not included
Replacing Supabase/Postgres, moving hosting away from GitHub Pages, changing applicant authentication, or deleting existing Supabase Auth users. Those are separate architectural decisions.
