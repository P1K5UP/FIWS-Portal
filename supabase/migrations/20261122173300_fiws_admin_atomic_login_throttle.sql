begin;
create or replace function public.fiws_consume_admin_login_attempt(p_username_key text, p_ip_hash text)
returns table(attempts integer, locked_until timestamptz)
language plpgsql security invoker set search_path = ''
as $$
begin
 return query
 insert into public.fiws_admin_login_limits as current_limit
  (username_key,ip_hash,window_started_at,attempts,locked_until)
 values(p_username_key,p_ip_hash,now(),1,null)
 on conflict(username_key,ip_hash) do update set
  attempts=case when current_limit.locked_until is not null and current_limit.locked_until>now() then current_limit.attempts when current_limit.window_started_at<now()-interval '15 minutes' then 1 else current_limit.attempts+1 end,
  window_started_at=case when current_limit.locked_until is not null and current_limit.locked_until>now() then current_limit.window_started_at when current_limit.window_started_at<now()-interval '15 minutes' then now() else current_limit.window_started_at end,
  locked_until=case when current_limit.locked_until is not null and current_limit.locked_until>now() then current_limit.locked_until when (case when current_limit.window_started_at<now()-interval '15 minutes' then 1 else current_limit.attempts+1 end)>=5 then now()+make_interval(mins=>least(60,5*power(2,least((case when current_limit.window_started_at<now()-interval '15 minutes' then 1 else current_limit.attempts+1 end)-5,4))::integer)) else null end
 returning current_limit.attempts,current_limit.locked_until;
end;
$$;
revoke all on function public.fiws_consume_admin_login_attempt(text,text) from public,anon,authenticated;
grant execute on function public.fiws_consume_admin_login_attempt(text,text) to service_role;
commit;