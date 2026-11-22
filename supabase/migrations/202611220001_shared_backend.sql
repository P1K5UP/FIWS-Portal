-- FIWS shared backend foundation
-- Apply with the Supabase SQL editor or Supabase CLI migrations.
-- Never put a service_role key in the browser.
begin;
create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated;

create or replace function private.is_fiws_admin()
returns boolean language sql stable security invoker set search_path = ''
as $$ select coalesce((auth.jwt() -> 'app_metadata' ->> 'fiws_role') = 'admin', false); $$;
revoke all on function private.is_fiws_admin() from public, anon;
grant execute on function private.is_fiws_admin() to authenticated;

create table if not exists public.site_settings (
 setting_key text primary key check (length(setting_key) between 1 and 80),
 setting_value jsonb not null default '{}'::jsonb,
 updated_at timestamptz not null default now(),
 updated_by uuid references auth.users(id) on delete set null
);
create table if not exists public.applications (
 id uuid primary key default gen_random_uuid(),
 applicant_id uuid not null references auth.users(id) on delete cascade,
 reference_code text not null unique check (length(reference_code) between 6 and 32),
 application_data jsonb not null,
 status text not null default 'pending' check (status in ('pending','accepted','rejected')),
 staff_note text,
 created_at timestamptz not null default now(),
 decided_at timestamptz,
 decided_by uuid references auth.users(id) on delete set null,
 constraint application_data_is_object check (jsonb_typeof(application_data) = 'object'),
 constraint application_data_size check (octet_length(application_data::text) <= 20000),
 constraint staff_note_size check (staff_note is null or length(staff_note) <= 1000)
);
create index if not exists applications_applicant_created_idx on public.applications (applicant_id, created_at desc);
create index if not exists applications_status_created_idx on public.applications (status, created_at desc);

create table if not exists public.admin_audit_log (
 id bigint generated always as identity primary key,
 actor_id uuid references auth.users(id) on delete set null,
 action text not null check (length(action) <= 80),
 record_type text not null check (length(record_type) <= 80),
 record_id text,
 occurred_at timestamptz not null default now()
);
create index if not exists admin_audit_log_occurred_idx on public.admin_audit_log (occurred_at desc);

create or replace function private.guard_application_insert()
returns trigger language plpgsql security invoker set search_path = ''
as $$
declare recent_count integer;
begin
 if auth.uid() is null or new.applicant_id <> auth.uid() then
  raise exception 'Invalid applicant identity' using errcode = '42501';
 end if;
 if jsonb_typeof(new.application_data) <> 'object' or octet_length(new.application_data::text) > 20000 then
  raise exception 'Invalid application payload';
 end if;
 perform pg_advisory_xact_lock(hashtextextended(auth.uid()::text, 0));
 select count(*) into recent_count from public.applications a
 where a.applicant_id = auth.uid() and a.created_at > now() - interval '1 hour';
 if recent_count >= 5 then raise exception 'Application submission limit reached' using errcode = 'P0001'; end if;
 new.status := 'pending';
 new.staff_note := null;
 new.decided_at := null;
 new.decided_by := null;
 new.created_at := now();
 return new;
end;
$$;
revoke all on function private.guard_application_insert() from public, anon, authenticated;
drop trigger if exists applications_guard_insert on public.applications;
create trigger applications_guard_insert before insert on public.applications
for each row execute function private.guard_application_insert();

create or replace function private.audit_admin_change()
returns trigger language plpgsql security definer set search_path = ''
as $$
declare target_id text; action_name text;
begin
 if tg_table_name = 'site_settings' then
  if tg_op = 'DELETE' then target_id := old.setting_key; else target_id := new.setting_key; end if;
  action_name := lower(tg_op);
 elsif tg_op = 'DELETE' then
  target_id := old.id::text; action_name := lower(tg_op);
 else
  target_id := new.id::text; action_name := lower(tg_op);
 end if;
 insert into public.admin_audit_log(actor_id, action, record_type, record_id)
 values (auth.uid(), action_name, tg_table_name, target_id);
 if tg_op = 'DELETE' then return old; end if;
 return new;
end;
$$;
revoke all on function private.audit_admin_change() from public, anon, authenticated;
drop trigger if exists site_settings_audit on public.site_settings;
create trigger site_settings_audit after insert or update or delete on public.site_settings
for each row execute function private.audit_admin_change();
drop trigger if exists applications_audit on public.applications;
create trigger applications_audit after update or delete on public.applications
for each row when (private.is_fiws_admin()) execute function private.audit_admin_change();

alter table public.site_settings enable row level security;
alter table public.applications enable row level security;
alter table public.admin_audit_log enable row level security;
revoke all on public.site_settings from anon, authenticated;
revoke all on public.applications from anon, authenticated;
revoke all on public.admin_audit_log from anon, authenticated;
grant select on public.site_settings to anon, authenticated;
grant insert, update, delete on public.site_settings to authenticated;
grant select, insert, update, delete on public.applications to authenticated;
grant select on public.admin_audit_log to authenticated;

drop policy if exists "Public can read published settings" on public.site_settings;
create policy "Public can read published settings" on public.site_settings for select to anon, authenticated using (true);
drop policy if exists "Admins manage settings" on public.site_settings;
create policy "Admins manage settings" on public.site_settings for all to authenticated
using (public.is_fiws_admin()) with check (public.is_fiws_admin());

drop policy if exists "Applicants read their own application" on public.applications;
create policy "Applicants read their own application" on public.applications for select to authenticated
using (applicant_id = auth.uid() or public.is_fiws_admin());
drop policy if exists "Applicants submit as themselves" on public.applications;
create policy "Applicants submit as themselves" on public.applications for insert to authenticated
with check (applicant_id = auth.uid() and status = 'pending');
drop policy if exists "Admins update applications" on public.applications;
create policy "Admins update applications" on public.applications for update to authenticated
using (public.is_fiws_admin()) with check (public.is_fiws_admin());
drop policy if exists "Admins delete applications" on public.applications;
create policy "Admins delete applications" on public.applications for delete to authenticated
using (public.is_fiws_admin());
drop policy if exists "Admins read audit log" on public.admin_audit_log;
create policy "Admins read audit log" on public.admin_audit_log for select to authenticated
using (public.is_fiws_admin());
commit;
