-- Remove the legacy one-owner-only index left behind by the original admin schema.
-- Multiple owners are supported; fiws_owner_create_admin enforces owner authorization.
drop index if exists public.fiws_single_owner_uq;
