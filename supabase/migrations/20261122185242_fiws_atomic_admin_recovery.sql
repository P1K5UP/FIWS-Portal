-- Make password recovery operations atomic: a recovery token is never consumed
-- unless the password reset, session revocation, and audit record all commit.
begin;

create or replace function public.fiws_complete_admin_recovery(
  p_admin_id uuid,
  p_recovery_code_id uuid,
  p_password_hash text,
  p_username_key text,
  p_ip_hash text
) returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_username text;
  v_rank text;
begin
  update public.fiws_admin_recovery_codes
     set used_at = now()
   where id = p_recovery_code_id
     and admin_id = p_admin_id
     and used_at is null;
  if not found then
    return false;
  end if;

  update public.fiws_admin_accounts
     set password_hash = p_password_hash,
         password_salt = 'embedded-in-argon2id-hash',
         password_changed_at = now(),
         totp_secret_ciphertext = null,
         totp_secret_iv = null,
         totp_enabled = false,
         totp_last_step = null,
         failed_login_count = 0,
         locked_until = null
   where id = p_admin_id
     and disabled = false
   returning username, admin_rank into v_username, v_rank;
  if not found then
    raise exception 'Administrator account unavailable';
  end if;

  update public.fiws_admin_sessions
     set revoked_at = now()
   where admin_id = p_admin_id and revoked_at is null;

  delete from public.fiws_admin_recovery_codes
   where admin_id = p_admin_id;

  delete from public.fiws_admin_login_limits
   where username_key = p_username_key and ip_hash = p_ip_hash;

  insert into public.fiws_admin_audit_log
    (actor_admin_id, actor_username, actor_rank, action, target_type, target_id)
  values
    (p_admin_id, v_username, v_rank, 'auth.recovery_password_reset', 'admin', p_admin_id::text);

  return true;
end;
$$;

create or replace function public.fiws_complete_owner_recovery(
  p_password_hash text
) returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner_id uuid;
  v_username text;
begin
  select id, username into v_owner_id, v_username
    from public.fiws_admin_accounts
   where admin_rank = 'owner'
   for update;
  if not found then
    return false;
  end if;

  update public.fiws_admin_bootstrap_state
     set owner_recovery_used_at = now()
   where singleton = true and owner_recovery_used_at is null;
  if not found then
    return false;
  end if;

  update public.fiws_admin_accounts
     set password_hash = p_password_hash,
         password_salt = 'embedded-in-argon2id-hash',
         password_changed_at = now(),
         totp_secret_ciphertext = null,
         totp_secret_iv = null,
         totp_enabled = false,
         totp_last_step = null,
         failed_login_count = 0,
         locked_until = null,
         disabled = false
   where id = v_owner_id;

  update public.fiws_admin_sessions
     set revoked_at = now()
   where admin_id = v_owner_id and revoked_at is null;

  delete from public.fiws_admin_recovery_codes
   where admin_id = v_owner_id;

  insert into public.fiws_admin_audit_log
    (actor_admin_id, actor_username, actor_rank, action, target_type, target_id)
  values
    (v_owner_id, v_username, 'owner', 'auth.owner_emergency_recovery', 'admin', v_owner_id::text);

  return true;
end;
$$;

revoke all on function public.fiws_complete_admin_recovery(uuid, uuid, text, text, text) from public, anon, authenticated;
revoke all on function public.fiws_complete_owner_recovery(text) from public, anon, authenticated;
grant execute on function public.fiws_complete_admin_recovery(uuid, uuid, text, text, text) to service_role;
grant execute on function public.fiws_complete_owner_recovery(text) to service_role;

commit;
