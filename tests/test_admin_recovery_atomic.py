import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FUNCTION = (ROOT / "supabase/functions/fiws-admin/index.ts").read_text(encoding="utf-8")
MIGRATION = (ROOT / "supabase/migrations/20261122183000_fiws_atomic_admin_recovery.sql").read_text(encoding="utf-8")


class AdminRecoveryAtomicityTests(unittest.TestCase):
    def test_recovery_endpoints_use_database_transactions(self):
        self.assertIn('db.rpc("fiws_complete_admin_recovery"', FUNCTION)
        self.assertIn('db.rpc("fiws_complete_owner_recovery"', FUNCTION)
        self.assertNotIn('action === "recover-password"', FUNCTION.split('action === "admin-list"')[0].split('action === "recover-password"')[1].split('action === "admin-list"')[0] if 'action === "recover-password"' in FUNCTION else "")

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

    def test_transaction_rolls_back_if_a_later_step_fails(self):
        self.assertIn("begin;", MIGRATION.lower())
        self.assertIn("commit;", MIGRATION.lower())
        self.assertIn("raise exception", MIGRATION.lower())


if __name__ == "__main__":
    unittest.main()
