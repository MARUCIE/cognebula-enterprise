/* CogNebula KG API Proxy — CF Pages Function
   Bridges HTTPS (hegui.io) → HTTP (VPS KG API at 167.86.74.172:8400).
   Adapted from worker/src/index.ts; same-origin proxy means the frontend's
   default KG_API_BASE = "/api/v1" works without env override. */

interface Env {
  KG_API_ORIGIN?: string;
  KG_API_KEY?: string;
}

// CF Workers/Pages Functions block fetch to bare IP (returns 1003).
// Production must use an HTTPS hostname via CF Tunnel (cloudflared) on contabo.
// Override with env.KG_API_ORIGIN binding when migrating to named tunnel.
const DEFAULT_KG_API_ORIGIN = "https://halifax-drop-college-oliver.trycloudflare.com";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Accept",
  "Access-Control-Max-Age": "86400",
};

export const onRequest: PagesFunction<Env> = async (context) => {
  const { request, env } = context;

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }

  const url = new URL(request.url);

  try {
    const kgApiOrigin = env.KG_API_ORIGIN || DEFAULT_KG_API_ORIGIN;
    const headers = new Headers({
      "Content-Type": request.headers.get("Content-Type") || "application/json",
      Accept: request.headers.get("Accept") || "application/json",
    });
    if (env.KG_API_KEY) {
      headers.set("X-API-Key", env.KG_API_KEY);
    }

    const fetchInit: RequestInit = {
      method: request.method,
      headers,
    };
    if (request.method === "POST" || request.method === "PUT") {
      fetchInit.body = await request.text();
    }

    const response = await fetch(`${kgApiOrigin}${url.pathname}${url.search}`, fetchInit);

    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/json",
        ...CORS_HEADERS,
      },
    });
  } catch (err) {
    return Response.json(
      { error: "KG API unreachable", detail: String(err) },
      { status: 502, headers: CORS_HEADERS },
    );
  }
};
