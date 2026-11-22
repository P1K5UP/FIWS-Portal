-- Keep all application reads and writes behind the server-side service role.
begin;
revoke all on public.applications from anon, authenticated;
drop policy if exists "Applicants read their own application" on public.applications;
drop policy if exists "Applicants submit as themselves" on public.applications;
drop policy if exists "Admins update applications" on public.applications;
drop policy if exists "Admins delete applications" on public.applications;
commit;
