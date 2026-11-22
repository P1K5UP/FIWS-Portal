begin;
alter table public.fiws_admin_bootstrap_state add column if not exists owner_recovery_used_at timestamptz;
commit;