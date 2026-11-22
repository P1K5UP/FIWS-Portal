begin;
alter table public.fiws_admin_sessions add column if not exists mfa_verified boolean not null default false;
create table if not exists public.fiws_admin_login_limits (
 username_key text not null,
 ip_hash text not null check(length(ip_hash)=64),
 window_started_at timestamptz not null default now(),
 attempts integer not null default 0 check(attempts>=0),
 locked_until timestamptz,
 primary key(username_key,ip_hash)
);
alter table public.fiws_admin_login_limits enable row level security;
revoke all on public.fiws_admin_login_limits from anon,authenticated;
grant all on public.fiws_admin_login_limits to service_role;
create index if not exists fiws_admin_accounts_created_by_idx on public.fiws_admin_accounts(created_by);
create index if not exists fiws_admin_audit_actor_idx on public.fiws_admin_audit_log(actor_admin_id);
create index if not exists fiws_admin_bootstrap_completed_by_idx on public.fiws_admin_bootstrap_state(completed_by);
create index if not exists fiws_staff_logbook_created_by_idx on public.fiws_staff_logbook(created_by);
create index if not exists fiws_staff_logbook_updated_by_idx on public.fiws_staff_logbook(updated_by);
commit;