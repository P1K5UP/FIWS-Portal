# Supabase backend setup (FIWS)

FIWS remains hosted on GitHub Pages. Supabase provides shared persistence and authentication.

## Security model
- Browser clients may use only the Supabase project URL and publishable/anon key. Never put a service_role or secret key in HTML, JavaScript, GitHub Pages configuration, or this repository.
- Applicants use Supabase Auth sessions. Application rows are scoped to the authenticated user ID by PostgreSQL Row Level Security (RLS).
- Administrators must be provisioned by a trusted operator. Set app_metadata.fiws_role = "admin" using the Supabase dashboard or a trusted server-side admin tool. Never set admin role in user-editable metadata and never expose the service-role key.
- Public visitors can read site_settings only. Store public configuration there, never secrets or applicant data.
- Applicants can submit up to five applications per authenticated user per hour and read only their own records. The database trigger overrides client-supplied review fields.
- Only administrators can review, update, or delete applications and read the audit log.
- The audit log records action metadata, not application payloads or applicant PII.

## Applied Supabase setup
The following migrations are applied to the `fiws-portal` project and tracked in `supabase/migrations/` using the exact database migration versions:
- `20261122162330_fiws_shared_backend.sql`
- `20261122162341_fiws_policy_performance_hardening.sql`
- `20261122162550_fiws_public_asset_storage.sql`
- `20261122162729_fiws_application_identity_and_duplicate_guard.sql`
- `20261122162809_fiws_submission_ip_rate_limit.sql`
- `20261122163037_fiws_ip_limit_deny_policy.sql`

The website template now uses the project's URL and publishable key. These are public client configuration; RLS remains the security boundary. The `submit-application` Edge Function is deployed and applies a network-level HMACed IP rate limit plus the database per-account limit. It uses the Edge Function's secret-key context; no secret key is shipped to the browser.

## Remaining project configuration
1. In Supabase **Authentication → URL Configuration**, set the Site URL to `https://p1k5up.github.io/fiws-portal/` and add that exact URL as an allowed redirect URL. Also add the preview URL if you use a separate test deployment.
2. Confirm Email provider / magic-link sign-in is enabled. Supabase's default email sender is rate-limited; configure a custom SMTP provider before opening applications to the public.
3. Create the first staff account using **Admin → Staff sign-in** on the site and complete its email link. Then set `app_metadata.fiws_role` to `admin` for that exact account using a trusted dashboard/server-side process. Never set the role in user-editable metadata and never expose a secret key.
4. Test applicant and admin accounts separately before accepting applications. Confirm applicants can only read their own applications and only admins can read the queue, change decisions, upload workbooks, edit team colours, or publish logos.
5. Confirm the public `fiws-public` bucket contains only public website assets (workbooks and logos), never applicant data.
6. Add CAPTCHA/anti-bot controls before wide public launch. The deployed IP/account limits are defense in depth, not a complete bot defence.

## Tables
- site_settings: public shared settings such as team colour overrides, selected logo asset paths, and the published workbook pointer. Only admins can write.
- applications: applicant-owned submissions. Keep personal fields in application_data; never copy them into public settings, audit logs, or public status JSON. Applicants now retrieve their applications after signing in with a verified email link. The site does not expose a public reference-code lookup endpoint, avoiding reference-code enumeration and PII disclosure.
- admin_audit_log: administrator action metadata for traceability. It does not store changed values or applicant payloads.

## Migration and deployment notes
- Do not merge or publish the connected frontend until the allowed redirect URL is configured, the first admin is provisioned, and applicant/admin flows have been tested end-to-end.
- Existing browser-local applications, workbooks, colours, and logos are not automatically migrated. Export/import legacy applications only after matching each record to a verified applicant identity; do not assign arbitrary local records to an applicant account. Publish the workbook, team colours and logos from the authenticated Admin panel.
- Uploaded SVG logos are sanitized against an element/attribute allowlist and rasterized to PNG in the browser before upload. Uploaded logo images are rendered through a canvas pass that changes only neutral near-black/near-white pixels for the active theme; colored pixels and alpha are retained. Never inject uploaded SVG markup with innerHTML.
- Keep applicant status private. The portal currently requires a verified email sign-in and queries only the authenticated user's own rows under RLS.
- Define a retention/deletion schedule for application personal data before production use.
- Test RLS with separate applicant and admin accounts before deployment.
