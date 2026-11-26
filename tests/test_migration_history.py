import unittest
from pathlib import Path

MIGRATIONS = Path("supabase/migrations")
PRODUCTION_VERSIONS = [
    "20261122162330",
    "20261122162341",
    "20261122162550",
    "20261122162729",
    "20261122162809",
    "20261122163037",
    "20261122175332",
    "20261122175349",
    "20261122175630",
    "20261122175748",
    "20261122175846",
    "20261122175855",
    "20261122185242",
    "20261122185244",
    "20261122185246",
    "20261122185248",
    "20261122193044",
    "20261122194030",
    "20261122194105",
    "20261122204341",
    "20261122204526",
    "20261122210551",
    "20261124210752",
    "20261124211457",
]
LOCAL_PENDING_VERSIONS = ["20261126162000"]


class MigrationHistoryTests(unittest.TestCase):
    def test_production_migration_versions_are_represented_exactly(self):
        versions = sorted(path.name.split("_", 1)[0] for path in MIGRATIONS.glob("*.sql"))
        self.assertEqual(versions, sorted(PRODUCTION_VERSIONS + LOCAL_PENDING_VERSIONS))

    def test_application_workflow_grants_match_live_service_role_access(self):
        migration = next(MIGRATIONS.glob("20261122193044_*.sql")).read_text(encoding="utf-8")
        self.assertIn("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE PUBLIC.APPLICATIONS TO SERVICE_ROLE", migration.upper())
        self.assertIn("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE PUBLIC.APPLICATION_IP_LIMITS TO SERVICE_ROLE", migration.upper())

    def test_multi_owner_migration_removes_the_single_owner_index(self):
        migration = next(MIGRATIONS.glob("20261124211457_*.sql")).read_text(encoding="utf-8")
        self.assertIn("DROP INDEX IF EXISTS PUBLIC.FIWS_SINGLE_OWNER_UQ", migration.upper())

    def test_pending_function_grant_is_idempotent_and_versioned_after_production(self):
        migration = next(MIGRATIONS.glob("20261126162000_*.sql")).read_text(encoding="utf-8")
        self.assertIn("GRANT EXECUTE ON FUNCTION private.is_fiws_admin() TO service_role", migration)
        self.assertGreater(LOCAL_PENDING_VERSIONS[0], PRODUCTION_VERSIONS[-1])


if __name__ == "__main__":
    unittest.main()
