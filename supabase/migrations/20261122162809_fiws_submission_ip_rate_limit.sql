-- HMACed IP rate limiting for the public application submission Edge Function.
begin;
create table if not exists public.application_ip_limits (
 ip_hash text primary key check (length(ip_hash) = 64),
 window_started_at timestamptz not null default now(),
 request_count integer not null default 1 check (request_count >= 1)
);
alter table public.application_ip_limits enable row level security;
revoke all on public.application_ip_limits from public, anon, authenticated;
grant select, insert, update, delete on public.application_ip_limits to service_role;

create or replace function public.consume_fiws_ip_limit(p_ip_hash text)
returns boolean language plpgsql security definer set search_path = ''
as $$
declare current_count integer;
begin
 if p_ip_hash is null or length(p_ip_hash) <> 64 or p_ip_hash !~ '^[0-9a-f]{64}$' then
  raise exception 'Invalid rate limit key';
 end if;
 insert into public.application_ip_limits(ip_hash, window_started_at, request_count)
 values (p_ip_hash, now(), 1)
 on conflict (ip_hash) do update set
  window_started_at = case
   when public.application_ip_limits.window_started_at <= now() - interval '1 hour' then now()
   else public.application_ip_limits.window_started_at end,
  request_count = case
   when public.application_ip_limits.window_started_at <= now() - interval '1 hour' then 1
   else public.application_ip_limits.request_count + 1 end
 returning request_count into current_count;
 delete from public.application_ip_limits where window_started_at < now() - interval '7 days';
 return current_count <= 10;
end;
$$;
revoke all on function public.consume_fiws_ip_limit(text) from public, anon, authenticated;
grant execute on function public.consume_fiws_ip_limit(text) to service_role;
commit;
