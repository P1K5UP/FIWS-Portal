import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_INTEGRITY = "sha384-EnyY0/GSHQGSxSgMwaIPzSESbqoOLSexfnSMN2AP+39Ckmn92stwABZynq1JyzdT"


class AssetIntegrityTests(unittest.TestCase):
    def test_sheetjs_cdn_script_has_matching_sri_in_source_and_generated_site(self):
        for path in (ROOT / "src/index.template.html", ROOT / "index.html"):
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn(EXPECTED_INTEGRITY, content)
                self.assertIn('crossorigin="anonymous"', content)
                self.assertIn("xlsx-0.20.3/package/dist/xlsx.full.min.js", content)


if __name__ == "__main__":
    unittest.main()
