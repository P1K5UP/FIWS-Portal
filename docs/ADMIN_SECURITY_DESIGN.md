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
- Login throttles atomically by normalized username and network source, applies progressive account and network lockouts to password and MFA failures, and returns generic credential errors to reduce account enumeration.
- Sessions are random opaque bearer tokens; only SHA-256 token hashes are stored in Postgres. An eight-hour absolute expiry and server-side revocation are enforced; browser memory-only storage means reload requires a fresh login.
- Because the website is hosted on GitHub Pages and the API is on a different site (Supabase), browser third-party-cookie restrictions make cross-site HttpOnly cookies unreliable. The browser keeps the opaque bearer token in page memory only (not localStorage or sessionStorage) and sends it over HTTPS. Reloading the page requires a fresh login; the server-side session expires after eight hours. This avoids leaving an admin token in persistent browser storage. Strong CSP and safe DOM handling remain important XSS defenses.
- Recovery codes are generated once, displayed once, stored only as hashes, and individually consumed. A higher-ranked administrator can reset a lower-ranked account. Owner recovery uses a separately configured, one-time server secret and is never exposed to the browser. It resets the owner password and MFA, revokes sessions, and consumes the emergency secret.
- Initial owner bootstrap is a one-time Edge Function operation protected by a server-side secret configured outside Git. It becomes permanently unavailable after successful creation.

## Staff memory and audit
The shared staff logbook stores general notes, handovers, driver/team/application/incident/competition notes, optional related references, and author/timestamp attribution. The current website interface supports creating and reading entries; the API also supports updates and archiving. Audit entries record administrative security and moderation actions without copying applicant PII or passwords into the audit stream. Logbook and audit reads/writes are rank-checked server-side.

## Database
The additive migrations `20261122175332_fiws_admin_identity_logbook.sql`, `20261122175349_fiws_admin_mfa_login_hardening.sql`, `20261122175630_fiws_totp_replay_protection.sql`, `20261122175748_fiws_admin_atomic_login_throttle.sql`, `20261122175846_fiws_owner_recovery_gate.sql`, `20261122175855_fiws_retire_legacy_auth_admin_policies.sql`, `20261122183000_fiws_atomic_admin_recovery.sql`, `20261122184500_fiws_atomic_owner_bootstrap.sql`, `20261122190000_fiws_atomic_mfa_enrollment.sql`, and `20261122191500_fiws_atomic_admin_account_lifecycle.sql` add custom admin accounts, sessions, recovery codes, bootstrap state, staff logbook, audit, MFA replay protection, atomic login throttling, and remove the old Supabase Auth admin policies. Existing applications, settings, Auth users, and Storage objects are not rewritten. All custom-admin tables deny direct access to anon/authenticated roles; Edge Functions use server-side service credentials.

## Deployment gates (must all pass before public rollout)
1. In Supabase → Edge Functions → Secrets, configure `FIWS_BOOTSTRAP_SECRET` (at least 40 random characters), `FIWS_TOTP_ENCRYPTION_KEY` (base64 encoding of exactly 32 random bytes), and `FIWS_RATE_LIMIT_PEPPER` (at least 32 random characters), and `FIWS_OWNER_RECOVERY_SECRET` (at least 40 random characters; store offline and only use for a one-time emergency). Never put these in the repository. The Supabase service-role key is read only from the function environment. Never expose any of these secrets in HTML or a public browser request.
2. Apply the additive migration and verify RLS, grants, constraints, and advisors.
3. Deploy `fiws-admin` with JWT verification disabled only because it validates its own opaque sessions. The function enforces the exact GitHub Pages Origin, checks all admin sessions server-side, and uses only server-side service credentials. Run automated tests for login, TOTP, replay resistance, brute-force throttling, recovery, role escalation, session revocation, CORS and origin checks.
4. Create the initial Owner by sending a POST to `/functions/v1/fiws-admin` with `{"action":"bootstrap","username":"...","display_name":"...","password":"..."}` and the `x-fiws-bootstrap-secret` header from a trusted local terminal. Never put the bootstrap secret in the website. The function permits bootstrap only while no admin exists and permanently marks it complete after success. Then sign in on the website, enroll MFA, generate and safely store recovery codes.
5. Create the second admin through the owner UI and test every rank against the permission matrix.
6. The custom API source includes rank-checked application review, settings writes, asset upload/delete, logbook, account creation/rank changes/disable, password reset, recovery, and session operations. Direct Auth-claim-based database write permissions have been removed; public applicant access remains scoped to each applicant's own records. Verify every operation against each rank before removing old admin access.
7. Verify applicant flows separately; applicant email authentication is not being changed in this admin-only redesign.
8. Retire the old email-based admin bootstrap only after the new owner has successfully logged in with MFA and all staff operations pass.
9. Do not merge the PR or change GitHub Pages deployment until end-to-end tests pass.

The emergency owner recovery action is `owner-recover`; send the one-time secret in `x-fiws-owner-recovery-secret` from a trusted local terminal with a new password. The endpoint consumes the recovery gate and resets MFA; immediately remove `FIWS_OWNER_RECOVERY_SECRET` from project secrets after use.

## Explicitly not included
Replacing Supabase/Postgres, moving hosting away from GitHub Pages, changing applicant authentication, or deleting existing Supabase Auth users. Those are separate architectural decisions.

## Generate and configure server secrets

Generate these on your own computer with OpenSSL (do not send them to anyone):
```sh
openssl rand -hex 32       # FIWS_BOOTSTRAP_SECRET
openssl rand -base64 32    # FIWS_TOTP_ENCRYPTION_KEY
openssl rand -hex 32       # FIWS_RATE_LIMIT_PEPPER
openssl rand -hex 32       # FIWS_OWNER_RECOVERY_SECRET
```
In Supabase Dashboard → Edge Functions → Secrets, add each value under the matching name. Keep the bootstrap and owner recovery secrets in a password manager or offline secure store. Never put them in GitHub, the website, or chat. The TOTP encryption key must remain stable: losing it makes existing authenticator secrets undecryptable.

After the secrets are configured, deploy the fiws-admin Edge Function with JWT verification disabled (it validates its own random session tokens and rejects every non-allowlisted browser Origin). The public website uses only the publishable key; all service credentials stay in the Edge Function environment.

## Bootstrap request example (run locally, never from the browser)
Use a local terminal after configuring secrets and deploying the function. Keep the secret out of shell history and do not paste it into chat:
```sh
read -rsp "FIWS bootstrap secret: " FIWS_BOOTSTRAP_SECRET; echo
read -rp "Owner username: " FIWS_OWNER_USERNAME
read -rp "Owner display name: " FIWS_OWNER_NAME
read -rsp "Owner password (14+ chars): " FIWS_OWNER_PASSWORD; echo
read -rsp "Supabase publishable key: " FIWS_PUBLISHABLE_KEY; echo
export FIWS_BOOTSTRAP_SECRET FIWS_OWNER_USERNAME FIWS_OWNER_NAME FIWS_OWNER_PASSWORD FIWS_PUBLISHABLE_KEY
python3 - <<'PY'
import json, os, urllib.request
payload = {
    "action": "bootstrap",
    "username": os.environ["FIWS_OWNER_USERNAME"],
    "display_name": os.environ["FIWS_OWNER_NAME"],
    "password": os.environ["FIWS_OWNER_PASSWORD"],
}
request = urllib.request.Request(
    "https://yipzokjzqltxcufixrsv.supabase.co/functions/v1/fiws-admin",
    data=json.dumps(payload).encode(),
    headers={
        "Origin": "https://p1k5up.github.io",
        "apikey": os.environ["FIWS_PUBLISHABLE_KEY"],
        "Content-Type": "application/json",
        "x-fiws-bootstrap-secret": os.environ["FIWS_BOOTSTRAP_SECRET"],
    },
    method="POST",
)
with urllib.request.urlopen(request) as response:
    print(response.read().decode())
PY
unset FIWS_BOOTSTRAP_SECRET FIWS_OWNER_PASSWORD FIWS_PUBLISHABLE_KEY
```
Replace the publishable key placeholder with the existing public key from project configuration. If Python is unavailable, construct the JSON request locally without placing the secret in the URL. The bootstrap secret is a one-time capability; rotate or remove it after successful bootstrap.

## Current implementation status
The custom admin database schema and the removal of legacy Auth-claim admin policies have been applied additively and verified. The Edge Function and website integration are in the feature branch; they are not yet deployed/merged. Required secrets are not configured by this repository change. Do not treat the admin system as production-ready until the deployment gates and browser/API tests pass.
