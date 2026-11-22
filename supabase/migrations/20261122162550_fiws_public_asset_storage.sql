-- Public FIWS assets only; applicant data must never be stored in this bucket.
begin;
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('fiws-public', 'fiws-public', true, 4000000,
 array['image/png','image/jpeg','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'])
on conflict (id) do update set
 public = excluded.public,
 file_size_limit = excluded.file_size_limit,
 allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "Public read FIWS public assets" on storage.objects;
create policy "Public read FIWS public assets" on storage.objects
for select to anon, authenticated using (bucket_id = 'fiws-public');
drop policy if exists "FIWS admins upload public assets" on storage.objects;
create policy "FIWS admins upload public assets" on storage.objects
for insert to authenticated with check (bucket_id = 'fiws-public' and (select private.is_fiws_admin()));
drop policy if exists "FIWS admins update public assets" on storage.objects;
create policy "FIWS admins update public assets" on storage.objects
for update to authenticated using (bucket_id = 'fiws-public' and (select private.is_fiws_admin()))
with check (bucket_id = 'fiws-public' and (select private.is_fiws_admin()));
drop policy if exists "FIWS admins delete public assets" on storage.objects;
create policy "FIWS admins delete public assets" on storage.objects
for delete to authenticated using (bucket_id = 'fiws-public' and (select private.is_fiws_admin()));
commit;
