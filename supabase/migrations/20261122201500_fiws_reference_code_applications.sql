-- Replace email-verified applicant accounts with reference-code access.
begin;
alter table public.applications alter column applicant_id drop not null;
create or replace function private.guard_application_insert()
returns trigger language plpgsql security invoker set search_path = ''
as $$
begin
 if current_user <> 'service_role' then raise exception 'Applications must be submitted through the application service' using errcode = '42501'; end if;
 if new.applicant_id is not null then raise exception 'Applicant account identity is not used' using errcode = '42501'; end if;
 if new.reference_code !~ '^FIWS-[A-F0-9]{26}$' then raise exception 'Invalid application reference code'; end if;
 if coalesce(new.application_data ->> 'type','') not in ('Driver','Steward') then raise exception 'Invalid application type'; end if;
 if lower(coalesce(new.application_data ->> 'email','')) !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]{2,}$' then raise exception 'A valid contact email is required'; end if;
 if jsonb_typeof(new.application_data) <> 'object' or octet_length(new.application_data::text) > 20000 then raise exception 'Invalid application payload'; end if;
 new.status:='pending';new.staff_note:=null;new.decided_at:=null;new.decided_by:=null;new.created_at:=now();return new;
end;
$$;
drop index if exists public.applications_one_pending_per_type_idx;
create unique index if not exists applications_one_pending_per_email_type_idx on public.applications(lower(application_data->>'email'),application_data->>'type') where status='pending' and application_data ? 'email';
commit;
