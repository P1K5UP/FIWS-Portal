-- Delete accepted/rejected applications 24 hours after the decision timestamp.
-- The scheduled job is installed separately in the production migration.
create extension if not exists pg_cron with schema pg_catalog;

do $$
declare
  existing_job bigint;
begin
  select jobid into existing_job
  from cron.job
  where jobname = 'fiws-delete-decided-applications-24h';
  if existing_job is not null then
    perform cron.unschedule(existing_job);
  end if;

  perform cron.schedule(
    'fiws-delete-decided-applications-24h',
    '*/5 * * * *',
    $job$
      delete from public.applications
      where status in ('accepted', 'rejected')
        and decided_at is not null
        and decided_at <= now() - interval '24 hours';
    $job$
  );
end
$$;
