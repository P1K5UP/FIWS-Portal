-- The multi-owner account lifecycle supersedes the original single-owner invariant.
-- The live production catalog confirms this partial unique index is absent.
begin;

drop index if exists public.fiws_single_owner_uq;

commit;
