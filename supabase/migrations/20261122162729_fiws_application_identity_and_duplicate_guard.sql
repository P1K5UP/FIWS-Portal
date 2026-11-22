-- Require a verified applicant email and prevent duplicate pending applications of the same type.
begin;
create or replace function private.guard_application_insert()
returns trigger language plpgsql security invoker set search_path = ''
as $$
declare recent_count integer;
begin
 if auth.uid() is null or new.applicant_id <> auth.uid() then
  raise exception 'Invalid applicant identity' using errcode = '42501';
 end if;
 if lower(coalesce(new.application_data ->> 'email','')) <> lower(coalesce(auth.jwt() ->> 'email','')) then
  raise exception 'Application email must match the verified account email' using errcode = '42501';
 end if;
 if new.reference_code !~ '^FIWS-[A-Z0-9]{8}$' then
  raise exception 'Invalid application reference code';
 end if;
 if coalesce(new.application_data ->> 'type','') not in ('Driver','Steward') then
  raise exception 'Invalid application type';
 end if;
 if jsonb_typeof(new.application_data) <> 'object' or octet_length(new.application_data::text) > 20000 then
  raise exception 'Invalid application payload';
 end if;
 perform pg_advisory_xact_lock(hashtextextended(auth.uid()::text, 0));
 select count(*) into recent_count from public.applications a
 where a.applicant_id = auth.uid() and a.created_at > now() - interval '1 hour';
 if recent_count >= 5 then raise exception 'Application submission limit reached' using errcode = 'P0001'; end if;
 new.status := 'pending';
 new.staff_note := null;
 new.decided_at := null;
 new.decided_by := null;
 new.created_at := now();
 return new;
end;
$$;
create unique index if not exists applications_one_pending_per_type_idx
on public.applications (applicant_id, (application_data ->> 'type'))
where status = 'pending';
commit;
