import { withSupabase } from "npm:@supabase/server";

const SITE_ORIGIN = "https://p1k5up.github.io";
const corsHeaders = {
  "Access-Control-Allow-Origin": SITE_ORIGIN,
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Vary": "Origin",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

const authenticatedHandler = withSupabase({ auth: "user" }, async (req, ctx) => {
  try {
    const { data: { user }, error: userError } = await ctx.supabase.auth.getUser();
    if (userError || !user || !user.email_confirmed_at) return json({ error: "Verify your email before submitting." }, 401);

    const contentLength = Number(req.headers.get("content-length") || "0");
    if (contentLength > 30000) return json({ error: "Application payload is too large." }, 413);

    const body = await req.json();
    const applicantId = body?.applicant_id;
    const referenceCode = body?.reference_code;
    const applicationData = body?.application_data;

    if (applicantId !== user.id) return json({ error: "Invalid applicant identity." }, 403);
    if (typeof referenceCode !== "string" || !/^FIWS-[A-Z0-9]{8}$/.test(referenceCode)) return json({ error: "Invalid application reference." }, 400);
    if (!applicationData || typeof applicationData !== "object" || Array.isArray(applicationData)) return json({ error: "Invalid application details." }, 400);
    if (new TextEncoder().encode(JSON.stringify(applicationData)).length > 20000) return json({ error: "Application payload is too large." }, 413);
    if (!["Driver", "Steward"].includes(applicationData.type)) return json({ error: "Invalid application type." }, 400);
    if (String(applicationData.email || "").toLowerCase() !== String(user.email || "").toLowerCase()) return json({ error: "Application email must match your verified account." }, 403);

    const ip = (req.headers.get("cf-connecting-ip") || req.headers.get("x-real-ip") || req.headers.get("x-forwarded-for")?.split(",").map((part) => part.trim()).filter(Boolean).at(-1) || "").trim();
    if (!ip) return json({ error: "Unable to verify request origin. Please try again." }, 400);

    const secretKeys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}");
    const pepper = secretKeys.default;
    if (!pepper) throw new Error("Server rate-limit key is not configured.");
    const hmacKey = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(pepper),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    );
    const digest = await crypto.subtle.sign("HMAC", hmacKey, new TextEncoder().encode(ip));
    const ipHash = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");

    const { data: allowed, error: rateError } = await ctx.supabaseAdmin.rpc(
      "consume_fiws_ip_limit",
      { p_ip_hash: ipHash },
    );
    if (rateError) throw rateError;
    if (allowed !== true) return json({ error: "Too many applications from this network. Please try again later." }, 429);

    const { data, error } = await ctx.supabase
      .from("applications")
      .insert({
        applicant_id: user.id,
        reference_code: referenceCode,
        application_data: applicationData,
      })
      .select("id, reference_code")
      .single();

    if (error) {
      if (error.code === "23505") return json({ error: "You already have a pending application of this type, or this reference code was already used." }, 409);
      if (error.code === "P0001") return json({ error: "Your account has reached the application submission limit. Please try again later." }, 429);
      console.error("FIWS application insert failed:", error.code || "unknown");
      return json({ error: "Your application could not be submitted. Please try again." }, 400);
    }
    return json({ id: data.id, reference_code: data.reference_code }, 201);
  } catch (error) {
    console.error("FIWS submit-application failed:", error instanceof Error ? error.message : "unknown");
    return json({ error: "A server error prevented submission. Please try again." }, 500);
  }
});

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    const origin = req.headers.get("origin");
    if (origin !== SITE_ORIGIN) return new Response("Forbidden", { status: 403 });
    return new Response("ok", { headers: corsHeaders });
  }
  if (req.method !== "POST") return json({ error: "Method not allowed." }, 405);
  if (req.headers.get("origin") !== SITE_ORIGIN) return json({ error: "Origin not allowed." }, 403);
  return await authenticatedHandler(req);
});
