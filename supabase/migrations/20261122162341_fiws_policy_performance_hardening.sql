-- FIWS RLS and index tuning (verified against Supabase advisors).
begin;
create index if not exists site_settings_updated_by_idx on public.site_settings(updated_by);
create index if not exists applications_decided_by_idx on public.applications(decided_by);
create index if not exists admin_audit_log_actor_id_idx on public.admin_audit_log(actor_id);

drop policy if exists "Admins manage settings" on public.site_settings;
create policy "Admins insert settings" on public.site_settings for insert to authenticated
with check ((select private.is_fiws_admin()));
create policy "Admins update settings" on public.site_settings for update to authenticated
using ((select private.is_fiws_admin())) with check ((select private.is_fiws_admin()));
create policy "Admins delete settings" on public.site_settings for delete to authenticated
using ((select private.is_fiws_admin()));

drop policy if exists "Applicants read their own application" on public.applications;
create policy "Applicants read their own application" on public.applications for select to authenticated
using ((select auth.uid()) = applicant_id or (select private.is_fiws_admin()));
drop policy if exists "Applicants submit as themselves" on public.applications;
create policy "Applicants submit as themselves" on public.applications for insert to authenticated
with check ((select auth.uid()) = applicant_id and status = 'pending');
drop policy if exists "Admins update applications" on public.applications;
create policy "Admins update applications" on public.applications for update to authenticated
using ((select private.is_fiws_admin())) with check ((select private.is_fiws_admin()));
drop policy if exists "Admins delete applications" on public.applications;
create policy "Admins delete applications" on public.applications for delete to authenticated
using ((select private.is_fiws_admin()));
drop policy if exists "Admins read audit log" on public.admin_audit_log;
create policy "Admins read audit log" on public.admin_audit_log for select to authenticated
using ((select private.is_fiws_admin()));
commit;
