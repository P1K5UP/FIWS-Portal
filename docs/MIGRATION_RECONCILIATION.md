# FIWS migration-history reconciliation

**Production project:** `yipzokjzqltxcufixrsv`  
**Reconciled against:** read-only production migration ledger and PostgreSQL catalog, 26 November 2026  
**Production schema changes made:** none

## Result

Production reports 24 applied migration versions. The repository now contains SQL files at all 24 production versions, plus one intentionally pending local migration at `20261126162000`.

## Filename corrections

| Previous repository version | Production version | Migration |
|---|---|---|
| `20261122183000` | `20261122185242` | `fiws_atomic_admin_recovery` |
| `20261122184500` | `20261122185244` | `fiws_atomic_owner_bootstrap` |
| `20261122190000` | `20261122185246` | `fiws_atomic_mfa_enrollment` |
| `20261122191500` | `20261122185248` | `fiws_atomic_admin_account_lifecycle` |
| `20261122194031` | `20261122194105` | `grant_service_role_write_public_site_settings` |
| `20261124220000` | `20261124210752` | `fiws_multi_owner_account_management` |

The TOTP replay-protection migration `20261122175630` was already present at the exact production version. It was incorrectly described as absent in the first audit report.

## Reconstructed production migrations

### `20261122193044_grant_service_role_application_workflow_access.sql`

Read-only catalog checks confirmed that `service_role` has SELECT, INSERT, UPDATE and DELETE privileges on both `public.applications` and `public.application_ip_limits`. The restored migration expresses those grants explicitly so a clean database can reproduce the deployed application workflow access.

### `20261124211457_fix_multi_owner_unique_owner_index.sql`

The original admin-identity migration creates the partial unique index `public.fiws_single_owner_uq`, which permits only one owner account. The multi-owner account-management functions in the next production migration allow multiple owners. The live catalog no longer contains the single-owner index. The restored migration uses `DROP INDEX IF EXISTS public.fiws_single_owner_uq` to reproduce that production state.

These two SQL files are reconstructed from the live catalog and the repository's current access/ownership model. They are not represented as byte-for-byte recovery of the original historical migration bodies.

## Pending local migration

`20261126162000_grant_service_role_execute_fiws_admin_check.sql` records the EXECUTE privilege for `private.is_fiws_admin()` on `service_role`. The production catalog already reports that privilege, but no matching production migration version exists. This idempotent grant is retained as a new pending migration with a timestamp after the production ledger, rather than leaving an older, untracked timestamp in the middle of production history.

## Verification and rollout

- Read-only checks confirmed the production migration ledger, the TOTP column, service-role table grants, function EXECUTE privilege, and absence of the single-owner index.
- CI checks that all 24 production version identifiers exist exactly once, plus the one pending local migration.
- CI checks the reconstructed application grants and index-drop statement.
- No `supabase db push`, migration repair, DDL, or data mutation was run against production.

**Required before a production schema push:** create a disposable Supabase development branch/database, apply the repository migrations from an empty database, compare the resulting schema/privileges/indexes with production, and resolve any differences. Only after that review should a production migration push be considered. The Supabase development branch may incur additional compute charges; obtain approval for those charges before provisioning it.
