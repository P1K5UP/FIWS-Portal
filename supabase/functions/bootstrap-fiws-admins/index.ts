import "jsr:@supabase/functions-js/edge-runtime.d.ts";

// Retired legacy FIWS administrator bootstrap endpoint.
// The custom fiws-admin authentication system is authoritative.
Deno.serve((_req: Request) => {
  return new Response(
    JSON.stringify({
      error: "This legacy administrator bootstrap endpoint has been retired.",
      code: "FUNCTION_RETIRED",
    }),
    {
      status: 410,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
      },
    },
  );
});
