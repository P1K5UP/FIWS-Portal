import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.119.2";
import { argon2id, argon2Verify } from "npm:hash-wasm@4.13.0";

const SITE_ORIGIN = "https://p1k5up.github.io";
const cors = {
  "Access-Control-Allow-Origin": SITE_ORIGIN,
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info, x-fiws-session, x-fiws-bootstrap-secret, x-fiws-owner-recovery-secret",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Vary": "Origin",
};
const url = Deno.env.get("SUPABASE_URL")!;
const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const db = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
async function mustSucceed(operation: PromiseLike<{ error: { message?: string } | null }>) {
  const { error } = await operation;
  if (error) throw error;
}
const enc = new TextEncoder();
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" },
});
const b64 = (b: Uint8Array) => btoa(String.fromCharCode(...b)).replace(/=/g, "");
const unb64 = (s: string) => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const hex = (b: Uint8Array) => [...b].map(x => x.toString(16).padStart(2, "0")).join("");
const random = (n: number) => crypto.getRandomValues(new Uint8Array(n));
async function sha(value: string) { return hex(new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(value)))); }
async function hmac(value: string, secret: string) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(value))));
}
function same(a: string, b: string) {
  const x = enc.encode(a), y = enc.encode(b);
  let d = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) d |= (x[i] || 0) ^ (y[i] || 0);
  return d === 0;
}
async function hashPassword(password: string) {
  const salt = random(16);
  return await argon2id({ password, salt, parallelism: 1, iterations: 2, memorySize: 19456, hashLength: 32, outputType: "encoded" });
}
async function passwordOK(password: string, hash: string) {
  try { return await argon2Verify({ password, hash }); } catch { return false; }
}
let dummyPasswordHash: Promise<string> | null = null;
async function getDummyPasswordHash() {
  if (!dummyPasswordHash) dummyPasswordHash = hashPassword("FIWS dummy password timing equalizer");
  return await dummyPasswordHash;
}
async function encryptSecret(secret: string) {
  const raw = Deno.env.get("FIWS_TOTP_ENCRYPTION_KEY") || "";
  const keyBytes = unb64(raw);
  if (keyBytes.length !== 32) throw new Error("FIWS_TOTP_ENCRYPTION_KEY must be base64 for exactly 32 random bytes.");
  const key = await crypto.subtle.importKey("raw", keyBytes, "AES-GCM", false, ["encrypt"]);
  const iv = random(12);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, enc.encode(secret));
  return { ciphertext: b64(new Uint8Array(ciphertext)), iv: b64(iv) };
}
async function decryptSecret(ciphertext: string, iv: string) {
  const keyBytes = unb64(Deno.env.get("FIWS_TOTP_ENCRYPTION_KEY") || "");
  if (keyBytes.length !== 32) throw new Error("TOTP encryption key is not configured.");
  const key = await crypto.subtle.importKey("raw", keyBytes, "AES-GCM", false, ["decrypt"]);
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(iv) }, key, unb64(ciphertext));
  return new TextDecoder().decode(plain);
}
function base32(bytes: Uint8Array) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; let bits = 0, value = 0, out = "";
  for (const byte of bytes) { value = (value << 8) | byte; bits += 8; while (bits >= 5) { out += alphabet[(value >>> (bits - 5)) & 31]; bits -= 5; } }
  if (bits) out += alphabet[(value << (5 - bits)) & 31];
  return out;
}
function fromBase32(s: string) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; let bits = 0, value = 0; const out: number[] = [];
  for (const c of s.replace(/=+$/g, "").toUpperCase()) { const n = alphabet.indexOf(c); if (n < 0) throw new Error("Invalid TOTP secret."); value = (value << 5) | n; bits += 5; if (bits >= 8) { out.push((value >>> (bits - 8)) & 255); bits -= 8; } }
  return new Uint8Array(out);
}
async function totp(secret: string, step = Math.floor(Date.now() / 30000)) {
  const key = await crypto.subtle.importKey("raw", fromBase32(secret), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
  const msg = new Uint8Array(8); new DataView(msg.buffer).setBigUint64(0, BigInt(step));
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, msg));
  const offset = mac[mac.length - 1] & 15;
  const num = (((mac[offset] & 127) << 24) | (mac[offset + 1] << 16) | (mac[offset + 2] << 8) | mac[offset + 3]) % 1000000;
  return String(num).padStart(6, "0");
}
async function matchingTotpStep(secret: string, code: string) {
  if (!/^\d{6}$/.test(code)) return null;
  const now = Math.floor(Date.now() / 30000);
  for (let delta = -1; delta <= 1; delta++) if (same(await totp(secret, now + delta), code)) return now + delta;
  return null;
}
async function audit(admin: any, action: string, targetType?: string, targetId?: string, details = {}) {
  const { error } = await db.from("fiws_admin_audit_log").insert({
    actor_admin_id: admin?.id || null, actor_username: admin?.username || "bootstrap",
    actor_rank: admin?.admin_rank || "owner", action, target_type: targetType || null,
    target_id: targetId || null, details,
  });
  if (error) throw error;
}
async function newSession(adminId: string, verified: boolean, minutes: number) {
  const token = b64(random(32));
  const tokenHash = await sha(token);
  const { error } = await db.from("fiws_admin_sessions").insert({
    admin_id: adminId, token_hash: tokenHash, mfa_verified: verified,
    expires_at: new Date(Date.now() + minutes * 60000).toISOString(),
  });
  if (error) throw error;
  return token;
}
async function session(req: Request, requireMfa = true) {
  const token = req.headers.get("x-fiws-session") || "";
  if (token.length < 32 || token.length > 128) return null;
  const { data, error } = await db.from("fiws_admin_sessions")
    .select("id,admin_id,mfa_verified,expires_at,revoked_at,fiws_admin_accounts(id,username,display_name,admin_rank,disabled,totp_enabled)")
    .eq("token_hash", await sha(token)).is("revoked_at", null).gt("expires_at", new Date().toISOString()).maybeSingle();
  if (error || !data || !data.mfa_verified && requireMfa) return null;
  const admin = Array.isArray(data.fiws_admin_accounts) ? data.fiws_admin_accounts[0] : data.fiws_admin_accounts;
  if (!admin || admin.disabled) return null;
  await mustSucceed(db.from("fiws_admin_sessions").update({ last_seen_at: new Date().toISOString() }).eq("id", data.id));
  return { token, row: data, admin };
}
function allowedRank(rank: string, min: string) {
  const level: Record<string, number> = { moderator: 1, administrator: 2, owner: 3 };
  return (level[rank] || 0) >= (level[min] || 99);
}
function makeRecoveryCodes() {
  return Array.from({ length: 10 }, () => {
    const bytes = random(16);
    return [...bytes].map(x => x.toString(16).padStart(2, "0")).join("").toUpperCase().match(/.{1,4}/g)!.join("-");
  });
}
async function logbookAction(action: string, req: Request, body: any) {
  const auth = await session(req);
  if (!auth) return json({ error: "Authentication required." }, 401);
  if (action === "logbook-list") {
    const { data, error } = await db.from("fiws_staff_logbook").select("id,category,title,body,related_reference,pinned,created_by,created_at,updated_by,updated_at,archived_at,author:fiws_admin_accounts!fiws_staff_logbook_created_by_fkey(username,display_name)").is("archived_at", null).order("pinned", { ascending: false }).order("created_at", { ascending: false }).limit(200);
    if (error) return json({ error: "Could not load staff logbook." }, 500);
    return json({ entries: data || [] });
  }
  if (!allowedRank(auth.admin.admin_rank, "moderator")) return json({ error: "Insufficient permissions." }, 403);
  if (action === "logbook-create") {
    const category = ["general","handover","driver","team","application","incident","competition"].includes(body.category) ? body.category : "general";
    const title = String(body.title || "").trim().slice(0,160), text = String(body.body || "").trim().slice(0,12000);
    if (!title || !text) return json({ error: "A title and note are required." }, 400);
    const { data, error } = await db.from("fiws_staff_logbook").insert({
      category, title, body: text, related_reference: String(body.related_reference || "").trim().slice(0,120) || null,
      pinned: body.pinned === true, created_by: auth.admin.id,
    }).select("id").single();
    if (error) return json({ error: "Could not save the logbook entry." }, 500);
    await audit(auth.admin, "logbook.create", "logbook", data.id, { category });
    return json({ success: true, id: data.id }, 201);
  }
  if (action === "logbook-update" || action === "logbook-archive") {
    const id = String(body.id || "");
    const patch = action === "logbook-archive"
      ? { archived_at: new Date().toISOString(), updated_by: auth.admin.id, updated_at: new Date().toISOString() }
      : { title: String(body.title || "").trim().slice(0,160), body: String(body.body || "").trim().slice(0,12000), category: body.category, pinned: body.pinned === true, updated_by: auth.admin.id, updated_at: new Date().toISOString() };
    const { error } = await db.from("fiws_staff_logbook").update(patch).eq("id", id).is("archived_at", null);
    if (error) return json({ error: "Could not update the logbook entry." }, 500);
    await audit(auth.admin, action, "logbook", id);
    return json({ success: true });
  }
  return json({ error: "Unknown action." }, 400);
}
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    if (req.headers.get("origin") !== SITE_ORIGIN) return new Response("Forbidden", { status: 403 });
    return new Response("ok", { headers: cors });
  }
  if (req.method !== "POST") return json({ error: "Method not allowed." }, 405);
  if (req.headers.get("origin") !== SITE_ORIGIN) return json({ error: "Origin not allowed." }, 403);
  if (!url || !serviceKey) return json({ error: "Server is not configured." }, 503);
  let body: any;
  try { body = await req.json(); } catch { return json({ error: "Invalid JSON." }, 400); }
  const action = String(body.action || "");
  try {
    if (action === "bootstrap") {
      const expected = Deno.env.get("FIWS_BOOTSTRAP_SECRET") || "";
      const supplied = req.headers.get("x-fiws-bootstrap-secret") || "";
      if (expected.length < 40 || !same(expected, supplied)) return json({ error: "Bootstrap is unavailable or unauthorized." }, 403);
      const username = String(body.username || "").trim().toLowerCase();
      const displayName = String(body.display_name || "").trim();
      const password = String(body.password || "");
      if (!/^[a-z0-9][a-z0-9._-]{2,31}$/.test(username) || displayName.length < 1 || displayName.length > 80 || password.length < 14 || password.length > 128) return json({ error: "Username, display name or password does not meet the required format." }, 400);
      const passwordHash = await hashPassword(password);
      const { data: ownerId, error: bootstrapError } = await db.rpc("fiws_bootstrap_admin", {
        p_username: username, p_display_name: displayName, p_password_hash: passwordHash,
      });
      if (bootstrapError) {
        if (/already been completed|already consumed/i.test(bootstrapError.message || "")) return json({ error: "Bootstrap has already been completed." }, 409);
        throw bootstrapError;
      }
      const owner = { id: ownerId };
      const token = await newSession(owner.id, false, 15);
      await audit({ id: owner.id, username, admin_rank: "owner" }, "bootstrap.owner_created", "admin", owner.id);
      return json({ success: true, enrollment_required: true, session: token, username });
    }
    if (action === "login") {
      const username = String(body.username || "").trim().toLowerCase();
      const password = String(body.password || "");
      if (!/^[a-z0-9][a-z0-9._-]{2,31}$/.test(username) || password.length > 128) return json({ error: "Invalid username or password." }, 401);
      const ip = req.headers.get("cf-connecting-ip") || req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
      const pepper = Deno.env.get("FIWS_RATE_LIMIT_PEPPER") || "";
      if (pepper.length < 32) return json({ error: "Authentication service is not configured." }, 503);
      const ipHash = await hmac(ip, pepper);
      const key = await hmac(username, pepper);
      const { data: throttleData, error: throttleError } = await db.rpc("fiws_consume_admin_login_attempt", { p_username_key: key, p_ip_hash: ipHash });
      if (throttleError) throw throttleError;
      const throttle = Array.isArray(throttleData) ? throttleData[0] : throttleData;
      if (throttle?.locked_until && new Date(throttle.locked_until).getTime() > Date.now()) return json({ error: "Invalid username or password." }, 429);
      const { data: account, error: accountError } = await db.from("fiws_admin_accounts").select("*").eq("username", username).maybeSingle();
      if (accountError) throw accountError;
      const eligible = !!account && !account.disabled && (!account.locked_until || new Date(account.locked_until).getTime() < Date.now());
      const candidateHash = account?.password_hash || await getDummyPasswordHash();
      const passwordMatches = await passwordOK(password, candidateHash);
      const valid = eligible && passwordMatches;
      if (!valid) {
        if (account) {
          const failures = (account.failed_login_count || 0) + 1;
          await db.from("fiws_admin_accounts").update({
            failed_login_count: failures,
            locked_until: failures >= 5 ? new Date(Date.now() + Math.min(60, 5 * 2 ** Math.min(failures - 5, 4)) * 60000).toISOString() : null,
          }).eq("id", account.id);
        }
        return json({ error: "Invalid username or password." }, 401);
      }
      if (account.totp_enabled) {
        const secret = await decryptSecret(account.totp_secret_ciphertext, account.totp_secret_iv);
        const matchedStep = await matchingTotpStep(secret, String(body.otp || ""));
        if (matchedStep === null) {
          const failures = (account.failed_login_count || 0) + 1;
          const { error: lockError } = await mustSucceed(db.from("fiws_admin_accounts").update({ failed_login_count: failures, locked_until: failures >= 5 ? new Date(Date.now() + Math.min(60, 5 * 2 ** Math.min(failures - 5, 4)) * 60000).toISOString() : null }).eq("id", account.id));
          if (lockError) throw lockError;
          return json({ mfa_required: true, error: "Enter a valid authenticator code." }, 401);
        }
        const { data: stepUpdated, error: stepError } = await db.from("fiws_admin_accounts").update({ totp_last_step: matchedStep }).eq("id", account.id).or(`totp_last_step.is.null,totp_last_step.lt.${matchedStep}`).select("id").maybeSingle();
        if (stepError) throw stepError;
        if (!stepUpdated) {
          const failures = (account.failed_login_count || 0) + 1;
          await db.from("fiws_admin_accounts").update({ failed_login_count: failures, locked_until: failures >= 5 ? new Date(Date.now() + Math.min(60, 5 * 2 ** Math.min(failures - 5, 4)) * 60000).toISOString() : null }).eq("id", account.id);
          return json({ mfa_required: true, error: "That authenticator code has already been used. Wait for the next code." }, 401);
        }
        const token = await newSession(account.id, true, 8 * 60);
        await mustSucceed(db.from("fiws_admin_accounts").update({ failed_login_count: 0, locked_until: null, last_login_at: new Date().toISOString() }).eq("id", account.id));
        await mustSucceed(db.from("fiws_admin_login_limits").delete().eq("username_key", key).eq("ip_hash", ipHash));
        await audit(account, "auth.login", "admin", account.id);
        return json({ success: true, session: token, admin: { username: account.username, display_name: account.display_name, rank: account.admin_rank } });
      }
      const token = await newSession(account.id, false, 15);
      return json({ success: true, mfa_enrollment_required: true, session: token, username: account.username });
    }
    if (action === "mfa-enroll") {
      const auth = await session(req, false);
      if (!auth || auth.row.mfa_verified) return json({ error: "Enrollment session required." }, 401);
      const secret = base32(random(20));
      const encrypted = await encryptSecret(secret);
      const { error: enrollError } = await db.from("fiws_admin_accounts").update({ totp_secret_ciphertext: encrypted.ciphertext, totp_secret_iv: encrypted.iv, totp_enabled: false, totp_last_step: null }).eq("id", auth.admin.id);
      if (enrollError) throw enrollError;
      const uri = "otpauth://totp/" + encodeURIComponent("FIWS:" + auth.admin.username) + "?secret=" + secret + "&issuer=FIWS&algorithm=SHA1&digits=6&period=30";
      return json({ secret, otpauth_uri: uri });
    }
    if (action === "mfa-confirm") {
      const auth = await session(req, false);
      if (!auth || auth.row.mfa_verified) return json({ error: "Enrollment session required." }, 401);
      const { data: account, error: accountError } = await db.from("fiws_admin_accounts").select("*").eq("id", auth.admin.id).single();
      if (accountError) throw accountError;
      if (!account?.totp_secret_ciphertext) return json({ error: "Start authenticator enrollment first." }, 409);
      const secret = await decryptSecret(account.totp_secret_ciphertext, account.totp_secret_iv);
      const matchedStep = await matchingTotpStep(secret, String(body.otp || ""));
      if (matchedStep === null) return json({ error: "Authenticator code is incorrect." }, 401);
      const codes = makeRecoveryCodes();
      const rows = await Promise.all(codes.map(async code => ({ code_hash: await sha(code) })));
      const { data: confirmed, error: confirmError } = await db.rpc("fiws_confirm_admin_mfa", {
        p_admin_id: account.id, p_session_id: auth.row.id, p_matched_step: matchedStep, p_codes: rows,
      });
      if (confirmError) throw confirmError;
      if (!confirmed) return json({ error: "That authenticator code has already been used or the enrollment session expired." }, 409);
      return json({ success: true, recovery_codes: codes, admin: { username: account.username, display_name: account.display_name, rank: account.admin_rank } });
    }
    if (action === "session") {
      const auth = await session(req);
      return auth ? json({ authenticated: true, admin: { username: auth.admin.username, display_name: auth.admin.display_name, rank: auth.admin.admin_rank } }) : json({ authenticated: false }, 401);
    }
    if (action === "logout") {
      const auth = await session(req, false);
      if (auth) await mustSucceed(db.from("fiws_admin_sessions").update({ revoked_at: new Date().toISOString() }).eq("id", auth.row.id));
      return json({ success: true });
    }
    if (action === "owner-recover") {
      const expected = Deno.env.get("FIWS_OWNER_RECOVERY_SECRET") || "";
      const supplied = req.headers.get("x-fiws-owner-recovery-secret") || "";
      if (expected.length < 40 || !same(expected, supplied)) return json({ error: "Owner recovery is unavailable or unauthorized." }, 403);
      const password = String(body.new_password || "");
      if (password.length < 14 || password.length > 128) return json({ error: "Choose a password of at least 14 characters." }, 400);
      const passwordHash = await hashPassword(password);
      const { data: recovered, error } = await db.rpc("fiws_complete_owner_recovery", { p_password_hash: passwordHash });
      if (error) throw error;
      if (!recovered) return json({ error: "Owner recovery has already been consumed or no owner account exists." }, 409);
      return json({ success: true, message: "Owner password reset. All sessions and recovery codes were revoked. Sign in and enroll MFA again. Remove the consumed recovery secret from project secrets." });
    }
    if (action === "recover-password") {
      const username = String(body.username || "").trim().toLowerCase();
      const code = String(body.recovery_code || "").replace(/[^a-f0-9]/gi, "").toUpperCase();
      const password = String(body.new_password || "");
      if (!/^[a-z0-9][a-z0-9._-]{2,31}$/.test(username) || code.length !== 32 || password.length < 14 || password.length > 128) return json({ error: "Recovery could not be completed. Check the details or contact the FIWS owner." }, 400);
      const recoveryPepper = Deno.env.get("FIWS_RATE_LIMIT_PEPPER") || "";
      if (recoveryPepper.length < 32) return json({ error: "Recovery service is not configured." }, 503);
      const recoveryIp = req.headers.get("cf-connecting-ip") || req.headers.get("x-forwarded-for")?.split(",").at(-1)?.trim() || "unknown";
      const recoveryIpHash = await hmac(recoveryIp, recoveryPepper);
      const recoveryUsernameKey = await hmac(username, recoveryPepper);
      const { data: recoveryThrottle, error: recoveryThrottleError } = await db.rpc("fiws_consume_admin_login_attempt", { p_username_key: recoveryUsernameKey, p_ip_hash: recoveryIpHash });
      if (recoveryThrottleError) throw recoveryThrottleError;
      const recoveryLimit = Array.isArray(recoveryThrottle) ? recoveryThrottle[0] : recoveryThrottle;
      if (recoveryLimit?.locked_until && new Date(recoveryLimit.locked_until).getTime() > Date.now()) return json({ error: "Recovery could not be completed. Check the details or contact the FIWS owner." }, 429);
      const { data: account, error: accountError } = await db.from("fiws_admin_accounts").select("id,username,disabled").eq("username", username).maybeSingle();
      if (accountError) throw accountError;
      if (!account || account.disabled) return json({ error: "Recovery could not be completed. Check the details or contact the FIWS owner." }, 400);
      const { data: recovery, error: recoveryError } = await db.from("fiws_admin_recovery_codes").select("id").eq("admin_id", account.id).eq("code_hash", await sha(code.match(/.{1,4}/g)!.join("-"))).is("used_at", null).maybeSingle();
      if (recoveryError) throw recoveryError;
      if (!recovery) return json({ error: "Recovery could not be completed. Check the details or contact the FIWS owner." }, 400);
      const passwordHash = await hashPassword(password);
      const { data: recovered, error } = await db.rpc("fiws_complete_admin_recovery", {
        p_admin_id: account.id,
        p_recovery_code_id: recovery.id,
        p_password_hash: passwordHash,
        p_username_key: recoveryUsernameKey,
        p_ip_hash: recoveryIpHash,
      });
      if (error) throw error;
      if (!recovered) return json({ error: "Recovery code has already been used or the account is unavailable." }, 409);
      return json({ success: true, mfa_enrollment_required: true, message: "Password reset. Sign in and enroll your authenticator app again." });
    }
    if (action === "admin-list") {
      const auth = await session(req);
      if (!auth || auth.admin.admin_rank !== "owner") return json({ error: "Owner permission required." }, 403);
      const { data, error } = await db.from("fiws_admin_accounts").select("id,username,display_name,admin_rank,totp_enabled,disabled,created_at,last_login_at,password_changed_at").order("created_at");
      if (error) return json({ error: "Could not load administrator accounts." }, 500);
      return json({ admins: data || [] });
    }
    if (action === "admin-create") {
      const auth = await session(req);
      if (!auth || auth.admin.admin_rank !== "owner") return json({ error: "Owner permission required." }, 403);
      const username = String(body.username || "").trim().toLowerCase();
      const displayName = String(body.display_name || "").trim();
      const password = String(body.password || "");
      const rank = ["administrator", "moderator"].includes(body.rank) ? body.rank : "";
      if (!/^[a-z0-9][a-z0-9._-]{2,31}$/.test(username) || !displayName || displayName.length > 80 || password.length < 14 || password.length > 128 || !rank) return json({ error: "Username, display name, rank or password does not meet requirements." }, 400);
      const { data, error } = await db.from("fiws_admin_accounts").insert({
        username, display_name: displayName, admin_rank: rank,
        password_hash: await hashPassword(password), password_salt: "embedded-in-argon2id-hash",
        created_by: auth.admin.id,
      }).select("id,username,admin_rank").single();
      if (error) return json({ error: "Could not create administrator. The username may already be taken." }, 409);
      await audit(auth.admin, "admin.create", "admin", data.id, { rank });
      return json({ success: true, admin: data, note: "The new administrator must enroll authenticator MFA at first sign-in." }, 201);
    }
    if (action === "admin-change-rank") {
      const auth = await session(req);
      if (!auth || auth.admin.admin_rank !== "owner") return json({ error: "Owner permission required." }, 403);
      const id = String(body.id || ""), rank = String(body.rank || "");
      if (!id || id === auth.admin.id || !["administrator", "moderator"].includes(rank)) return json({ error: "Invalid rank change." }, 400);
      const { data: target } = await db.from("fiws_admin_accounts").select("id,username,admin_rank").eq("id", id).maybeSingle();
      if (!target || target.admin_rank === "owner") return json({ error: "Owner rank cannot be reassigned here." }, 403);
      const { error } = await db.from("fiws_admin_accounts").update({ admin_rank: rank, updated_at: new Date().toISOString() }).eq("id", id);
      if (error) return json({ error: "Could not change administrator rank." }, 500);
      await audit(auth.admin, "admin.rank_change", "admin", id, { from: target.admin_rank, to: rank });
      return json({ success: true });
    }
    if (action === "password-change") {
      const auth = await session(req);
      if (!auth) return json({ error: "Authentication required." }, 401);
      const current = String(body.current_password || ""), next = String(body.new_password || "");
      if (next.length < 14 || next.length > 128 || next === current) return json({ error: "Choose a different password of at least 14 characters." }, 400);
      const { data: account } = await db.from("fiws_admin_accounts").select("password_hash").eq("id", auth.admin.id).single();
      if (!account || !await passwordOK(current, account.password_hash)) return json({ error: "Current password is incorrect." }, 401);
      await db.from("fiws_admin_accounts").update({ password_hash: await hashPassword(next), password_salt: "embedded-in-argon2id-hash", password_changed_at: new Date().toISOString() }).eq("id", auth.admin.id);
      await db.from("fiws_admin_sessions").update({ revoked_at: new Date().toISOString() }).eq("admin_id", auth.admin.id).neq("id", auth.row.id).is("revoked_at", null);
      await audit(auth.admin, "auth.password_changed", "admin", auth.admin.id);
      return json({ success: true, note: "Other sessions have been revoked." });
    }
    if (action === "admin-disable") {
      const auth = await session(req);
      if (!auth || auth.admin.admin_rank !== "owner") return json({ error: "Owner permission required." }, 403);
      const id = String(body.id || "");
      if (!id || id === auth.admin.id) return json({ error: "You cannot disable your own owner account." }, 400);
      const { data: target } = await db.from("fiws_admin_accounts").select("id,username,admin_rank").eq("id", id).maybeSingle();
      if (!target || target.admin_rank === "owner") return json({ error: "Owner account cannot be disabled here." }, 403);
      await db.from("fiws_admin_accounts").update({ disabled: body.disabled !== false, updated_at: new Date().toISOString() }).eq("id", id);
      if (body.disabled !== false) await db.from("fiws_admin_sessions").update({ revoked_at: new Date().toISOString() }).eq("admin_id", id).is("revoked_at", null);
      await audit(auth.admin, body.disabled === false ? "admin.enable" : "admin.disable", "admin", id);
      return json({ success: true });
    }
    if (action === "admin-reset-password") {
      const auth = await session(req);
      if (!auth || auth.admin.admin_rank !== "owner") return json({ error: "Owner permission required." }, 403);
      const id = String(body.id || ""), password = String(body.password || "");
      if (!id || id === auth.admin.id || password.length < 14 || password.length > 128) return json({ error: "Select another administrator and provide a 14+ character password." }, 400);
      const { data: target } = await db.from("fiws_admin_accounts").select("id,username,admin_rank").eq("id", id).maybeSingle();
      if (!target || target.admin_rank === "owner") return json({ error: "Owner password resets must use the account's recovery codes." }, 403);
      await db.from("fiws_admin_accounts").update({
        password_hash: await hashPassword(password), password_salt: "embedded-in-argon2id-hash",
        password_changed_at: new Date().toISOString(), totp_secret_ciphertext: null,
        totp_secret_iv: null, totp_enabled: false, totp_last_step: null, updated_at: new Date().toISOString(),
      }).eq("id", id);
      await db.from("fiws_admin_sessions").update({ revoked_at: new Date().toISOString() }).eq("admin_id", id).is("revoked_at", null);
      await db.from("fiws_admin_recovery_codes").delete().eq("admin_id", id);
      await audit(auth.admin, "admin.password_reset", "admin", id);
      return json({ success: true, note: "The administrator must enroll MFA again at next sign-in." });
    }
    if (action === "mfa-rotate-recovery") {
      const auth = await session(req);
      if (!auth) return json({ error: "Authentication required." }, 401);
      const { data: account, error: accountError } = await db.from("fiws_admin_accounts").select("totp_secret_ciphertext,totp_secret_iv").eq("id", auth.admin.id).single();
      if (accountError) throw accountError;
      if (!account?.totp_secret_ciphertext) return json({ error: "MFA is not configured." }, 409);
      const secret = await decryptSecret(account.totp_secret_ciphertext, account.totp_secret_iv);
      const matchedStep = await matchingTotpStep(secret, String(body.otp || ""));
      if (matchedStep === null) return json({ error: "Authenticator code is incorrect." }, 401);
      const codes = makeRecoveryCodes();
      const rows = await Promise.all(codes.map(async code => ({ code_hash: await sha(code) })));
      const { data: rotated, error: rotateError } = await db.rpc("fiws_rotate_admin_recovery_codes", {
        p_admin_id: auth.admin.id, p_matched_step: matchedStep, p_codes: rows,
      });
      if (rotateError) throw rotateError;
      if (!rotated) return json({ error: "That authenticator code has already been used." }, 409);
      return json({ success: true, recovery_codes: codes });
    }
    if (action === "applications-list") {
      const auth = await session(req);
      if (!auth || !allowedRank(auth.admin.admin_rank, "moderator")) return json({ error: "Insufficient permissions." }, 403);
      const { data, error } = await db.from("applications").select("id,reference_code,application_data,status,staff_note,created_at,decided_at").order("created_at", { ascending: false }).limit(500);
      if (error) return json({ error: "Could not load applications." }, 500);
      return json({ applications: data || [] });
    }
    if (action === "application-update") {
      const auth = await session(req);
      if (!auth || !allowedRank(auth.admin.admin_rank, "moderator")) return json({ error: "Insufficient permissions." }, 403);
      const id = String(body.id || ""), status = String(body.status || "");
      const note = String(body.staff_note || "");
      if (!id || !["pending", "accepted", "rejected"].includes(status) || note.length > 1000) return json({ error: "Invalid application update." }, 400);
      const { error } = await db.from("applications").update({
        status, staff_note: note || null, decided_at: status === "pending" ? null : new Date().toISOString(),
        decided_by: null,
      }).eq("id", id);
      if (error) return json({ error: "Could not update the application." }, 500);
      await audit(auth.admin, "application.update", "application", id, { status });
      return json({ success: true });
    }
    if (action === "application-delete") {
      const auth = await session(req);
      if (!auth || !allowedRank(auth.admin.admin_rank, "administrator")) return json({ error: "Administrator permission required." }, 403);
      const id = String(body.id || "");
      if (!id) return json({ error: "Application id is required." }, 400);
      const { error } = await db.from("applications").delete().eq("id", id);
      if (error) return json({ error: "Could not delete the application." }, 500);
      await audit(auth.admin, "application.delete", "application", id);
      return json({ success: true });
    }
    if (action === "setting-write") {
      const auth = await session(req);
      if (!auth || !allowedRank(auth.admin.admin_rank, "administrator")) return json({ error: "Administrator permission required." }, 403);
      const key = String(body.key || ""), value = body.value;
      if (!["workbook", "team_colors", "logos"].includes(key) || value === undefined) return json({ error: "This setting is not writable through the administrator API." }, 400);
      const { error } = await db.from("site_settings").upsert({
        setting_key: key, setting_value: value, updated_at: new Date().toISOString(), updated_by: null,
      }, { onConflict: "setting_key" });
      if (error) return json({ error: "Could not save the shared setting." }, 500);
      await audit(auth.admin, "setting.update", "setting", key);
      return json({ success: true });
    }
    if (action === "asset-upload") {
      const auth = await session(req);
      if (!auth || !allowedRank(auth.admin.admin_rank, "administrator")) return json({ error: "Administrator permission required." }, 403);
      const path = String(body.path || "");
      const mime = String(body.content_type || "");
      const allowed = path === "workbooks/current.xlsx" && mime === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        || /^logos\/(FIWS|FITC)\.png$/.test(path) && mime === "image/png";
      if (!allowed || typeof body.base64 !== "string" || body.base64.length > 8_000_000) return json({ error: "Invalid asset upload." }, 400);
      let bytes: Uint8Array;
      try { bytes = unb64(body.base64); } catch { return json({ error: "Invalid asset encoding." }, 400); }
      if (!bytes.length || bytes.length > 6_000_000) return json({ error: "Asset exceeds the 6 MB upload limit." }, 413);
      const { error } = await db.storage.from("fiws-public").upload(path, bytes, { upsert: true, contentType: mime });
      if (error) return json({ error: "Could not publish the asset." }, 500);
      await audit(auth.admin, "asset.upload", "asset", path, { bytes: bytes.length, content_type: mime });
      return json({ success: true, path });
    }
    if (action === "asset-delete") {
      const auth = await session(req);
      if (!auth || !allowedRank(auth.admin.admin_rank, "administrator")) return json({ error: "Administrator permission required." }, 403);
      const path = String(body.path || "");
      if (!/^logos\/(FIWS|FITC)\.png$/.test(path)) return json({ error: "Only a FIWS or FITC logo can be deleted here." }, 400);
      const { error } = await db.storage.from("fiws-public").remove([path]);
      if (error) return json({ error: "Could not remove the logo." }, 500);
      await audit(auth.admin, "asset.delete", "asset", path);
      return json({ success: true });
    }
    if (action.startsWith("logbook-")) return await logbookAction(action, req, body);
    return json({ error: "Unknown action." }, 400);
  } catch (error) {
    console.error("FIWS admin operation failed:", error instanceof Error ? error.message : "unknown");
    return json({ error: "The administrator operation could not be completed." }, 500);
  }
});
