-- Explicitly deny all client roles access to the internal IP throttle table.
drop policy if exists "No client access to IP rate limits" on public.application_ip_limits;
create policy "No client access to IP rate limits" on public.application_ip_limits
for all to anon, authenticated using (false) with check (false);
