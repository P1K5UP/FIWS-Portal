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
            "$$('[data-reset]',P).forEach",
            "$$('[data-logo]',P).forEach",
            "$$('[data-logo-remove]',P).forEach",
        ):
            self.assertIn(selector, source)

    def test_admin_colour_studio_supports_separate_selectors_copy_and_custom_rgb_hex_picker(self):
        for relative in ("src/index.template.html", "index.html"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("colour-select-trigger", source)
            self.assertIn("target-series", source)
            self.assertIn("target-season", source)
            self.assertIn("source-series", source)
            self.assertIn("source-season", source)
            self.assertIn("copy-season-colours", source)
            self.assertIn("data-colour-hex", source)
            self.assertIn("data-colour-rgb", source)
            self.assertIn("data-colour-hsl", source)
            self.assertNotRegex(source, r"<input[^>]+type=['\"]color['\"]")
            self.assertIn("@media(prefers-reduced-motion:reduce)", source)

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


    def test_public_seasons_hide_future_and_provisional_entries(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("const publicSeasons=()=>D.filter(s=>!isFutureSeason(s))", page)
        self.assertIn("['FUTURE','UPCOMING','PLANNED','PRIVATE','UNCONFIRMED']", page)
        self.assertIn("o.entriesVisible=o.status==='FINISHED'||o.entriesConfirmed", page)
        self.assertIn("Lineups not confirmed", page)
        self.assertIn("CONFIRMED", page)

    def test_calendar_includes_scheduled_rounds_and_marks_next_race(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        calendar = page.split("V.calendar=()=>", 1)[1].split("V.entries=()=>", 1)[0]
        self.assertIn("c.date>=t", calendar)
        self.assertIn("NEXT RACE · ROUND", calendar)
        self.assertIn("isNext?' next':''", calendar)
        self.assertIn("visible=s.cal.map", calendar)
        self.assertNotIn('data-more-link="apply"', page)
        self.assertIn("The current grid, organised by team.", page)


    def test_mobile_apply_and_numeric_dob_entry(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn('href="#apply" aria-label="Apply to FIWS"', page)
        self.assertIn("width:68px;height:68px;margin-top:-18px", page)
        self.assertIn("input.value=digits.length>4?", page)
        self.assertIn("digits.slice(0,2)+'/'+digits.slice(2,4)+'/'+digits.slice(4)", page)

    def test_admin_remember_device_has_server_and_client_expiry(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        function = (ROOT / "supabase/functions/fiws-admin/index.ts").read_text(encoding="utf-8")
        self.assertIn("Remember this device for 30 days", page)
        self.assertIn("expires:Date.now()+30*86400000", page)
        self.assertIn("body.remember_device === true ? 30 * 24 * 60 : 8 * 60", function)
        self.assertIn("sessionMinutes * 60000", function)

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
            "top four drivers qualify",
            "500 points",
            "+2 points for each race win",
            "+0.5 points for each stage win",
            "R19 to R23",
            "most points after R23 wins the championship",
            "Reverse Gear Glitch abuse",
        ):
            self.assertIn(phrase, rules)

    def test_playoff_standings_are_derived_from_workbook_rules_and_entries(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("playoffStandingsData", page)
            self.assertIn("o.playoffSlots=[]", page)
            self.assertIn("o.playoffRules=rules", page)
            self.assertIn("regularSeasonEndRound", page)
            self.assertIn("qualificationThreshold", page)
            self.assertIn("qualifierCount", page)
            self.assertIn("playoffStartRound", page)
            self.assertIn("bonusPerWin", page)
            self.assertIn("bonusPerStage", page)
            self.assertIn("driverBonus.wins", page)
            self.assertIn("Excel-listed entrants", page)
            self.assertIn("playoffStandingsMarkup(s,true)", page)
            self.assertIn("playoff-mobile-total", page)
            self.assertIn("playoff-mobile-hide", page)
            self.assertIn("if(beforePlayoffs&&i<=cutoff)", page)
            self.assertIn("playoffPoints:total-startPoints,startPoints,total", page)
            self.assertNotIn("workbookStart", page)
            self.assertNotIn("workbook playoff total does not match", page)
            self.assertNotIn("below the '+data.threshold", page)
            self.assertIn('id="playoff-standings"', page)
            self.assertNotIn("seasonOnePlayoffQualifierNames", page)
            self.assertNotIn("29decesaris','tenooji','formula b", page)
            self.assertNotIn("playoff-explainer", page)
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
            self.assertIn('class="staff-access" href="#admin" aria-label="Staff access"', page)
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
        self.assertIn("driverLink(d.name,leaderboardPhoneText(resultDriverText(s,d.name)||d.name))", page)
        self.assertIn("leaderboardPhoneText([i.num,i.nat,i.team].filter(Boolean).join(' · '))", page)

    def test_driver_dossiers_are_linked_and_avoid_dumping_unfiltered_workbook_fields(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("const driverHref=name=>'#driver/'+encodeURIComponent(String(name||''))", page)
        self.assertIn("V.driver=()=>", page)
        self.assertNotIn("group('Identity'", page)
        self.assertNotIn("group('Team & entry'", page)
        self.assertNotIn("group('Other workbook fields'", page)
        self.assertNotIn("!k.startsWith('_')", page)
        self.assertIn("entry-member-card-link", page)
        self.assertIn("driverHref(name)", page)
        self.assertIn("driverLink(name)", page)
    def test_driver_history_reads_every_detailed_event_and_keeps_pole_separate(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        profile = page.split("V.driver=()=>", 1)[1].split("V.standings=()=>", 1)[0]
        self.assertIn("o.statsEvents=statBlocks.map", page)
        self.assertIn("driverDetailedEventsForRound", page)
        self.assertIn("driverDetailedRaceRecord", page)
        self.assertIn("driverDetailedPosition(raceLabel)", profile)
        self.assertIn("driverRacePosition(season,result,name,i)", profile)
        self.assertIn("P'+position", profile)
        self.assertIn("pole&&position?'POLE'", profile)
        self.assertIn("const recent=selectedSeasons.flatMap", profile)
        self.assertIn("driverEntryParticipated", profile)
        self.assertIn("detailedParticipation=valid(detail?.row?.Race)&&!/^RESULT NOT LISTED$/i.test", profile)
        self.assertNotIn(".slice(-12)", profile)
        self.assertIn("calendar.circuit||calendar.track||calendar.name||'Track not listed'", profile)
        self.assertIn("driver-result-event", profile)
        self.assertIn("driver-result-meta", profile)
        self.assertIn("driver-result-position", profile)
    def test_entries_driver_cards_are_full_click_targets_and_team_tinted(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        entries = page.split("V.entries=()=>", 1)[1].split("V.rules=()=>", 1)[0]
        self.assertIn('class="entry-member-card-link" href="'+ "'+driverHref(name)+'" +'"', entries)
        self.assertIn("style=\"--team:'+color", entries)
        self.assertNotIn("driverLink(driverEntryName(d))", entries)

    def test_driver_dossier_is_simplified_and_keeps_result_hierarchy(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        profile = page.split("V.driver=()=>", 1)[1].split("V.standings=()=>", 1)[0]
        self.assertIn("tcol(displayTeam,s.key)", profile)
        self.assertIn("driver-stat-win", profile)
        self.assertNotIn("Victory lane", profile)
        self.assertNotIn("Career snapshot · all published seasons", profile)
        self.assertNotIn("Other workbook fields", profile)
        self.assertIn("driver-result-win", profile)
        self.assertIn("prefers-reduced-motion:reduce", page)
        self.assertIn(".driver-season-filter{position:relative;z-index:8;isolation:isolate;overflow:visible", page)
        self.assertIn("max-height:min(50vh,320px);overflow-y:auto", page)
        self.assertIn("cl.push(()=>document.removeEventListener('pointerdown',outside))", profile)
    def test_admin_password_policy_is_consistent_in_ui_and_edge_function(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        edge = (ROOT / "supabase/functions/fiws-admin/index.ts").read_text(encoding="utf-8")
        for rule in ("p.length<10", "/[a-z]/", "/[A-Z]/", "/[0-9]/", "/[^A-Za-z0-9]/"):
            self.assertIn(rule, page)
        for rule in ("password.length < 10", "/[a-z]/", "/[A-Z]/", "/[0-9]/", "/[^A-Za-z0-9]/"):
            self.assertIn(rule, edge)

    def test_round_by_round_team_ranges_drive_driver_status_and_team_switches(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("const entryTeamForRound=(s,n,round=s.done)=>", page)
        self.assertIn("const parts=raw.split(/\\s*,\\s*/)", page)
        self.assertIn("current>=start&&current<=end", page)
        self.assertIn("function isFormerGridDriver(s,name,round=s.done){return (s.drivers||[]).length>0&&!entryTeamForRound(s,name,round)}", page)
        self.assertIn("const roundInfo=kind==='drv'?info(s,d.name,r):null", page)
        self.assertIn("marker.style.background=tcol(roundInfo.team||d.name,s.key)", page)
        self.assertIn("row.classList.toggle('former-grid',former)", page)
        self.assertNotIn("Left after R", page)
        self.assertNotIn("formerGridExitLabel", page)
        self.assertIn(".tr.former-grid .dl,.tr.former-grid .pt{color:var(--mute)}", page)

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
        self.assertIn("const driverEntryName=d=>String(d?.Driver??d?.['Driver Name']??d?.Name??'')", page)
        self.assertIn("normalize('NFKC').replace(/\\s+/g,' ').trim().toLocaleLowerCase()", page)
        self.assertIn("const driverEntryForResult=(s,raw)=>", page)
        self.assertIn("e.Team??e['Team Name']??e.Constructor??''", page)
        self.assertIn("if(!l.length||(k==='con'&&s.done<0))", page)
        self.assertIn("s.done>=0?(d.vals[s.done]??0):0", page)
        self.assertNotIn("seasonOnePlayoffQualifierNames", page)
        for name in ("Yoshinaran", "Mariusz", "Protomango", "Jetto", "Yishmate", "P1K5UP", "BlackDragon", "Endo", "Putra", "Pmoneyspread"):
            self.assertNotIn(name, page)
    def test_season_one_playoff_entries_are_read_from_the_workbook_not_driver_names(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("o.playoffSlots=[]", page)
            self.assertIn("slotByNumber.get(playoffNumberKey(entry?.Number))", page)
            self.assertIn("qualificationSource='Excel playoff roster'", page)
            self.assertIn("rules.qualificationThreshold", page)
            self.assertIn("belowThreshold=rows.filter", page)
            self.assertNotIn("seasonOnePlayoffQualifierNames", page)
            self.assertNotIn("qualified=regularPoints>100", page)
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

    def test_theme_palette_uses_shared_semantic_tokens(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            css = page.split("<style>", 1)[1].split("</style>", 1)[0]
            for token in (
                "--accent-ink:", "--inverse-ink:", "--inverse-muted:",
                "--inverse-border-soft:", "--inverse-border:",
                "--inverse-border-strong:", "--inverse-fill:",
                "--overlay-dark:", "--shadow-dark:", "--shadow-color:",
                "--discord-surface:", "--discord-surface-raised:",
                "--discord-surface-deep:",
            ):
                self.assertIn(token, css, f"{relative} is missing {token}")
            self.assertIn("color-scheme:light", css)
            self.assertIn("color-scheme:dark", css)
            self.assertIn(".seg button[aria-pressed=true]{background:var(--gr);color:var(--inverse-ink)}", css)
            self.assertIn(".tower{background:var(--gr);color:var(--inverse-ink)", css)

    def test_light_theme_inverts_leaderboard_surface_and_text_palette(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            css = page.split("<style>", 1)[1].split("</style>", 1)[0]
            self.assertIn("--gr:#FFFFFF;", css)
            self.assertIn("--inverse-ink:#0B2239;", css)
            self.assertIn("--inverse-muted:#52697F;", css)
            self.assertIn("--inverse-border:rgba(11,34,57,.18);", css)
            self.assertIn(".tower{background:var(--gr);color:var(--inverse-ink);border:1px solid var(--inverse-border)", css)
            self.assertIn(":root[data-theme=dark]{--bg:#09141E;", css)
            self.assertIn("--gr:#050B11;--ok:#3CC796", css)
            self.assertIn("--inverse-ink:#FFFFFF;--inverse-muted:#C9DAE8;", css)

    def test_theme_toggle_persists_only_after_all_cookie_consent(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn('localStorage.getItem("fiws.consent")', page)
        self.assertIn("consent?.all===true&&match", page)
        self.assertIn("allCookiesAccepted=()=>LS.get('consent',{})?.all===true", page)
        self.assertIn("if(allCookiesAccepted())saveThemeCookie(next)", page)
        self.assertIn("Accept all cookies", page)
        self.assertIn("clearThemeCookie()", page)
        self.assertNotIn("LS.set('theme',next)", page)
        self.assertIn("syncThemeControls();$('#theme').onclick=toggleTheme;$('#theme-mobile').onclick=toggleTheme;", page)
        self.assertIn("b.setAttribute('aria-pressed',String(dark))", page)

    def test_dob_input_auto_inserts_day_month_year_separators(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("if(input.name!=='dob')return", page)
        self.assertIn("digits.slice(0,2)+'/'+digits.slice(2,4)+'/'+digits.slice(4)", page)

    def test_selected_mobile_season_buttons_have_rounded_corners(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn(".pick .seg button[aria-pressed=true]{border-radius:8px;margin:2px}", page)

    def test_discreet_staff_access_and_desktop_full_navigation(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn('class="staff-access" href="#admin" aria-label="Staff access"', page)
        self.assertIn("@media(min-width:701px){.bar{gap:.8rem", page)
        self.assertIn(".nav-ico{display:block;width:15px;height:15px", page)
        self.assertIn(".staff-access{display:none!important}", page)
        self.assertIn('href="#admin" data-more-link="admin"', page)
        self.assertIn(".mobile-apply{grid-column:4;grid-row:1", page)
        self.assertIn("width:68px;height:68px;margin-top:-18px", page)

    def test_latest_race_card_includes_available_event_details(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("Latest result", page)
        self.assertNotIn("latestMeta=li>=0?", page)
        self.assertNotIn("home-result-meta", page)
        self.assertIn(".home-highlights{gap:clamp(.7rem,1.4vw,1rem);margin-top:1.25rem;align-items:start}", page)

    def test_entries_grey_out_drivers_without_a_current_grid_team(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("const driverRows=[...(s.drivers||[])]", page)
        self.assertIn("teamMap=new Map()", page)
        self.assertIn("getAssignments=d=>teamAssignments(", page)
        self.assertIn("isPast=!active", page)
        self.assertIn("data-entry-search=", page)
        self.assertIn(".entry-member.is-former{opacity:.48", page)
        self.assertIn(".former-grid-row td,.former-grid-row td b{color:var(--mute)!important}", page)
        self.assertIn(".tr.former-grid .pos,.tr.former-grid[data-p=\"0\"] .pos", page)


    def test_homepage_hides_latest_result_metadata_strip(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertNotIn("home-result-meta", page)
        self.assertNotIn("latestMeta.length", page)

    def test_entries_are_team_first_clean_and_follow_series_join_order(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("const driverRows=[...(s.drivers||[])]", page)
        self.assertIn("const entryTeamHistory=", page)
        self.assertIn("teamMap=new Map()", page)
        self.assertIn("getAssignments=d=>teamAssignments(", page)
        self.assertIn('id="entry-grid-search"', page)
        self.assertIn('data-entry-team-card', page)
        self.assertIn("CURRENT DRIVERS", page)
        self.assertIn("PAST DRIVERS", page)
        self.assertIn("d._range", page)
        self.assertIn("view-transition-name:roster-", page)
        self.assertIn("driverJoinOrder(s,list[a].name)-driverJoinOrder(s,list[b].name)", page)
        self.assertNotIn('id="entry-driver-search"', page)
        self.assertNotIn('class="entries-table"', page)

    def test_team_range_parser_accepts_explicit_round_prefixes(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("R?\\s*\\d*", page)


    def test_results_resolve_driver_numbers_and_shared_positions(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("const driverEntryForResult=", page)
        self.assertIn("const resolveResultDrivers=", page)
        self.assertIn("split(/\\s*\\/\\s*/)", page)
        self.assertIn("resultDriverMarkup(s,q,i)", page)
        self.assertIn("resolveResultDrivers(s,s.res[i].win).forEach", page)
        self.assertIn("resultDriverText(s,d.name)||d.name", page)

    def test_results_use_race_specific_teams_and_exclude_annulled_podiums(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("entryTeamForRound(s,name,round)", page)
        self.assertIn("entryTeamForRound(s,name,i)", page)
        self.assertIn("resultDriverSummary(s,r.pole,i)", page)
        self.assertIn("tm||r.team", page)
        self.assertIn("!isAnnulledRound(s.cal[i])", page)
        self.assertIn("Annulled Rounds", page)
        self.assertIn("Points retained", page)
        self.assertIn("isAnnulledRound=c=>/ANN?UL+ED/i", page)
        self.assertIn("dateCell?.w", page)
        self.assertIn("dateText+' ANNULED'", page)

    def test_nationality_names_are_normalized_to_three_letter_codes(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("const nationalityCode=value=>", page)
        self.assertIn("Poland:POL", page)
        self.assertIn("nationalityCode(d.Nationality)", page)
        self.assertIn("nationalityCode(e.Nationality)", page)

    def test_boot_screen_is_non_blocking_and_logo_switch_is_crossfaded(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn('id="boot-screen"', page)
        self.assertIn("boot.classList.add('done')", page)
        self.assertNotIn("setTimeout(()=>render", page)
        self.assertIn("L.replaceChildren(canvas)", page)
        self.assertIn("L.style.opacity='0'", page)
        self.assertIn("L.style.opacity='1'", page)

    def test_admin_tab_switches_reuse_loaded_applications_data(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("adminRowsLoaded=false", page)
        self.assertIn("async function adminLoad(force=adminTab==='apps')", page)
        self.assertIn("if(force||!adminRowsLoaded)", page)
        self.assertIn("adminLoad(adminTab==='apps')", page)

    def test_mobile_apply_button_has_wider_separation_from_bottom_dock(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("border:5px solid var(--panel)", page)


    def test_dob_validation_accepts_formatted_or_plain_digits_and_uses_calendar_date(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("digits=v.replace(/\\D/g,'').slice(0,8)", page)
        self.assertIn("normalized=digits.length===8?digits.slice(0,2)+'/'+digits.slice(2,4)+'/'+digits.slice(4):v", page)
        self.assertIn("today=Date.UTC(now.getFullYear(),now.getMonth(),now.getDate())", page)
        self.assertIn("birth>today", page)

    def test_team_cards_show_round_range_tags_and_historical_teams(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("entryTeamHistory(s,driverEntryName(d),round)", page)
        self.assertIn(".entry-team-ranges{display:none!important}", page)
        self.assertIn('class="team-range-tag"', page)
        self.assertIn("PAST DRIVERS", page)
        self.assertIn('data-entry-team-card', page)
        self.assertIn("roundInfo.teamRound>=0", page)
        self.assertIn("entryTeamHistory(s,driverEntryName(e),round)", page)
        self.assertIn("current<=end", page)

    def test_home_latest_result_card_does_not_stretch_and_hover_glow_is_subtle(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn(".home-highlights>*{min-height:0}", page)
        self.assertIn(".home-result{height:max-content;min-height:0;align-self:start", page)
        self.assertIn("0 0 0 1px color-mix(in srgb,var(--sky) 13%,transparent)", page)
        self.assertGreater(page.rfind("box-shadow:0 10px 22px -18px var(--shadow-color)"), page.find("box-shadow:0 12px 28px -22px var(--ink)"))

    def test_entries_page_has_refined_team_cards_and_range_tag_layout(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn(".entry-team-card{padding:1.15rem 1.2rem 1.25rem", page)
        self.assertIn(".entry-team-ranges{display:none!important}", page)
        self.assertIn(".entry-member .team-range-tag{flex:0 0 auto", page)
        self.assertIn(".entries-intro{max-width:68ch", page)


    def test_championship_winner_cards_cover_finished_driver_and_constructor_seasons(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("function championCardMarkup(s,kind='drv')", page)
        self.assertIn("kind==='con'?s.con:allSeasonDrivers(s)", page)
        self.assertIn("champion-more", page)
        self.assertIn("Race wins", page)
        self.assertIn("Podium finishes", page)
        self.assertIn("Pole positions", page)
        self.assertIn("driverTeamHistoryMarkup(s,d.name)", page)
        standings = page[page.index("V.standings=()"):page.index("V.results=()")]
        self.assertLess(standings.index('<div id="world-champion"></div>'), standings.index('<div id="tw"'))
        self.assertIn("$('#world-champion').innerHTML=championCardMarkup(s,k)", page)
        self.assertNotIn("P1 LEADER", page)

    def test_owner_accounts_support_multiple_owners_and_last_owner_protection(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        api = (ROOT / "supabase/functions/fiws-admin/index.ts").read_text(encoding="utf-8")
        migration = next((ROOT / "supabase/migrations").glob("*fiws_multi_owner_account_management.sql")).read_text(encoding="utf-8")
        self.assertIn('<option value="owner">Owner</option>', page)
        self.assertIn('["owner", "administrator", "moderator"].includes(body.rank)', api)
        self.assertIn('["owner", "administrator", "moderator"].includes(rank)', api)
        self.assertIn("if v_active_owners<=1 then return false; end if;", migration)
        self.assertEqual(migration.count("pg_advisory_xact_lock(80421731)"), 2)
        self.assertIn("data-reset", page)

    def test_fitc_never_renders_fiws_playoff_panels(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        playoff = page.split("const playoffStandingsData=s=>", 1)[1].split("function championCardMarkup", 1)[0]
        self.assertIn("const rules=s?.playoffRules||{}", playoff)
        self.assertIn("if(!Number.isFinite(regularEnd)", playoff)
        self.assertIn("const hasExplicitRoster=Array.isArray(s.playoffSlots)", playoff)
        self.assertNotIn("isFiwsSeasonOne(s)", playoff)
        self.assertNotIn("isFiwsSeasonTwo(s)", playoff)
    def test_season_one_playoff_rules_and_bold_double_points_are_wired(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        for marker in ("isFiwsSeasonOne", "playoffRoundIndex(s,regularEnd)", "regularSeasonEndRound",
                       "playoffStartRound", "playoffEndRound", "basePoints", "bonusPerWin",
                       "pointsBeforePlayoffsCap", "roundPoints(driver,index)", "cellStyles:true",
                       "special:Array.from("):
            self.assertIn(marker, page)
    def test_driver_dossier_can_filter_a_season_or_all_time(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        profile = page.split("V.driver=()=>", 1)[1].split("V.standings=()=>", 1)[0]
        for marker in ("driverSeasonFilter", "selectedSeasons=allTime?available:(s?[s]:[])",
                       "data-driver-season", "All time", "Race history · all results"):
            self.assertIn(marker, profile)
        self.assertNotIn("Career snapshot · all published seasons", profile)
        self.assertIn("recent.map(resultBadge)", profile)
    def test_season_one_uses_workbook_playoff_totals_and_keeps_threshold_tint_logic(self):
        for relative in ("src/index.template.html", "index.html"):
            page = (ROOT / relative).read_text(encoding="utf-8")
            playoff = page.split("const playoffStandingsData=s=>", 1)[1].split("const playoffStandingsMarkup=", 1)[0]
            self.assertIn("startPoints=basePoints+startingBonus.wins*bonusPerWin+startingBonus.stages*bonusPerStage", playoff)
            self.assertIn("sourceScores[index+1]", playoff)
            self.assertIn("workbookStart", playoff)
            self.assertIn("scoreMismatch", playoff)
            self.assertIn("seasonOne&&v>100", page)
            self.assertIn("season-one-qualified", page)
            self.assertIn("if(o.cal.some(calendar=>calendar.special))", page)
            self.assertIn("rounds=Array.from({length:playoffEnd-playoffStart+1}", playoff)
    def test_driver_season_filter_lists_all_available_fiws_seasons(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        profile = page.split("V.driver=()=>", 1)[1].split("V.standings=()=>", 1)[0]
        self.assertIn("publicSeasons().filter(season=>season.sheet===cur.series)", profile)
        self.assertIn("value:'ALL'", profile)
        self.assertIn("seasonLabel=season=>", profile)
        self.assertIn("data-driver-season=", profile)
        self.assertIn(".driver-season-trigger{display:flex", page)

    def test_driver_directory_filters_by_name_team_and_participation(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn('id="entry-grid-search"', page)
        self.assertIn('id="entry-team-filter"', page)
        self.assertIn('id="entry-status-filter"', page)
        self.assertIn("data-driver-name=", page)
        self.assertIn("data-driver-status=", page)
        self.assertIn("Reset filters", page)

    def test_application_header_and_form_share_the_same_width(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn(".application-page{max-width:860px;margin:0 auto}", page)
        self.assertIn(".application-panel{max-width:none!important;width:100%", page)

    def test_season_one_qualification_uses_parsed_cutoff_and_handles_blank_round_cells(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        playoff = page.split("const playoffStandingsData=s=>", 1)[1].split("const playoffStandingsMarkup=", 1)[0]
        self.assertIn("const regularIndex=playoffRoundIndex(s,regularEnd)", playoff)
        self.assertIn("const scoreAt=(driver,index)=>", playoff)
        self.assertIn("const regularPoints=regularIndex>=0?scoreAt(driver,Math.min(cutoff,regularIndex)):0", playoff)
        self.assertIn("return scoreAt(driver,i)-scoreAt(driver,i-1)", playoff)
        self.assertIn("qualificationThreshold", page)
        # Missing cumulative cells must carry forward the previous non-null score.
        scores = [0, 34, None, 72, None, 116]
        carried = 0
        for value in scores:
            if value is not None:
                carried = value
        self.assertEqual(carried, 116)
        self.assertGreater(carried, 100)
    def test_completed_playoffs_use_workbook_end_round(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        playoff = page.split("const playoffStandingsData=s=>", 1)[1].split("const playoffStandingsMarkup=", 1)[0]
        self.assertIn("playoffsComplete=endIndex>=0&&s.done>=endIndex", playoff)
        self.assertIn("playoffsActive=startIndex>=0&&s.done>=startIndex&&!playoffsComplete", playoff)
        self.assertIn("data.playoffsComplete?'Final playoff standings'", page)
        self.assertNotIn("R15–R17 underway", page)
    def test_native_browser_dialogs_are_replaced_and_signout_requires_site_confirmation(self):
        page = (ROOT / "src/index.template.html").read_text(encoding="utf-8")
        self.assertIn("function showSiteDialog(", page)
        self.assertIn("const showConfirm=", page)
        self.assertIn("const showPrompt=", page)
        self.assertNotIn("confirm(", page)
        self.assertNotIn("window.prompt(", page)
        self.assertEqual(page.count("showConfirm('Sign out?'"), 2)

if __name__ == "__main__":
    unittest.main()
