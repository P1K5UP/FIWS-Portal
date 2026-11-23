import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LightModePolishTests(unittest.TestCase):
    def test_discord_ctas_and_theme_icon_have_explicit_contrast(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(".community-widget-head>b{color:#5865f2}", page)
            self.assertIn(".discord-join{align-self:flex-start", page)
            self.assertIn("background:#5865f2;color:#fff", page)
            self.assertIn('id="theme" type="button"', page)
            self.assertIn("if(sel==='#theme')b.innerHTML=dark?", page)
            self.assertNotIn('id="theme" aria-label="Toggle light and dark theme">Theme</button>', page)

    def test_selected_series_and_season_are_visible_in_light_mode(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn(".pick .seg button[aria-pressed=true]{background:var(--sky);color:var(--accent-ink)", page)

    def test_standings_explanatory_note_is_removed(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("Points per round are derived from the cumulative standings", page)

    def test_cancelled_rounds_are_grouped_in_results_and_calendar(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("const cancelledIx=s.cal.map", page)
            self.assertIn("ix.length||cancelledIx.length||annulledIx.length?", page)
            self.assertIn("const t=new Date().toISOString().slice(0,10),cancelled=s.cal.map", page)
            self.assertIn("visible.length||cancelled.length||annulled.length?", page)
            self.assertIn('<details class="panel cancelled-rounds">', page)
            self.assertIn(".cancelled-round-list{display:grid", page)
            self.assertNotIn("Points per round are derived from the cumulative standings", page)


if __name__ == "__main__":
    unittest.main()
