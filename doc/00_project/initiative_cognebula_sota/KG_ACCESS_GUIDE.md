# KG Access Guide — Local Dev → Production

> **Status**: live (2026-04-28). Replaces the previous local-sandbox-first dev model.
> **Trigger**: §19 atomic queue closeout. The `.demo` sandbox was deleted; production is now the only KG state of record.

---

## What changed

Before 2026-04-28, local dev work used a 109 MB KuzuDB sandbox at `data/finance-tax-graph.demo`. That sandbox diverged from production over months and ended up on a completely different timeline (audit Rev. 2 found 6,219 nodes in `.demo` vs **368,910 nodes** in production).

After 2026-04-28:

- The sandbox is deleted. Local dev no longer maintains a parallel KG.
- Production lives at `/home/kg/cognebula-enterprise/data/finance-tax-graph` on contabo (`100.88.170.57`), 102 GB.
- Local code reaches it via the Tailscale-routed REST API at `http://100.88.170.57:8400`.

---

## Three access modes (pick the right one)

### 1. REST API via Tailscale — default for local Python

Use `scripts/_lib/prod_kg_client.py`. This is the canonical access surface.

```python
from scripts._lib.prod_kg_client import health, stats, search, ontology_audit

print(health())
# {'status': 'healthy', 'kuzu': True, 'lancedb': True, 'lancedb_rows': 118011}

q = stats()
print(q['metrics']['total_nodes'])  # 368910
```

Override the base URL with the env var if you need to:

```bash
COGNEBULA_KG_URL=http://localhost:8400 python3 my_script.py   # if SSH-forwarded
```

**When to use**: any read-only query, audit script, dashboard fetch, hybrid search, ontology drift inspection. Latency is 0.5-5 sec per call (the `/quality` endpoint is heavy because it scans every table).

### 2. SSH probe — for one-off Cypher / introspection

For things the REST API doesn't expose (raw Cypher, file-system inspection, lsof of the running service):

```bash
ssh -o RemoteCommand=none -o RequestTTY=no contabo '
  python3 -c "
import kuzu
db = kuzu.Database(\"/home/kg/cognebula-enterprise/data/finance-tax-graph\", read_only=True)
conn = kuzu.Connection(db)
r = conn.execute(\"MATCH (n:KnowledgeUnit) RETURN count(n)\")
print(r.get_next()[0])
"'
```

The local `~/.ssh/config` entry for `contabo` forces `tmux` for interactive use. For non-interactive scripts always pass `-o RemoteCommand=none -o RequestTTY=no`.

**When to use**: ad-hoc Cypher queries, schema introspection, file-handle inspection, anything that needs Python `kuzu` library directly against the prod DB.

### 3. Offline fixture — for tests that must pass without network

For unit tests and CI runs that should not depend on the prod API being up:

```python
import pytest
@pytest.fixture
def mock_kg_response():
    return {"status": "healthy", "kuzu": True, "lancedb": True, "lancedb_rows": 118011}
```

For tests that need a real KuzuDB instance, seed a temporary Kuzu DB inside the
test fixture. Do not pin runtime code or Compose to local demo/archived KG
files. The old `data/finance-tax-graph.archived.157nodes` snapshot has been
removed from the working tree to prevent accidental runtime use.

**When to use**: pytest unit tests, CI matrix runs, anywhere the test must succeed in a network-isolated environment.

---

## Prerequisites

1. **Tailscale up.** Verify with `tailscale status` — the local mac should appear as `mauricemacbook-pro 100.113.180.44` and `kg-node-eu` should be reachable.
2. **No VPN that conflicts with Tailscale.** WireGuard, Clash split-tunnel, etc. can break the 100.x route to contabo.
3. **Service must be up.** Probe with `curl -sS --max-time 5 http://100.88.170.57:8400/api/v1/health`.

---

## Endpoint inventory (22 routes)

Read-only:
- `GET /api/v1/health` — liveness probe (cheap)
- `GET /api/v1/quality` — node/edge totals + per-type coverage + gate
- `GET /api/v1/stats` — *broken endpoint, returns malformed JSON* (use `/quality` instead)
- `GET /api/v1/ontology-audit` — schema-vs-live drift, brooks_ceiling, intersection
- `GET /api/v1/nodes?type=X&limit=N` — list nodes of a type
- `GET /api/v1/search?q=X&limit=N` — free-text
- `GET /api/v1/hybrid-search?q=X&limit=N` — vector + KG
- `GET /api/v1/graph?...` — graph traversal
- `GET /api/v1/constellation` / `GET /api/v1/constellation/type` — type browsing
- `GET /api/v1/debug/paths` — path resolution debug

Mutating (do NOT call from local dev):
- `POST /api/v1/admin/alter-table` / `enrich-edges` / `execute-ddl` / `fix-titles` / `migrate-table` / `reset-table` — production mutations
- `POST /api/v1/chat` — costs LLM tokens
- `POST /api/v1/ingest` — adds nodes

---

## Known issues

- **`/` returns a leaked local path**: `{"error":"Web UI not found at /Users/mauricewen/Projects/27-cognebula-enterprise/src/web/unified.html"}`. The deployed kg-api has Maurice's local mac path embedded in a config; harmless but ugly. Fix is on the deploy side, not the client side.
- **`/api/v1/stats` returns malformed JSON**: do not parse it. The healthy alternative is `/api/v1/quality`.
- **`/api/v1/.well-known/capabilities`**: the OPTIONS endpoint introduced in S15.1+S15.2+S18.26 is not yet deployed on contabo — that work is local. Will appear after next prod deploy.

---

## Migration notes for existing scripts

Scripts that previously defaulted `--db data/finance-tax-graph.demo` (e.g.
`scripts/migrate_phase1d_taxincentive_merge.py`, `scripts/check_ontology_conformance.py`)
are now broken by file deletion. Use the real KG instead:

1. Prefer the Tailscale REST surface through `scripts/_lib/prod_kg_client.py`.
2. For raw Cypher or file-level inspection, run on contabo against
   `/home/kg/cognebula-enterprise/data/finance-tax-graph`.
3. For CI/unit tests, create a temporary seeded Kuzu DB in the test itself.

---

Maurice | maurice_wen@proton.me
