import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "supabase/functions/fiws-admin/index.ts").read_text(encoding="utf-8")


class AdminPasswordBreachScreeningTests(unittest.TestCase):
    def test_password_range_lookup_uses_k_anonymity_and_padding(self):
        helper = SOURCE.split("async function passwordBreachError", 1)[1].split("let dummyPasswordHash", 1)[0]
        self.assertIn('crypto.subtle.digest("SHA-1"', helper)
        self.assertIn("const prefix = hash.slice(0, 5)", helper)
        self.assertIn("const suffix = hash.slice(5)", helper)
        self.assertIn("https://api.pwnedpasswords.com/range/${prefix}", helper)
        self.assertIn('"Add-Padding": "true"', helper)
        self.assertIn('"User-Agent": "FIWS-Portal/1.0"', helper)
        self.assertIn("AbortSignal.timeout(5000)", helper)
        self.assertIn("status: 503", helper)
        self.assertNotIn("range/${password}", helper)
        self.assertNotIn("range/${hash}", helper)

    def test_every_password_set_path_checks_breached_passwords(self):
        actions = ("bootstrap", "recover-password", "admin-create", "password-change", "admin-reset-password")
        for action in actions:
            start = SOURCE.index(f'if (action === "{action}")')
            next_action = SOURCE.find('if (action === "', start + 1)
            block = SOURCE[start: next_action if next_action >= 0 else len(SOURCE)]
            with self.subTest(action=action):
                self.assertIn("passwordBreachError(", block)

    def test_existing_local_password_policy_remains_enforced(self):
        self.assertIn("function passwordPolicyError(password: string)", SOURCE)
        self.assertGreaterEqual(SOURCE.count("passwordPolicyError(password)"), 3)
        self.assertIn("passwordPolicyError(next)", SOURCE)


if __name__ == "__main__":
    unittest.main()
