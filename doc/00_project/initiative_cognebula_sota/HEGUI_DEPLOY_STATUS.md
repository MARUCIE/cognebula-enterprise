# hegui.io Frontend Deploy — Status & Runbook

> **2026-04-28** · CogNebula Enterprise web UI deploy to hegui.io
> Owner: Maurice · Author: session pickup from §20 KG audit closeout
> Scope: bring the React/Next.js KG explorer live at hegui.io

---

## What is live right now

| Layer | URL | State |
|---|---|---|
| Frontend (Next.js static) | `https://hegui-site.pages.dev` | LIVE — production deploy `875d3ff` |
| Frontend preview (per-deploy alias) | `https://5b934ed8.hegui-site.pages.dev` | LIVE — same artifact |
| API proxy (Pages Function) | `https://hegui-site.pages.dev/api/v1/*` | LIVE — returns real KG stats |
| API proxy (standalone Worker) | `https://cognebula-kg-proxy.maoyuan-wen-683.workers.dev/api/v1/*` | LIVE — alternate path |
| Tunnel (cloudflared on contabo) | `https://halifax-drop-college-oliver.trycloudflare.com` | LIVE — ephemeral hostname |
| KG API (uvicorn on contabo) | `localhost:8400` (private) | LIVE — 518,498 nodes / 1,293,535 edges |

**End-to-end sanity check (verified 2026-04-28T07:50Z)**:

```
$ curl https://hegui-site.pages.dev/api/v1/stats
{"total_nodes":518498,"total_edges":1293535,...}
```

---

## What is NOT achieved (Maurice-side actions required)

The original directive was "把原来这个页面下架，将知识图谱前端部署在这个域名下" —
take down the PPT gallery on `hegui.io` and serve the KG frontend there. The
frontend is built and deployed on this CF account, but the **`hegui.io` domain
itself is on a different CF account** that is not authenticated in the current
session.

### Diagnosis

- `dig hegui.io` resolves to CF anycast IPs via `kim.ns.cloudflare.com`
- API call `GET /zones?name=hegui.io` against the active token (account
  `683392e016d0a9c5446a8c648da62ce6` = `alphameta010@gmail.com-Account`)
  returns `{"result": []}` — **the zone is not on this account**
- The PPT gallery currently served at `hegui.io` is therefore on another
  CF account or another infrastructure that this session cannot reach
- Cached `wrangler/pages.json` pointing to `hegui-site` on this account
  was historical context, not a custom-domain binding

### Three paths Maurice can take

**A. CNAME from owning account (5 min, lowest disruption)**
1. Log into the CF account that owns `hegui.io` zone
2. Replace the A record(s) for `hegui.io` (and `www.hegui.io`) with a CNAME
   pointing to `hegui-site.pages.dev`
3. Keep proxy ON; CF Pages will detect the cross-account custom domain
4. PPT gallery automatically stops serving once DNS propagates
5. (Optional) confirm the custom domain in the Pages dashboard on this account
   so the cert is issued automatically

**B. Migrate the zone (clean long-term, ~1-2 h)**
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
