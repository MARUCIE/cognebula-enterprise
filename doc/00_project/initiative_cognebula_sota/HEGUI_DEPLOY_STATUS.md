# hegui.io Frontend Deploy — Status & Runbook

> **2026-04-28** · CogNebula Enterprise web UI deploy to hegui.io
> Owner: Maurice · Author: session pickup from §20 KG audit closeout
> Scope: bring the React/Next.js KG explorer live at hegui.io
> **STATUS: LIVE on hegui.io as of 2026-04-28T08:41Z**
>
> **Last audit-fix deploy**: 2026-04-28T10:33Z · preview alias `https://f976e5cc.hegui-site.pages.dev` · prod commit `5bc4df4` (3 audit-fix commits: `91cf66c` P0+P1.6+P3.10, `cdab111` P0.3+P1.5, `5bc4df4` non-audit feature work). Closes 6/11 items from `state/outputs/reports/pm-strategy-swarm/2026-04-28-hegui-expert-audit.md` (P0.1 6 status rows wired → /health · P0.2 READY pill tri-state · P0.3 100% replaced with composite-gate breakdown · P0.4 curl-discipline · P1.5 boundary 301s for 6 System B leak directories · P1.6 返回灵阙产品端 link removed · P3.10 quick cards deleted). Curl-verified: `/workbench/`→301→`/expert/bridge/`, `发布门` 6× present, `质量评分` 0×, `返回灵阙产品端` 0×, `PROBING/System A/Internal Console` all present. Deferred next sprint: P2.7 stats/quality drift rename, P2.8 知识问答 ↔ /reasoning, P3.11 架构说明 prose card.

---

## What is live right now

| Layer | URL | State |
|---|---|---|
| **Frontend on apex domain** | `https://hegui.io` | **LIVE — DNS swap completed 2026-04-28T08:40Z** |
| **Frontend on www subdomain** | `https://www.hegui.io` | **LIVE — same Pages project** |
| Frontend (Pages canonical) | `https://hegui-site.pages.dev` | LIVE — production deploy `875d3ff` |
| Frontend preview (per-deploy alias) | `https://5b934ed8.hegui-site.pages.dev` | LIVE — same artifact |
| API proxy (Pages Function) | `https://hegui.io/api/v1/*` | LIVE — returns real KG stats |
| API proxy (Pages canonical) | `https://hegui-site.pages.dev/api/v1/*` | LIVE — same Pages Function |
| API proxy (standalone Worker) | `https://cognebula-kg-proxy.maoyuan-wen-683.workers.dev/api/v1/*` | LIVE — alternate path |
| Tunnel (cloudflared on contabo) | `https://halifax-drop-college-oliver.trycloudflare.com` | LIVE — ephemeral hostname |
| KG API (uvicorn on contabo) | `localhost:8400` (private) | LIVE — 518,498 nodes / 1,293,535 edges |

**End-to-end sanity check (verified 2026-04-28T08:41Z, post-swap)**:

```
$ /usr/bin/curl -sS https://hegui.io | grep -oE '<title>[^<]+</title>'
<title>灵阙财税 | AI 虚拟财税公司</title>

$ /usr/bin/curl -sS https://hegui.io/api/v1/stats
{"total_nodes":518498,"total_edges":1293535,...}

$ dig @1.1.1.1 hegui.io +short
172.67.190.6
104.21.73.123

$ BASE=https://hegui.io bash scripts/smoke_test_hegui_deploy.sh
summary
  total:  16
  PASS:   13
  FAIL:   3   # all 3 = pre-existing contabo backend gaps (reasoning-chain, inspect/clause, inspect/clause/batch), NOT swap regressions
```

**Captures (4K + Mobile 3x DPI, 2026-04-28T08:43Z)**:
- `outputs/screenshots/hegui-io-pc-4k-2026-04-28T08-43.png` — 4320×2700, 738K
- `outputs/screenshots/hegui-io-mobile-4k-2026-04-28T08-43.png` — 1179×1980, 159K

---

## Default-route swap to /expert/ (2026-04-28T09:00Z)

**Trigger**: post-DNS-swap, the homepage at `hegui.io/` was rendering the
Lingque B2B SaaS landing (`/dashboard`, `/workbench`, `/clients`, `/reports`
routes), not the KG explorer + expert workbench. Maurice confirmed the wrong
default route — original directive was to surface KG/expert content.

**Discovery**: same Next.js bundle contains TWO products:
- Lingque B2B routes: `/`, `/dashboard`, `/workbench/*`, `/clients/*`, `/reports/*`
- CogNebula expert routes: `/expert/`, `/expert/kg`, `/expert/reasoning`,
  `/expert/data-quality`, `/expert/rules`, `/expert/bridge`

The deploy was correct; the IA was wrong. Fix is a single redirect, not a
rebuild of the wrong artifact.

**Fix applied**:

1. Created `web/public/_redirects` with `/  /expert/  302` (CF Pages native
   syntax; Next.js `redirects()` config doesn't work in `output: "export"` mode)
2. Rebuilt: `npm run build` → 39 static pages exported with `_redirects` copied to `out/_redirects`
3. Deployed: `wrangler pages deploy out --project-name=hegui-site` → preview alias `https://0f9c65e4.hegui-site.pages.dev`, production `hegui.io` updated within seconds

**Verification (2026-04-28T09:00Z)**:

```
$ /usr/bin/curl -sS -I https://hegui.io/ | head -5
HTTP/2 302
location: /expert/
server: cloudflare

$ /usr/bin/curl -sSL https://hegui.io/ | grep -E "(System A 总览|节点总数|KG 基础设施)" | wc -l
3   # all 3 expert markers present after follow-redirect

$ /usr/bin/curl -sS https://hegui.io/dashboard/ | grep -E "(月度仪表盘|服务客户)" | wc -l
2   # legacy lingque routes still accessible (no breakage)

$ playwright → final URL: https://hegui.io/expert/   # browser-level confirmation
```

**Captures (post-redirect, 2026-04-28T09:01Z)**:
- `outputs/screenshots/hegui-io-root-after-redirect-pc-4k-2026-04-28T09-01.png` — 4320×2700, 568K
- `outputs/screenshots/hegui-io-root-after-redirect-mobile-2026-04-28T09-01.png` — 575K

**Status note**: B2B routes (`/dashboard`, `/workbench/*`, etc) remain
accessible by URL but no longer have entry-link navigation from the new
`/expert/` homepage. If B2B content needs to be hidden from `hegui.io`
entirely, that's a separate IA decision (Option D in the route map): fork the
build to drop those routes. For now, redirect is sufficient.

---

## Upgrade to URL-stable rewrite (Option B, 2026-04-28T09:10Z)

Maurice picked Option B from the route-map: keep the homepage URL at `/`
(no visible `/expert/` in address bar), but render the expert dashboard there.

**Approach taken — minimalist**: instead of refactoring the app structure
with Next.js route groups (~30 min), changed the `_redirects` rule from
`302 redirect` to `200 rewrite`. CF Pages serves `/expert/index.html` content
when `/` is requested while preserving the URL bar.

**Diff applied**:

```diff
- /  /expert/  302
+ /  /expert/  200
```

**Why this works without refactor**: CF Pages `_redirects` accepts status `200`
as a server-side proxy directive (Netlify-compatible syntax). The browser
sees a single `HTTP/2 200` response; no redirect chain; URL bar stays at `/`.
Source code untouched, no route groups, no layout changes.

**Verification (2026-04-28T09:10Z)**:

```
$ /usr/bin/curl -sS -I https://hegui.io/ | head -2
HTTP/2 200                                 # NOT 302 — direct response
content-type: text/html; charset=utf-8

$ /usr/bin/curl -sS https://hegui.io/ | grep -E "(System A 总览|节点总数|KG 基础设施)" | wc -l
3                                          # all expert markers in body, no follow needed

$ playwright (real browser) → final URL = https://hegui.io/   # URL bar confirmed stable
```

**Captures (Option B verification, 2026-04-28T09:10Z)**:
- `outputs/screenshots/hegui-io-rewrite-200-pc-4k-2026-04-28T09-10.png` — 4320×2700, 579K
- `outputs/screenshots/hegui-io-rewrite-200-mobile-2026-04-28T09-10.png` — 459K

**Cosmetic follow-up (not blocking)**: the CogNebula sidebar in
`expert/layout.tsx` uses `href="/expert"` for the "总览" item. Clicking it from
`/` navigates to `/expert/` (URL bar changes from `/` to `/expert/`). If strict
URL/content coherence is desired, change that nav link to `href="/"`. Logged
as deferred work.

**Deploy alias**: `https://dc861b92.hegui-site.pages.dev`

---

## What was achieved this session — original directive resolved

The original directive was "把原来这个页面下架，将知识图谱前端部署在这个域名下" —
take down the PPT gallery on `hegui.io` and serve the KG frontend there.

**RESOLVED 2026-04-28T08:41Z**: Maurice executed the DNS swap manually in the
Cloudflare dashboard (deleted 4 A records, added 2 CNAMEs). Frontend went live
on `https://hegui.io` and `https://www.hegui.io` within 30 seconds of the
last DNS write. CF Pages auto-issued the TLS cert (Google Trust Services CA),
HTTP/3 + anycast routing both confirmed via `cf-ray: 9f34c42e0b5378ef-LAX`.

The smoke test (16 endpoints, 14 pulled from frontend's `kg-api.ts`) returned
13 PASS / 3 FAIL. All 3 failures are pre-existing contabo backend gaps
(`reasoning-chain`, `inspect/clause`, `inspect/clause/batch`) that the frontend
calls but kg-api-server.py never implemented; identical failure profile against
`hegui-site.pages.dev` confirms these are not introduced by today's swap.

### Historical CORRECTED diagnosis (2026-04-28T08:01Z, kept for record)

A previous version of this doc claimed `hegui.io` zone was on a different CF
account. **That was wrong.** The earlier `zones?name=hegui.io` API call returned
empty because it was made with `CLOUDFLARE_API_TOKEN` (a custom token without
`Zone:Read` scope). When re-issued with the OAuth token (which has `zone:read`),
the same call returns the zone:

```json
{"id":"0f9ab49d3f3bab8e31609afdca6de1f1","name":"hegui.io","status":"active",
 "account":{"id":"683392e016d0a9c5446a8c648da62ce6",
            "name":"alphameta010@gmail.com-Account"}}
```

**The zone is on this account.** The earlier verdict was a token-scope-disguise
failure — same family as the memorized "Wrangler OAuth env var precedence trap"
(custom token shadows OAuth for curl, but wrangler's own calls refresh OAuth
internally; when only one of them works, the wrong inference is "permission
denied = resource doesn't exist" rather than "permission denied = wrong token").

### What is now done (autonomously)

- Custom domain `hegui.io` attached to Pages project `hegui-site` (status:
  `initializing`, awaiting DNS verification)
- Custom domain `www.hegui.io` attached to `hegui-site` (same status)
- Both wait on a single signal: a CNAME record pointing to `hegui-site.pages.dev`

### What is still blocked

The current OAuth token has `zone:read` but not `dns_records:edit`. DNS write
returns `code: 10000 Authentication error`. So the four DNS-record edits
required to flip `hegui.io` from PPT gallery to KG frontend cannot be done
from this session.

### Maurice action — 4 clicks, ~1 min

Open Cloudflare dashboard → `hegui.io` zone → DNS → Records:

1. **Delete** the A record `@ → 104.21.73.123` (and the second A record `@ → 172.67.190.6`)
2. **Add** CNAME `@ → hegui-site.pages.dev` (proxied = ON, orange cloud)
3. **Delete** the A records for `www`
4. **Add** CNAME `www → hegui-site.pages.dev` (proxied = ON)

Within ~30 seconds of step 4, CF Pages auto-issues a cert (Google CA, already
configured) and `hegui.io` starts serving the KG frontend. PPT gallery stops
serving automatically because the DNS no longer points to its upstream.

To verify after the swap:

```
$ curl -sS https://hegui.io | grep -oE '<title>[^<]+</title>'
<title>灵阙财税 | AI 虚拟财税公司</title>     # KG frontend served
$ curl -sS https://hegui.io/api/v1/stats
{"total_nodes":518498,"total_edges":1293535,...}     # API chain still works
```

Or run the smoke test:

```
$ BASE=https://hegui.io bash scripts/smoke_test_hegui_deploy.sh
```

### Alternative — give the agent DNS edit access

If Maurice prefers not to click in the dashboard, options:

1. Create a CF API token with **Zone DNS:Edit** for `hegui.io`, set as
   `CLOUDFLARE_API_TOKEN`, and the agent can finish DNS in 30 seconds
2. Run `wrangler login` interactively in the browser — the OAuth flow can
   be set to include DNS scope, and the agent can finish from the new token

### Where the PPT page actually comes from

(Answers Maurice's question "怎么没部署到 hegui.io" implicitly: the deploy
went to the right Pages project, but the DNS records on `hegui.io` zone were
never updated to point to that project. The current A records target some
other CF infrastructure — possibly an older Pages project that has been
deleted but whose anycast routing is still cached, or a Workers for Platforms
hostname that doesn't show up in the standard project/worker enumeration.
Without DNS-records read access, the exact upstream cannot be identified
from this session, but the fix is the same regardless: replace the A
records with the CNAME above.)

### Three paths Maurice can take (legacy section, kept for context)

**A. CNAME from owning account (5 min, lowest disruption)**
1. Log into the CF account that owns `hegui.io` zone
2. Replace the A record(s) for `hegui.io` (and `www.hegui.io`) with a CNAME
   pointing to `hegui-site.pages.dev`
3. Keep proxy ON; CF Pages will detect the cross-account custom domain
4. PPT gallery automatically stops serving once DNS propagates
5. (Optional) confirm the custom domain in the Pages dashboard on this account
   so the cert is issued automatically

**B. Migrate the zone (clean long-term, ~1-2 h)** — *(no longer needed since
the zone IS on this account; kept for historical reference)*
1. Change `hegui.io` registrar nameservers from current account's CF NS to the
   alphameta010 account's CF NS pair
2. Re-import the DNS records on the alphameta010 account
3. Add `hegui.io` as Pages custom domain to project `hegui-site` via dashboard
4. Single-account ownership, no cross-account fragility

**C. Hand off CF credentials for the owning account**
1. Provide a CF API token with `Zone:Edit` + `Pages:Edit` for the owning account
2. Or do `wrangler logout && wrangler login` from a clean shell pointing
   to the owning account, then `wrangler pages domain add hegui.io
   --project-name=<owning-project>` (or replicate the deploy on that account)

Recommendation: **A** is the fastest, no-regret path. **B** if Maurice wants
single-account simplicity. **C** if Maurice prefers to hand the keys.

---

## Architecture as deployed

```
hegui-site.pages.dev   ←──── (custom domain hegui.io will plug in here once DNS swaps)
       │
       ├─ static assets         (Next.js out/, 389 files, 5.8 MB)
       └─ /api/v1/*  ───────┐
                            │
                            ▼
              CF Pages Function ([[path]].ts)
                            │
                            ▼
              fetch(KG_API_ORIGIN + path)
                            │
                            ▼
       cloudflared quick-tunnel HTTPS
                            │
                            ▼
              contabo localhost:8400 (uvicorn)
                            │
                            ▼
              KG REST API (kg-api-server.py)
```

**Why the tunnel layer exists**: CF Workers/Pages Functions block `fetch()` to
bare IPs (returns "error code: 1003"). Validated empirically:
`fetch("http://167.86.74.172:8400/...")` from worker → 1003;
`fetch("https://*.trycloudflare.com/...")` from worker → real data.

---

## Quick tunnel fragility (pending: graduate to named tunnel)

The current tunnel is a `cloudflared tunnel --url http://localhost:8400`
quick tunnel. Properties:

- URL is **stable for the lifetime of the cloudflared process**
- Survives transient failures via systemd `Restart=on-failure`
- Does **not** survive process kill, manual restart, or reboot — each
  cloudflared invocation gets a new random `*.trycloudflare.com` URL
- Boot persistence is partial: systemd will start cloudflared on reboot but
  the URL will differ from the one currently hardcoded in
  `web/functions/api/v1/[[path]].ts:DEFAULT_KG_API_ORIGIN` and
  `worker/wrangler.toml:KG_API_ORIGIN`

**Runbook — if the tunnel URL rotates**:

1. SSH to contabo: `ssh contabo` (alias in `~/.ssh/config`)
2. Bypass the tmux RemoteCommand: `ssh -o RemoteCommand=none -o RequestTTY=no
   -i ~/.ssh/id_ed25519_vps root@100.88.170.57 "grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /var/log/cloudflared-kg.log | tail -1"`
3. Update `web/functions/api/v1/[[path]].ts:DEFAULT_KG_API_ORIGIN` to the new URL
4. Update `worker/wrangler.toml:KG_API_ORIGIN` to the new URL
5. Rebuild + redeploy:
   - `cd web && npm run build && env -i HOME=$HOME PATH=$PATH wrangler pages deploy out --project-name=hegui-site --commit-dirty=true`
   - `cd worker && env -i HOME=$HOME PATH=$PATH wrangler deploy`

**Recommendation**: graduate to a named tunnel. Steps:

1. On contabo: `cloudflared tunnel login` (opens browser link → Maurice
   authenticates the CF account that should own the tunnel)
2. `cloudflared tunnel create cognebula-kg`
3. `cloudflared tunnel route dns cognebula-kg kg-api.<some-domain>`
4. Replace systemd unit's `ExecStart` with
   `cloudflared tunnel run cognebula-kg`
5. Update the two `KG_API_ORIGIN` references to the stable hostname
6. Redeploy

---

## Local files of record (after this session)

```
27-cognebula-enterprise/
├── web/
│   ├── functions/api/v1/[[path]].ts    NEW — Pages Function proxy
│   ├── tsconfig.json                   MOD — exclude functions/ from Next compile
│   └── out/                            BUILT — static export (gitignored)
├── worker/
│   ├── src/index.ts                    UNCHANGED — original worker source
│   └── wrangler.toml                   MOD — KG_API_ORIGIN → tunnel URL
└── doc/00_project/initiative_cognebula_sota/
    └── HEGUI_DEPLOY_STATUS.md          NEW — this file
```

Contabo state added this session:
- `/usr/local/bin/cloudflared` (binary, version 2026.3.0)
- `/etc/systemd/system/cloudflared-kg-quick.service` (systemd unit, enabled)
- `/var/log/cloudflared-kg.log` (tunnel logs)
- One running `cloudflared` process (PID `2101535` at install time)

Commit: `875d3ff` on branch `main`.

---

## Honest framing

This session shipped the **build pipeline + deploy pipeline + API chain** for
the CogNebula web UI. It did **not** ship "KG frontend on hegui.io" because
the domain itself is not on the active CF account. The PPT gallery still
serves at hegui.io — unchanged.

The remaining work is a single Maurice-side action (DNS swap, zone migration,
or credential hand-off) plus an optional graduation from quick → named tunnel
for stability.

---

Maurice | maurice_wen@proton.me
