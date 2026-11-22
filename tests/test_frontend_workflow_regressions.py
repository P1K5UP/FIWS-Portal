import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FrontendWorkflowRegressionTests(unittest.TestCase):
    def test_collection_handlers_use_all_matching_elements(self):
        for relative in ("src/index.template.html", "index.html"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            # $ is querySelector (one element); $$ is querySelectorAll (a collection).
            self.assertIsNone(
                re.search(r"(?<!\$)\$\([^)]*\)\.forEach", source),
                f"{relative} loops over a single querySelector result",
            )
            self.assertNotIn("$$$(", source, f"{relative} has a malformed selector helper")

    def test_applicant_form_and_admin_actions_keep_collection_bindings(self):
        source = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        for selector in (
            "$$('[data-ty]',f).forEach",
            "$$('[data-e]',f).forEach",
            "$$('[data-app]',P).forEach",
            "$$('[data-state]',card).forEach",
            "$$('[data-col]',P).forEach",
            "$$('[data-reset]',P).forEach",
            "$$('[data-logo]',P).forEach",
            "$$('[data-logo-remove]',P).forEach",
        ):
            self.assertIn(selector, source)

    def test_shared_xlsx_import_parses_before_upload_and_publishes_shared_path(self):
        source = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("XLSX.read(bytes,{type:'array',cellDates:true})", source)
        self.assertIn("const workbookPath='workbooks/current-'+crypto.randomUUID()+'.xlsx'", source)
        self.assertIn("adminUploadFile(file,workbookPath", source)
        self.assertIn("saveSharedSetting('workbook',{path:workbookPath", source)
        self.assertIn("const summary=parsed.map", source)

    def test_application_submission_supports_exact_local_and_production_origins(self):
        function = (ROOT / "supabase/functions/submit-application/index.ts").read_text(encoding="utf-8")
        self.assertIn('"https://p1k5up.github.io"', function)
        self.assertIn('"http://localhost:8000"', function)
        self.assertIn("if (!ALLOWED_ORIGINS.has(origin))", function)
        self.assertIn("withAllowedOrigin(await authenticatedHandler(req), origin)", function)
        self.assertNotIn('Access-Control-Allow-Origin": "*"', function)

    def test_application_draft_is_retried_when_auth_session_already_exists(self):
        source = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("await sb.functions.invoke('submit-application'", source)
        self.assertIn("await initSupabase();await loadSharedData();await finishPendingApplication()", source)

    def test_logo_storage_path_matches_edge_function_allowlist(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        function = (ROOT / "supabase/functions/fiws-admin/index.ts").read_text(encoding="utf-8")
        self.assertIn("const path='logos/'+k+'.png'", page)
        self.assertIn(r"/^logos\/(FIWS|FITC)\.png$/", function)


if __name__ == "__main__":
    unittest.main()
