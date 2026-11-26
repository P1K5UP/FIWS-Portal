-- Restore the service-role access required by the application submission workflow.
-- These grants are idempotent and match the verified production catalog.
begin;

grant select, insert, update, delete on table public.applications to service_role;
grant select, insert, update, delete on table public.application_ip_limits to service_role;

commit;
