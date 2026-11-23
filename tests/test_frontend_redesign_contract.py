from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FrontendRedesignContractTests(unittest.TestCase):
    def setUp(self):
        self.template = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.generated = (ROOT / "index.html").read_text(encoding="utf-8")

    def test_design_system_is_present_and_css_is_balanced(self):
        marker = '/* FIWS 2026 design system */'
        for document in (self.template, self.generated):
            self.assertIn(marker, document)
            css = document.split("<style>", 1)[1].split("</style>", 1)[0]
            self.assertEqual(css.count("{"), css.count("}"), "Design system CSS braces must balance")
            self.assertIn("@media(prefers-reduced-motion:reduce)", css)
            self.assertIn("Manrope", css)
            self.assertIn("--sky:", css)
            self.assertIn("--fiws-red:", css)

    def test_template_and_generated_design_system_match(self):
        marker = '/* FIWS 2026 design system */'
        template_css = self.template.split("<style>", 1)[1].split("</style>", 1)[0]
        generated_css = self.generated.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertEqual(template_css, generated_css)

    def test_primary_navigation_and_existing_views_remain(self):
        for key, label in (
            ("home", "Home"), ("standings", "Standings"), ("results", "Results"),
            ("calendar", "Calendar"), ("entries", "Entries"), ("rules", "Rules"),
            ("apply", "Apply"), ("status", "Status"),
        ):
            self.assertIn(f"['{key}','{label}']", self.template)
            self.assertIn(f"V.{key}=", self.template)

    def test_data_and_interaction_integrations_remain(self):
        for marker in (
            "function tower(", "function renderStatus(", "async function applicationApi(",
            "async function fetchSharedConfig(", "function admin(", "function render(",
        ):
            self.assertIn(marker, self.template)

    def test_mobile_navigation_remains_a_bottom_dock(self):
        marker = '/* FIWS 2026 design system */'
        css = self.template.split(marker, 1)[1].split("</style>", 1)[0]
        self.assertRegex(css, r"\.top\s*\{[^}]*position:fixed;top:auto;bottom:0")
        self.assertIn(".nav-ico{width:23px;height:23px}", css)
        self.assertIn("env(safe-area-inset-bottom,0px)", css)


if __name__ == "__main__":
    unittest.main()
