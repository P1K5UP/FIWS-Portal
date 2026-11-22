-- FIWS custom administrator identity, MFA, sessions, recovery and staff logbook.
-- Additive only: existing applications, settings, storage and Auth users are untouched.
begin;

create table if not exists public.fiws_admin_accounts (
  id uuid primary key default gen_random_uuid(),
  username text not null,
  display_name text not null,
  admin_rank text not null default 'moderator'
    check (admin_rank in ('owner','administrator','moderator')),
  password_hash text not null,
  password_salt text not null,
  totp_secret_ciphertext text,
  totp_secret_iv text,
  totp_enabled boolean not null default false,
  disabled boolean not null default false,
  failed_login_count integer not null default 0 check (failed_login_count >= 0),
  locked_until timestamptz,
  password_changed_at timestamptz not null default now(),
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  created_by uuid references public.fiws_admin_accounts(id) on delete set null,
  updated_at timestamptz not null default now(),
  constraint fiws_admin_username_format check (username ~ '^[a-z0-9][a-z0-9._-]{2,31}$'),
  constraint fiws_admin_display_name_length check (length(display_name) between 1 and 80),
  constraint fiws_admin_totp_pair check (
    (totp_secret_ciphertext is null and totp_secret_iv is null and not totp_enabled)
    or (totp_secret_ciphertext is not null and totp_secret_iv is not null)
  )
);
create unique index if not exists fiws_admin_username_lower_uq
  on public.fiws_admin_accounts (lower(username));
create unique index if not exists fiws_single_owner_uq
  on public.fiws_admin_accounts ((admin_rank)) where admin_rank = 'owner';

create table if not exists public.fiws_admin_sessions (
  id uuid primary key default gen_random_uuid(),
  admin_id uuid not null references public.fiws_admin_accounts(id) on delete cascade,
  token_hash text not null unique check (length(token_hash) = 64),
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  expires_at timestamptz not null,
  revoked_at timestamptz,
  ip_hash text check (ip_hash is null or length(ip_hash) = 64),
  user_agent_hash text check (user_agent_hash is null or length(user_agent_hash) = 64)
);
create index if not exists fiws_admin_sessions_admin_active_idx
  on public.fiws_admin_sessions (admin_id, expires_at) where revoked_at is null;

create table if not exists public.fiws_admin_recovery_codes (
  id uuid primary key default gen_random_uuid(),
  admin_id uuid not null references public.fiws_admin_accounts(id) on delete cascade,
  code_hash text not null,
  created_at timestamptz not null default now(),
  used_at timestamptz
);
create index if not exists fiws_admin_recovery_unused_idx
  on public.fiws_admin_recovery_codes (admin_id) where used_at is null;

create table if not exists public.fiws_admin_bootstrap_state (
  singleton boolean primary key default true check (singleton),
  completed_at timestamptz,
  completed_by uuid references public.fiws_admin_accounts(id) on delete set null
);
insert into public.fiws_admin_bootstrap_state(singleton)
values (true) on conflict (singleton) do nothing;

create table if not exists public.fiws_staff_logbook (
  id uuid primary key default gen_random_uuid(),
  category text not null default 'general'
    check (category in ('general','handover','driver','team','application','incident','competition')),
  title text not null check (length(title) between 1 and 160),
  body text not null check (length(body) between 1 and 12000),
  related_reference text check (related_reference is null or length(related_reference) <= 120),
  pinned boolean not null default false,
  created_by uuid not null references public.fiws_admin_accounts(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_by uuid references public.fiws_admin_accounts(id) on delete set null,
  updated_at timestamptz not null default now(),
  archived_at timestamptz
);
create index if not exists fiws_staff_logbook_recent_idx
  on public.fiws_staff_logbook (created_at desc) where archived_at is null;
create index if not exists fiws_staff_logbook_category_idx
  on public.fiws_staff_logbook (category, created_at desc) where archived_at is null;

create table if not exists public.fiws_admin_audit_log (
  id bigint generated always as identity primary key,
  actor_admin_id uuid references public.fiws_admin_accounts(id) on delete set null,
  actor_username text not null,
  actor_rank text not null check (actor_rank in ('owner','administrator','moderator')),
  action text not null check (length(action) between 1 and 80),
  target_type text check (target_type is null or length(target_type) <= 80),
  target_id text check (target_id is null or length(target_id) <= 120),
  details jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now()
);
create index if not exists fiws_admin_audit_recent_idx
  on public.fiws_admin_audit_log (occurred_at desc);

-- These tables are accessible only through trusted Edge Functions using the service role.
alter table public.fiws_admin_accounts enable row level security;
alter table public.fiws_admin_sessions enable row level security;
alter table public.fiws_admin_recovery_codes enable row level security;
alter table public.fiws_admin_bootstrap_state enable row level security;
alter table public.fiws_staff_logbook enable row level security;
alter table public.fiws_admin_audit_log enable row level security;

revoke all on public.fiws_admin_accounts from anon, authenticated;
revoke all on public.fiws_admin_sessions from anon, authenticated;
revoke all on public.fiws_admin_recovery_codes from anon, authenticated;
revoke all on public.fiws_admin_bootstrap_state from anon, authenticated;
revoke all on public.fiws_staff_logbook from anon, authenticated;
revoke all on public.fiws_admin_audit_log from anon, authenticated;

grant all on public.fiws_admin_accounts to service_role;
grant all on public.fiws_admin_sessions to service_role;
grant all on public.fiws_admin_recovery_codes to service_role;
grant all on public.fiws_admin_bootstrap_state to service_role;
grant all on public.fiws_staff_logbook to service_role;
grant all on public.fiws_admin_audit_log to service_role;
grant usage, select on sequence public.fiws_admin_audit_log_id_seq to service_role;

commit;
