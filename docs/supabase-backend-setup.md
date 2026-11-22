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

## Apply the migration
1. Create a Supabase project. Keep its URL and publishable key out of the SQL migration.
2. Enable the authentication method selected by the frontend integration. Anonymous sign-in can support the initial migration, but should be paired with abuse controls.
3. Run supabase/migrations/202611220001_shared_backend.sql in the Supabase SQL editor, or apply it with the Supabase CLI.
4. Create the first administrator through a trusted process that writes fiws_role: admin into that user's app_metadata. Do not provide public admin registration.
5. Configure the frontend with the project URL and publishable key. These are public client configuration; RLS is the security boundary.
6. Before accepting real applications, add an Edge Function or equivalent server-side submission endpoint with IP-based rate limiting and CAPTCHA/abuse checks. The per-user database limit is defense in depth, not a substitute for IP-based controls.

## Tables
- site_settings: public shared settings such as team colour overrides, selected logo asset paths, and the published workbook pointer. Only admins can write.
- applications: applicant-owned submissions. Keep personal fields in application_data; never copy them into public settings, audit logs, or public status JSON. The initial schema intentionally does not provide public lookup by reference code and email; that endpoint needs a separately rate-limited server-side function to avoid reference-code enumeration and PII disclosure.
- admin_audit_log: administrator action metadata for traceability. It does not store changed values or applicant payloads.

## Migration and deployment notes
- Do not switch the live frontend to Supabase until the project URL, publishable key, auth flow, and storage policies are configured and tested.
- Existing browser-local applications, workbooks, colours, and logos are not automatically migrated. Export/import them through an authenticated one-time admin migration workflow; do not bulk-upload localStorage contents from arbitrary visitors.
- Validate and sanitize uploaded logos. Prefer raster images or sanitize SVGs server-side before publishing them. Never inject uploaded SVG markup with innerHTML.
- Keep applicant status private. Cross-device status lookup should use a verified email magic link or a rate-limited Edge Function returning only minimum status fields.
- Define a retention/deletion schedule for application personal data before production use.
- Test RLS with separate applicant and admin accounts before deployment.
