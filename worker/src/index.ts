/* CogNebula KG API Proxy — CF Worker
   Bridges HTTPS (CF Pages frontend) → HTTP (VPS KG API).
   Deployed to: cognebula-kg-proxy.workers.dev */

const KG_API_ORIGIN = "http://167.86.74.172:8400";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

export default {
  async fetch(request: Request): Promise<Response> {
    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/" || url.pathname === "/health") {
      return Response.json({ ok: true, proxy: "cognebula-kg-proxy" }, { headers: CORS_HEADERS });
    }

    // Only proxy /api/v1/* paths
    if (!url.pathname.startsWith("/api/v1")) {
      return Response.json({ error: "Not found. Use /api/v1/*" }, { status: 404, headers: CORS_HEADERS });
    }

    try {
      const targetUrl = `${KG_API_ORIGIN}${url.pathname}${url.search}`;
      const fetchInit: RequestInit = {
        method: request.method,
        headers: { "Content-Type": "application/json" },
      };
      // Forward POST/PUT body
      if (request.method === "POST" || request.method === "PUT") {
        fetchInit.body = await request.text();
      }
      const response = await fetch(targetUrl, fetchInit);

      const body = await response.text();
      return new Response(body, {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
          ...CORS_HEADERS,
        },
      });
    } catch (err) {
      return Response.json(
        { error: "KG API unreachable", detail: String(err) },
        { status: 502, headers: CORS_HEADERS }
      );
    }
  },
};
