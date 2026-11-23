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

    def test_phone_navigation_is_an_icon_only_bottom_dock_and_footer_is_reachable(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(".top{position:fixed;top:auto;bottom:0", page)
            self.assertIn(".nav-ico{display:block;width:26px;height:26px", page)
            self.assertIn(".mobile-brand{all:unset;position:fixed;top:calc(env(safe-area-inset-top,0px) + .65rem)", page)
            self.assertIn("#mobile-logo svg,#mobile-logo img,#mobile-logo canvas{display:block;width:auto;height:auto", page)
            self.assertIn("M.replaceChildren(...Array.from(L.childNodes", page)
            self.assertIn("copy.getContext('2d')?.drawImage(node,0,0)", page)
            self.assertIn("getComputedStyle(document.documentElement).getPropertyValue('--ink')", page)
            self.assertIn("#mobile-logo{display:block;width:auto;height:auto", page)
            self.assertIn("max-width:min(144px,38vw);max-height:44px", page)
            self.assertIn('<button class="mobile-brand" type="button" aria-label="FIWS logo">', page)
            self.assertNotIn('<a class="mobile-brand" href="#home"', page)
            self.assertIn(".mobile-brand:active #mobile-logo svg,.mobile-brand:active #mobile-logo img,.mobile-brand:active #mobile-logo canvas{transform:scale(.96,.90)}", page)
            self.assertIn("all:unset;position:fixed", page)
            self.assertIn("background:transparent!important;box-shadow:none!important", page)
            self.assertNotIn("logo-tapped", page)
            self.assertIn("background:transparent!important;box-shadow:none!important", page)
            self.assertIn("max-width:min(144px,38vw);max-height:44px", page)
            self.assertIn(".fiws-secret-confetti{position:fixed;inset:0", page)
            self.assertIn("const targets=[$('#logo'),$('#mobile-logo')]", page)
            self.assertIn("taps=now-lastTap<3200?taps+1:1", page)
            self.assertIn("if(taps>=10){taps=0;launchSecretConfetti()}", page)
            self.assertIn("const colors=['#00AEEF','#E53945']", page)
            self.assertIn("matchMedia('(prefers-reduced-motion: reduce)').matches", page)
            self.assertIn(".nav-label{display:none}", page)
            self.assertIn(".ft{padding-bottom:calc(5.8rem + env(safe-area-inset-bottom,0px))}", page)
            self.assertIn("main{padding-bottom:calc(6.8rem + env(safe-area-inset-bottom,0px));scroll-margin-bottom:6.8rem}", page)
            self.assertIn("const NAV_ICONS=", page)
            self.assertIn('data-nav="${k}"', page)
            self.assertIn('id="nav-more"', page)
            self.assertIn('id="mobile-more" hidden', page)
            self.assertIn('aria-modal="true"', page)
            self.assertIn('data-more-link="admin"', page)
            self.assertIn("const openMore=()=>{moreSheet.hidden=false", page)
            self.assertIn("$('#theme-mobile').onclick=toggleTheme", page)
            self.assertIn(".nav a[data-nav=rules],.nav a[data-nav=apply],.nav a[data-nav=status]{display:none}", page)
            self.assertIn(".mobile-more{padding-bottom:calc(62px + env(safe-area-inset-bottom,0px))}", page)

    def test_leaderboard_round_titles_are_shortened_only_on_phones(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("function leaderboardRoundLabel(s,r)", page)
        self.assertIn("matchMedia('(max-width:700px)').matches", page)
        self.assertIn("paintLeaderboardRound(el,s,round)", page)
        self.assertIn("paintLeaderboardRound(el,s,max)", page)
        self.assertIn("grand prix", page)
        self.assertIn("return 'R'+c.n+' - '+code", page)
        self.assertIn("function leaderboardPhoneText(s)", page)
        self.assertIn(r"/\p{Extended_Pictographic}/gu", page)
        self.assertIn("esc(leaderboardPhoneText(d.name))", page)
        self.assertIn("leaderboardPhoneText([i.num,i.nat,i.team].filter(Boolean).join(' · '))", page)

    def test_former_grid_status_starts_after_workbook_exit_round(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("function entryGridExitRound(s,name)", page)
        self.assertIn(r"/\bR\s*(\d+)\s*-\s*(\d*)\b/gi", page)
        self.assertIn("return Number(currentRound)>entryExit", page)
        self.assertIn("row.classList.toggle('former-grid',former)", page)
        self.assertIn("formerTag.textContent=formerGridExitLabel(s,d.name)", page)
        self.assertIn("Left after R", page)
        self.assertIn(".tr.former-grid .pt{color:var(--mute)}", page)

    def test_mobile_interface_uses_no_arrow_glyphs_or_text_chevrons(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn(r"\u2190-\u21FF", page)
        self.assertIn(".home-intro .btn::after{content:none!important}", page)
        self.assertIn('<svg class="chev" viewBox="0 0 16 16"', page)
        self.assertNotIn('>◐</button>', page)

    def test_standings_includes_all_entry_drivers_even_without_points_rows(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("function allSeasonDrivers(s)", page)
        self.assertIn("(s.drivers||[]).forEach(entry=>", page)
        self.assertIn("vals:s.codes.map(()=>0)", page)
        self.assertIn("const standingsSeason=k==='drv'?{...s,drv:allSeasonDrivers(s)}:s", page)
        self.assertIn("tower($('#tw'),standingsSeason,k,l.length)", page)

    def test_leaderboard_cancelled_rounds_use_compact_red_marker(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("function paintLeaderboardRound(el,s,r)", page)
        self.assertIn("mark.textContent='(C)'", page)
        self.assertIn(".cancel-mark{display:inline-block;color:#ef9292", page)
        self.assertIn("leaderboardRoundLabel(s,r)", page)

    def test_fitc_live_dot_accepts_live_status_variants(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("/^(ONGOING|LIVE|ACTIVE)$/i.test(String(s.status||''))", page)
        self.assertIn(":root[data-series=FITC] .live{background:var(--sky)", page)

    def test_home_discord_fallback_is_join_link_and_unneeded_tagline_removed(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertNotIn("If the panel does not appear", page)
        self.assertIn("Join the server", page)
        self.assertIn("https://discord.gg/9uUdUCVnNN", page)
        self.assertNotIn("https://discord.com/servers/1430272514591817861", page)
        self.assertNotIn("Live server preview loads automatically", page)
        self.assertIn("The FIWS paddock.", page)

    def test_standings_dynamic_entries_are_not_hard_coded_and_zero_point_rows_remain_visible(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("entry.Driver??entry['Driver Name']??entry.Name", page)
        self.assertIn("const driverEntryName=d=>String(d?.Driver??d?.['Driver Name']??d?.Name??'')", page)
        self.assertIn("normalize('NFKC').replace(/\\s+/g,' ').trim().toLocaleLowerCase()", page)
        self.assertIn("e=(s.drivers||[]).find(d=>driverEntryName(d).toLocaleLowerCase()===key)", page)
        self.assertIn("e.Team??e['Team Name']??e.Constructor??''", page)
        self.assertIn("if(!l.length||(k==='con'&&s.done<0))", page)
        self.assertIn("s.done>=0?(d.vals[s.done]??0):0", page)
        for name in ("Yoshinaran", "29deCesaris", "Mariusz", "Formula B", "Protomango", "Jetto", "Yishmate", "P1K5UP", "BlackDragon", "Endo", "Putra", "Pmoneyspread"):
            self.assertNotIn(name, page)

    def test_homepage_ctas_have_distinct_but_coordinated_interactions(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn(".home-intro .btn:first-child::after", page)
        self.assertIn(".home-intro .btn.ghost::after", page)
        self.assertIn(".home-info .btn:not(.ghost)", page)
        self.assertIn(".home-info .btn:hover,.home-intro .btn:hover", page)

    def test_leaderboard_rank_swaps_animate_during_slider_scrubbing(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("transition:transform .5s cubic-bezier(.22,.75,.25,1)", page)
        self.assertNotIn(".tower.scrubbing .tr{transition:none!important}", page)
        self.assertIn("@media(max-width:700px){.tower .tr{transition-duration:.42s}", page)

if __name__ == "__main__":
    unittest.main()
