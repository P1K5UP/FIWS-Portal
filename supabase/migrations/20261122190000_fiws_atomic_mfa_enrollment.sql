-- Make MFA confirmation and recovery-code rotation indivisible.
begin;

create or replace function public.fiws_confirm_admin_mfa(
  p_admin_id uuid,
  p_session_id uuid,
  p_matched_step bigint,
  p_codes jsonb
) returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_username text;
  v_rank text;
begin
  select username, admin_rank into v_username, v_rank
    from public.fiws_admin_accounts
   where id = p_admin_id and disabled = false
   for update;
  if not found then return false; end if;

  update public.fiws_admin_accounts
     set totp_last_step = p_matched_step,
         totp_enabled = true,
         failed_login_count = 0,
         locked_until = null,
         last_login_at = now()
   where id = p_admin_id
     and (totp_last_step is null or totp_last_step < p_matched_step);
  if not found then return false; end if;

  if jsonb_typeof(p_codes) <> 'array' or jsonb_array_length(p_codes) <> 10 then
    raise exception 'Exactly ten recovery codes are required';
  end if;

  delete from public.fiws_admin_recovery_codes where admin_id = p_admin_id;
  insert into public.fiws_admin_recovery_codes(admin_id, code_hash)
    select p_admin_id, item.code_hash
      from jsonb_to_recordset(p_codes) as item(code_hash text);

  update public.fiws_admin_sessions
     set mfa_verified = true, expires_at = now() + interval '8 hours'
   where id = p_session_id and admin_id = p_admin_id
     and mfa_verified = false and revoked_at is null and expires_at > now();
  if not found then raise exception 'MFA enrollment session is no longer valid'; end if;

  insert into public.fiws_admin_audit_log(actor_admin_id,actor_username,actor_rank,action,target_type,target_id)
  values(p_admin_id,v_username,v_rank,'auth.mfa_enabled','admin',p_admin_id::text);
  return true;
end;
$$;

create or replace function public.fiws_rotate_admin_recovery_codes(
  p_admin_id uuid,
  p_matched_step bigint,
  p_codes jsonb
) returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_username text;
  v_rank text;
begin
  select username, admin_rank into v_username, v_rank
    from public.fiws_admin_accounts
   where id = p_admin_id and disabled = false and totp_enabled = true
   for update;
  if not found then return false; end if;

  if jsonb_typeof(p_codes) <> 'array' or jsonb_array_length(p_codes) <> 10 then
    raise exception 'Exactly ten recovery codes are required';
  end if;

  update public.fiws_admin_accounts
     set totp_last_step = p_matched_step
   where id = p_admin_id
     and (totp_last_step is null or totp_last_step < p_matched_step);
  if not found then return false; end if;

  delete from public.fiws_admin_recovery_codes where admin_id = p_admin_id;
  insert into public.fiws_admin_recovery_codes(admin_id, code_hash)
    select p_admin_id, item.code_hash
      from jsonb_to_recordset(p_codes) as item(code_hash text);

  insert into public.fiws_admin_audit_log(actor_admin_id,actor_username,actor_rank,action,target_type,target_id)
  values(p_admin_id,v_username,v_rank,'auth.recovery_codes_rotated','admin',p_admin_id::text);
  return true;
end;
$$;

revoke all on function public.fiws_confirm_admin_mfa(uuid,uuid,bigint,jsonb) from public, anon, authenticated;
revoke all on function public.fiws_rotate_admin_recovery_codes(uuid,bigint,jsonb) from public, anon, authenticated;
grant execute on function public.fiws_confirm_admin_mfa(uuid,uuid,bigint,jsonb) to service_role;
grant execute on function public.fiws_rotate_admin_recovery_codes(uuid,bigint,jsonb) to service_role;

commit;
