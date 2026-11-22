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

    def test_applications_use_reference_codes_without_applicant_email_auth(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        function = (ROOT / "supabase/functions/submit-application/index.ts").read_text(encoding="utf-8")
        self.assertIn("fiws_application_ref=", page)
        self.assertIn("SameSite=Strict", page)
        self.assertIn("applicationApi('submit'", page)
        self.assertIn("applicationApi('status'", page)
        self.assertNotIn("signInWithOtp", page)
        self.assertNotIn("finishPendingApplication", page)
        self.assertIn("crypto.getRandomValues(new Uint8Array(13))", function)
        self.assertIn("applicant_id:null", function)
        self.assertIn('body?.action==="status"', function)
        self.assertNotIn("auth.getUser", function)
        self.assertIn("FIWS_RATE_LIMIT_PEPPER", function)
        self.assertIn("ALLOWED_ORIGINS.has(origin)", function)

    def test_logo_storage_path_matches_edge_function_allowlist(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        function = (ROOT / "supabase/functions/fiws-admin/index.ts").read_text(encoding="utf-8")
        self.assertIn("const path='logos/'+k+'.png'", page)
        self.assertIn(r"/^logos\/(FIWS|FITC)\.png$/", function)


    def test_public_status_response_excludes_contact_email_and_full_application(self):
        function = (ROOT / "supabase/functions/submit-application/index.ts").read_text(encoding="utf-8")
        status = function.split('if(body?.action==="status")', 1)[1].split('return json({error:"Unknown application action."', 1)[0]
        self.assertIn("application_data:{name:d.name||\"\",type:d.type||\"\",series:d.series||\"\"}", status)
        self.assertNotIn("email:d.email", status)
        self.assertNotIn("application_data:data.application_data", status)

    def test_application_reference_cookie_requires_consent_and_is_secure_on_https(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        cookie = page.split("function saveReferenceCookie", 1)[1].split("function getReferenceCookie", 1)[0]
        self.assertIn("if(!LS.get('consent',null))return false", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn("location.protocol==='https:'?'; Secure':''", cookie)
        clear = page.split("function clearReferenceCookie", 1)[1].split("\n", 1)[0]
        self.assertIn("current!==normRef(code)", clear)
        self.assertIn("Max-Age=0", clear)

    def test_decided_application_cleanup_is_scheduled_for_24_hours(self):
        migration = (ROOT / "supabase/migrations/20261122210551_fiws_auto_delete_decided_applications_after_24h.sql").read_text(encoding="utf-8")
        self.assertIn("*/5 * * * *", migration)
        self.assertIn("status in ('accepted', 'rejected')", migration)
        self.assertIn("decided_at <= now() - interval '24 hours'", migration)


    def test_privacy_notice_matches_public_status_and_retention_behavior(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        privacy = page.split("privacy:['Privacy notice'", 1)[1].split("terms:['Terms of use'", 1)[0]
        self.assertIn("does not return the contact email or full application", privacy)
        self.assertIn("automatically deleted 24 hours after the decision", privacy)
        self.assertIn("Pending applications remain stored until staff make a decision or delete them", privacy)
        self.assertNotIn("Staff keep applications only as long as needed to run the season", privacy)


    def test_resetting_application_to_pending_clears_decision_timestamp(self):
        function = (ROOT / "supabase/functions/fiws-admin/index.ts").read_text(encoding="utf-8")
        self.assertIn('decided_at: status === "pending" ? null : new Date().toISOString()', function)


    def test_mobile_scoreboard_scrubbing_keeps_smooth_row_tweening(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("el.classList.add('tower')", page)
        self.assertIn("rng.addEventListener('pointerdown',e=>{touchScrub=e.pointerType==='touch';el.classList.add('scrubbing')})", page)
        self.assertIn("if(el.classList.contains('scrubbing')){pt.textContent=v;shown[idx]=v", page)
        self.assertNotIn(".tower.scrubbing .tr{transition:none!important}", page)
        self.assertIn(".tower.scrubbing .pt{transition:none!important}", page)
        self.assertIn("transition:transform .5s cubic-bezier(.22,.75,.25,1)", page)

    def test_mobile_navigation_uses_one_compact_top_bar(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertNotIn('id="mobile-nav"', page)
        self.assertNotIn(".mobile-dock{position:fixed", page)
        self.assertIn(".bar{padding:.4rem .55rem;gap:.45rem;flex-wrap:nowrap;min-width:0}", page)
        self.assertIn(".nav{order:0;flex:1 1 auto;width:auto;min-width:0", page)
        self.assertIn("main{padding:1rem .8rem calc(3rem + env(safe-area-inset-bottom,0px))}", page)
        self.assertIn(".admin-toolbar{position:static;top:auto;backdrop-filter:none}", page)
        self.assertIn(".pick .seg:last-child{width:100%;display:grid", page)

    def test_mobile_leaderboard_slider_prevents_page_pan_and_haptics_on_touch(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("touch-action:none;overscroll-behavior:contain", page)
        self.assertIn("e.pointerType==='touch'", page)
        self.assertIn("matchMedia('(pointer:coarse)').matches&&typeof navigator.vibrate==='function'", page)
        self.assertIn("navigator.vibrate(8)", page)
        self.assertIn("rng.addEventListener('pointercancel'", page)

    def test_rules_page_covers_current_sporting_directive_and_championship(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        rules = page.split("V.rules=()=>", 1)[1].split("/* application form definitions */", 1)[0]
        for phrase in (
            "one change of direction",
            "Do not move under braking",
            "120 km/h (75 mph) in FIWS",
            "80 km/h (50 mph) in FITC",
            "one mandatory pitstop",
            "12 penalty points",
            "Round 18",
            "best four results",
            "Reverse Gear Glitch abuse",
        ):
            self.assertIn(phrase, rules)

    def test_phone_navigation_is_a_bottom_app_dock_with_icon_labels(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(".top{position:fixed;top:auto;bottom:0", page)
            self.assertIn(".nav-ico{display:block;width:19px;height:19px", page)
            self.assertIn(".nav-label{display:block;font:600 .61rem", page)
            self.assertIn("main{padding-bottom:calc(6.8rem + env(safe-area-inset-bottom,0px))}", page)
            self.assertIn("const NAV_ICONS=", page)

    def test_leaderboard_round_titles_are_shortened_only_on_phones(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("function leaderboardRoundLabel(s,r)", page)
        self.assertIn("matchMedia('(max-width:700px)').matches", page)
        self.assertIn("leaderboardRoundLabel(s,round)", page)
        self.assertIn("leaderboardRoundLabel(s,max)", page)
        self.assertIn("grand prix", page)

    def test_standings_includes_all_entry_drivers_even_without_points_rows(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("function allSeasonDrivers(s)", page)
        self.assertIn("(s.drivers||[]).forEach(entry=>", page)
        self.assertIn("vals:s.codes.map(()=>0)", page)
        self.assertIn("const standingsSeason=k==='drv'?{...s,drv:allSeasonDrivers(s)}:s", page)
        self.assertIn("tower($('#tw'),standingsSeason,k,l.length)", page)

    def test_leaderboard_rank_swaps_animate_during_slider_scrubbing(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("transition:transform .5s cubic-bezier(.22,.75,.25,1)", page)
        self.assertNotIn(".tower.scrubbing .tr{transition:none!important}", page)
        self.assertIn("@media(max-width:700px){.tower .tr{transition-duration:.42s}", page)

if __name__ == "__main__":
    unittest.main()
