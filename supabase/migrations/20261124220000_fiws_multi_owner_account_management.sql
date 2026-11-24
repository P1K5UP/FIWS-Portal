-- Allow multiple owner accounts while preventing accidental removal of the final active owner.
begin;

create or replace function public.fiws_owner_create_admin(
  p_actor_id uuid, p_username text, p_display_name text, p_rank text, p_password_hash text
) returns uuid
language plpgsql security definer set search_path = ''
as $$
declare v_id uuid;
begin
  if not exists(select 1 from public.fiws_admin_accounts where id=p_actor_id and admin_rank='owner' and disabled=false) then
    raise exception 'Owner permission required';
  end if;
  if p_rank not in ('owner','administrator','moderator') then raise exception 'Invalid administrator rank'; end if;
  insert into public.fiws_admin_accounts(username,display_name,admin_rank,password_hash,password_salt,created_by)
  values(p_username,p_display_name,p_rank,p_password_hash,'embedded-in-argon2id-hash',p_actor_id)
  returning id into v_id;
  insert into public.fiws_admin_audit_log(actor_admin_id,actor_username,actor_rank,action,target_type,target_id,details)
  select id,username,admin_rank,'admin.create','admin',v_id::text,jsonb_build_object('rank',p_rank)
    from public.fiws_admin_accounts where id=p_actor_id;
  return v_id;
end;
$$;

create or replace function public.fiws_owner_change_admin_rank(
  p_actor_id uuid, p_target_id uuid, p_rank text
) returns boolean
language plpgsql security definer set search_path = ''
as $$
declare v_old_rank text; v_active_owners integer;
begin
  if p_rank not in ('owner','administrator','moderator') or p_actor_id=p_target_id then return false; end if;
  if not exists(select 1 from public.fiws_admin_accounts where id=p_actor_id and admin_rank='owner' and disabled=false) then
    raise exception 'Owner permission required';
  end if;
  select admin_rank into v_old_rank from public.fiws_admin_accounts
   where id=p_target_id and disabled=false for update;
  if not found then return false; end if;
  if v_old_rank='owner' and p_rank<>'owner' then
    select count(*) into v_active_owners from public.fiws_admin_accounts where admin_rank='owner' and disabled=false;
    if v_active_owners<=1 then return false; end if;
  end if;
  update public.fiws_admin_accounts set admin_rank=p_rank,updated_at=now() where id=p_target_id;
  insert into public.fiws_admin_audit_log(actor_admin_id,actor_username,actor_rank,action,target_type,target_id,details)
  select id,username,admin_rank,'admin.rank_change','admin',p_target_id::text,jsonb_build_object('from',v_old_rank,'to',p_rank)
    from public.fiws_admin_accounts where id=p_actor_id;
  return true;
end;
$$;

create or replace function public.fiws_owner_set_admin_disabled(
  p_actor_id uuid, p_target_id uuid, p_disabled boolean
) returns boolean
language plpgsql security definer set search_path = ''
as $$
declare v_rank text; v_active_owners integer;
begin
  if p_actor_id=p_target_id then return false; end if;
  if not exists(select 1 from public.fiws_admin_accounts where id=p_actor_id and admin_rank='owner' and disabled=false) then
    raise exception 'Owner permission required';
  end if;
  select admin_rank into v_rank from public.fiws_admin_accounts where id=p_target_id for update;
  if not found then return false; end if;
  if p_disabled and v_rank='owner' then
    select count(*) into v_active_owners from public.fiws_admin_accounts where admin_rank='owner' and disabled=false;
    if v_active_owners<=1 then return false; end if;
  end if;
  update public.fiws_admin_accounts set disabled=p_disabled,updated_at=now() where id=p_target_id;
  if p_disabled then
    update public.fiws_admin_sessions set revoked_at=now() where admin_id=p_target_id and revoked_at is null;
  end if;
  insert into public.fiws_admin_audit_log(actor_admin_id,actor_username,actor_rank,action,target_type,target_id)
  select id,username,admin_rank,case when p_disabled then 'admin.disable' else 'admin.enable' end,'admin',p_target_id::text
    from public.fiws_admin_accounts where id=p_actor_id;
  return true;
end;
$$;

create or replace function public.fiws_owner_reset_admin_password(
  p_actor_id uuid, p_target_id uuid, p_password_hash text
) returns boolean
language plpgsql security definer set search_path = ''
as $$
declare v_target_id uuid;
begin
  if p_actor_id=p_target_id then return false; end if;
  if not exists(select 1 from public.fiws_admin_accounts where id=p_actor_id and admin_rank='owner' and disabled=false) then
    raise exception 'Owner permission required';
  end if;
  select id into v_target_id from public.fiws_admin_accounts where id=p_target_id for update;
  if not found then return false; end if;
  update public.fiws_admin_accounts set password_hash=p_password_hash,password_salt='embedded-in-argon2id-hash',
    password_changed_at=now(),totp_secret_ciphertext=null,totp_secret_iv=null,totp_enabled=false,
    totp_last_step=null,updated_at=now() where id=p_target_id;
  update public.fiws_admin_sessions set revoked_at=now() where admin_id=p_target_id and revoked_at is null;
  delete from public.fiws_admin_recovery_codes where admin_id=p_target_id;
  insert into public.fiws_admin_audit_log(actor_admin_id,actor_username,actor_rank,action,target_type,target_id)
  select id,username,admin_rank,'admin.password_reset','admin',p_target_id::text
    from public.fiws_admin_accounts where id=p_actor_id;
  return true;
end;
$$;

revoke all on function public.fiws_owner_create_admin(uuid,text,text,text,text) from public,anon,authenticated;
revoke all on function public.fiws_owner_change_admin_rank(uuid,uuid,text) from public,anon,authenticated;
revoke all on function public.fiws_owner_set_admin_disabled(uuid,uuid,boolean) from public,anon,authenticated;
revoke all on function public.fiws_owner_reset_admin_password(uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.fiws_owner_create_admin(uuid,text,text,text,text) to service_role;
grant execute on function public.fiws_owner_change_admin_rank(uuid,uuid,text) to service_role;
grant execute on function public.fiws_owner_set_admin_disabled(uuid,uuid,boolean) to service_role;
grant execute on function public.fiws_owner_reset_admin_password(uuid,uuid,text) to service_role;

commit;
