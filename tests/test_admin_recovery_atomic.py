import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FUNCTION = (ROOT / "supabase/functions/fiws-admin/index.ts").read_text(encoding="utf-8")
MIGRATION = (ROOT / "supabase/migrations/20261122185242_fiws_atomic_admin_recovery.sql").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "supabase/migrations/20261122185244_fiws_atomic_owner_bootstrap.sql").read_text(encoding="utf-8")
MFA_MIGRATION = (ROOT / "supabase/migrations/20261122185246_fiws_atomic_mfa_enrollment.sql").read_text(encoding="utf-8")
LIFECYCLE_MIGRATION = (ROOT / "supabase/migrations/20261122185248_fiws_atomic_admin_account_lifecycle.sql").read_text(encoding="utf-8")


class AdminRecoveryAtomicityTests(unittest.TestCase):
    def test_recovery_endpoints_use_database_transactions(self):
        self.assertIn('db.rpc("fiws_complete_admin_recovery"', FUNCTION)
        self.assertIn('db.rpc("fiws_complete_owner_recovery"', FUNCTION)
        self.assertEqual(FUNCTION.count('db.rpc("fiws_complete_admin_recovery"'), 1)
        self.assertEqual(FUNCTION.count('db.rpc("fiws_complete_owner_recovery"'), 1)

    def test_recovery_code_consumption_and_password_change_share_transaction(self):
        body = FUNCTION.split('action === "recover-password"')[1].split('action === "admin-list"')[0]
        self.assertIn("fiws_complete_admin_recovery", body)
        self.assertNotIn('.update({ used_at:', body)
        self.assertNotIn('.update({\n        password_hash:', body)
        self.assertIn("p_recovery_code_id: recovery.id", body)

    def test_owner_recovery_gate_and_reset_share_transaction(self):
        body = FUNCTION.split('action === "owner-recover"')[1].split('action === "recover-password"')[0]
        self.assertIn("fiws_complete_owner_recovery", body)
        self.assertNotIn("owner_recovery_used_at", body)

    def test_rpc_functions_are_server_only(self):
        self.assertIn("security definer", MIGRATION.lower())
        self.assertRegex(MIGRATION, r"revoke all on function public\.fiws_complete_admin_recovery\([^;]+ from public, anon, authenticated")
        self.assertRegex(MIGRATION, r"revoke all on function public\.fiws_complete_owner_recovery\([^;]+ from public, anon, authenticated")
        self.assertIn("to service_role", MIGRATION)

    def test_bootstrap_state_and_owner_creation_are_atomic(self):
        body = FUNCTION.split('action === "bootstrap"')[1].split('action === "login"')[0]
        self.assertIn('db.rpc("fiws_bootstrap_admin"', body)
        self.assertNotIn("fiws_admin_bootstrap_state", body)
        self.assertIn("for update", BOOTSTRAP.lower())
        self.assertIn("completed_at = now()", BOOTSTRAP)
        self.assertIn("bootstrap.owner_created", BOOTSTRAP)
        self.assertIn("to service_role", BOOTSTRAP)

    def test_mfa_enrollment_and_code_rotation_use_atomic_rpcs(self):
        self.assertIn('db.rpc("fiws_confirm_admin_mfa"', FUNCTION)
        self.assertIn('db.rpc("fiws_rotate_admin_recovery_codes"', FUNCTION)
        self.assertNotIn('.delete().eq("admin_id", account.id)', FUNCTION.split('action === "mfa-confirm"')[1].split('action === "session"')[0])
        self.assertIn("for update", (ROOT / "supabase/migrations/20261122185246_fiws_atomic_mfa_enrollment.sql").read_text(encoding="utf-8").lower())

    def test_account_lifecycle_uses_atomic_database_procedures(self):
        for action in ("fiws_owner_create_admin", "fiws_owner_change_admin_rank", "fiws_owner_set_admin_disabled", "fiws_owner_reset_admin_password", "fiws_change_own_admin_password"):
            self.assertIn(f'db.rpc("{action}"', FUNCTION)
        sql = (ROOT / "supabase/migrations/20261122185248_fiws_atomic_admin_account_lifecycle.sql").read_text(encoding="utf-8").lower()
        self.assertIn("security definer", sql)
        self.assertIn("to service_role", sql)
        self.assertIn("revoke all on function", sql)

    def test_transaction_rolls_back_if_a_later_step_fails(self):
        self.assertIn("begin;", MIGRATION.lower())
        self.assertIn("commit;", MIGRATION.lower())
        self.assertIn("raise exception", MIGRATION.lower())


if __name__ == "__main__":
    unittest.main()

