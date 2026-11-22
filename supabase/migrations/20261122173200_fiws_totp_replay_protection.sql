begin;
alter table public.fiws_admin_accounts add column if not exists totp_last_step bigint;
commit;