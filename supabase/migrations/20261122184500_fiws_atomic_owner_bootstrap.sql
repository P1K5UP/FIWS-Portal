-- Atomically create the first Owner, consume bootstrap state, and audit the event.
begin;

create or replace function public.fiws_bootstrap_admin(
  p_username text,
  p_display_name text,
  p_password_hash text
) returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_owner_id uuid;
begin
  perform 1
    from public.fiws_admin_bootstrap_state
   where singleton = true
   for update;

  if not found then
    raise exception 'FIWS bootstrap state is missing';
  end if;

  if exists (
    select 1 from public.fiws_admin_bootstrap_state
     where singleton = true and completed_at is not null
  ) or exists (
    select 1 from public.fiws_admin_accounts
  ) then
    raise exception 'FIWS bootstrap has already been completed';
  end if;

  insert into public.fiws_admin_accounts (
    username, display_name, admin_rank, password_hash, password_salt
  ) values (
    p_username, p_display_name, 'owner', p_password_hash,
    'embedded-in-argon2id-hash'
  ) returning id into v_owner_id;

  update public.fiws_admin_bootstrap_state
     set completed_at = now(), completed_by = v_owner_id
   where singleton = true and completed_at is null;

  if not found then
    raise exception 'FIWS bootstrap state was already consumed';
  end if;

  insert into public.fiws_admin_audit_log (
    actor_admin_id, actor_username, actor_rank, action, target_type, target_id
  ) values (
    v_owner_id, p_username, 'owner', 'bootstrap.owner_created', 'admin', v_owner_id::text
  );

  return v_owner_id;
end;
$$;

revoke all on function public.fiws_bootstrap_admin(text, text, text) from public, anon, authenticated;
grant execute on function public.fiws_bootstrap_admin(text, text, text) to service_role;

commit;
