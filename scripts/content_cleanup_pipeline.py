#!/usr/bin/env python3
"""Content Cleanup Pipeline — AI-powered junk detection + replacement.

Three-pronged attack:
1. LawOrRegulation: detect junk → re-fetch via fleet-page-fetch → clear unfixable
2. LegalDocument: detect field-assembly → Gemini enhance (structured type, AI allowed)
3. KnowledgeUnit: already handled by ku_content_backfill.py (batch-size=15 fix)

Run on kg-node:
    sudo systemctl stop kg-api
    /home/kg/kg-env/bin/python3 scripts/content_cleanup_pipeline.py --phase lr [--dry-run]
    /home/kg/kg-env/bin/python3 scripts/content_cleanup_pipeline.py --phase ld [--dry-run]
    sudo systemctl start kg-api

Integrates with M3 orchestrator as optional Step 2c.
"""
import kuzu
import json
import os
import sys
import time
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, os.path.dirname(__file__))
from content_validator import is_junk, is_llm_generated

DB_PATH = "/home/kg/cognebula-enterprise/data/finance-tax-graph"
FLEET_URL = "http://100.106.223.39:19801/fetch"
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

CHECKPOINT_INTERVAL = 500  # Reconnect DB every N writes (KuzuDB WAL limit)
RATE_LIMIT = 3  # seconds between fleet/Gemini calls


def _get_api_key():
    """Load Gemini API key from .env."""
    for p in ["/home/kg/cognebula-enterprise/.env", ".env"]:
        if os.path.exists(p):
            for line in open(p):
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("GEMINI_API_KEY", "")


def _fleet_fetch(url, timeout=25000):
    """Fetch URL via fleet-page-fetch browser renderer."""
    body = json.dumps({
        "url": url,
        "timeout": timeout,
        "waitUntil": "domcontentloaded",
    }).encode()
    try:
        req = Request(FLEET_URL, data=body,
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=35) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return data.get("content", "") or data.get("text", "") or ""
    except Exception:
        pass
    return ""


def _call_gemini(prompt, api_key, model=GEMINI_MODEL):
    """Call Gemini API and return response text."""
    url = GEMINI_URL.format(model=model)
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096},
    }).encode()
    for attempt in range(3):
        try:
            req = Request(f"{url}?key={api_key}", data=body,
                          headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt + 1)
                continue
            return ""
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return ""
    return ""


def _reconnect_db():
    """Create fresh KuzuDB connection (WAL buffer management)."""
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)
    return db, conn


def _extract_json_content(text):
    """Extract real content from JSON object stored in fullText (legacy artifact).

    Some LR entries have fullText like '{"title":"xxx","content":"real text",...}'.
    Extract the longest text field as the real content.
    """
    try:
        obj = json.loads(text)
        if not isinstance(obj, dict):
            return ""
        # Try common content field names
        for key in ["content", "fullText", "text", "body", "detail", "summary"]:
            val = obj.get(key, "")
            if isinstance(val, str) and len(val) > 50:
                return val
        # Fallback: find longest string value
        best = ""
        for v in obj.values():
            if isinstance(v, str) and len(v) > len(best):
                best = v
        return best if len(best) > 50 else ""
    except (json.JSONDecodeError, TypeError):
        return ""


# ── Phase 1: LawOrRegulation Junk Cleanup ────────────────────────────

def cleanup_lr(dry_run=False, max_items=10000):
    """Detect and clean junk LawOrRegulation content.

    Strategy:
    1. Query all LR with fullText
    2. Run is_junk() on each
    3. For junk entries: try fleet re-fetch from sourceUrl
    4. If re-fetch returns real content → update
    5. If re-fetch fails/junk → clear fullText (keep metadata)
    """
    print("=" * 60)
    print("Phase 1: LawOrRegulation Junk Cleanup")
    print("=" * 60)

    db, conn = _reconnect_db()

    # Count junk
    r = conn.execute(
        "MATCH (lr:LawOrRegulation) "
        "WHERE lr.fullText IS NOT NULL AND size(lr.fullText) > 20 "
        "RETURN lr.id, lr.fullText, lr.sourceUrl, lr.title "
        f"LIMIT {max_items}"
    )

    junk_entries = []
    clean_count = 0
    while r.has_next():
        row = r.get_next()
        lid, ft, url, title = str(row[0]), str(row[1] or ""), str(row[2] or ""), str(row[3] or "")
        j, reason = is_junk(ft)
        if j:
            junk_entries.append((lid, ft, url, title, reason))
        else:
            clean_count += 1

    print(f"\n  Scanned: {clean_count + len(junk_entries)}")
    print(f"  Clean: {clean_count}")
    print(f"  Junk: {len(junk_entries)}")

    if not junk_entries:
        print("  No junk found. Done.")
        del conn; del db
        return

    # Categorize junk by type
    json_junk = [(l, f, u, t, r) for l, f, u, t, r in junk_entries if r == "json_object_in_text"]
    with_url = [(l, f, u, t, r) for l, f, u, t, r in junk_entries if len(u) > 10 and r != "json_object_in_text"]
    no_url = [(l, f, u, t, r) for l, f, u, t, r in junk_entries if len(u) <= 10 and r != "json_object_in_text"]
    print(f"  JSON objects: {len(json_junk)} (will extract real content)")
    print(f"  Junk with URL: {len(with_url)} (chinatax, will clear — fleet blocked)")
    print(f"  Junk no URL: {len(no_url)} (will clear fullText)")

    if dry_run:
        print("\n  [DRY RUN] Would process:")
        print(f"    JSON extract: {len(json_junk)}")
        print(f"    Clear (chinatax junk): {len(with_url)}")
        print(f"    Clear (no URL): {len(no_url)}")
        for lid, _, url, title, reason in junk_entries[:5]:
            print(f"    Sample: {lid} | {reason} | {title[:40]}")
        del conn; del db
        return

    # Process junk entries
    updated = 0
    cleared = 0
    json_extracted = 0
    failed = 0
    write_count = 0

    # Step A: Extract real content from JSON objects
    for lid, ft, _, title, reason in json_junk:
        extracted = _extract_json_content(ft)
        if extracted:
            j, _ = is_junk(extracted)
            if not j:
                safe = extracted.replace("'", "''")[:10000]
                try:
                    conn.execute(
                        f"MATCH (lr:LawOrRegulation) WHERE lr.id = '{lid}' "
                        f"SET lr.fullText = '{safe}', "
                        f"lr.contentStatus = 'json_extracted'"
                    )
                    json_extracted += 1
                    write_count += 1
                except Exception:
                    failed += 1
            else:
                # Extracted content is also junk
                try:
                    conn.execute(
                        f"MATCH (lr:LawOrRegulation) WHERE lr.id = '{lid}' "
                        f"SET lr.fullText = '', lr.contentStatus = 'junk_cleared'"
                    )
                    cleared += 1
                    write_count += 1
                except Exception:
                    failed += 1
        else:
            try:
                conn.execute(
                    f"MATCH (lr:LawOrRegulation) WHERE lr.id = '{lid}' "
                    f"SET lr.fullText = '', lr.contentStatus = 'junk_cleared'"
                )
                cleared += 1
                write_count += 1
            except Exception:
                failed += 1

        if write_count % CHECKPOINT_INTERVAL == 0 and write_count > 0:
            del conn; del db
            db, conn = _reconnect_db()
            print(f"    Checkpoint at {write_count} writes")

    print(f"  Step A done: {json_extracted} JSON extracted, {cleared} cleared")

    # Step B: Clear junk without URLs
    for lid, _, _, title, reason in no_url:
        try:
            conn.execute(
                f"MATCH (lr:LawOrRegulation) WHERE lr.id = '{lid}' "
                f"SET lr.fullText = '', lr.contentStatus = 'junk_cleared'"
            )
            cleared += 1
            write_count += 1
            if write_count % CHECKPOINT_INTERVAL == 0:
                del conn; del db
                db, conn = _reconnect_db()
                print(f"    Checkpoint at {write_count} writes")
        except Exception as e:
            failed += 1

    # Step C: Clear chinatax junk (fleet-page-fetch blocked by anti-bot)
    # These are all chinatax.gov.cn URLs whose content is nav/boilerplate HTML.
    # fleet returns IE compatibility warning, not real content. Clear and mark.
    for lid, _, url, title, reason in with_url:
        try:
            conn.execute(
                f"MATCH (lr:LawOrRegulation) WHERE lr.id = '{lid}' "
                f"SET lr.fullText = '', lr.contentStatus = 'source_blocked'"
            )
            cleared += 1
            write_count += 1
        except Exception:
            failed += 1

        if write_count % CHECKPOINT_INTERVAL == 0 and write_count > 0:
            del conn; del db
            db, conn = _reconnect_db()
            print(f"    Checkpoint at {write_count} writes")

        if cleared % 1000 == 0 and cleared > 0:
            print(f"    Progress: {json_extracted} extracted, {cleared} cleared, {failed} failed")

    print(f"\n  DONE: {json_extracted} JSON extracted, {cleared} cleared (junk removed), {failed} failed")
    del conn; del db


# ── Phase 2: LegalDocument Content Enhancement ──────────────────────

def cleanup_ld(dry_run=False, max_items=5000):
    """Enhance LegalDocument descriptions using Gemini.

    LegalDocument is NOT authoritative — it's structured/ai_expandable.
    Current descriptions are field assemblies like "法规名 + 类型 + 发布机构".
    Gemini can generate useful summaries from the metadata.
    """
    print("=" * 60)
    print("Phase 2: LegalDocument Content Enhancement")
    print("=" * 60)

    api_key = _get_api_key()
    if not api_key and not dry_run:
        print("  ERROR: GEMINI_API_KEY not set")
        return

    db, conn = _reconnect_db()

    # Pre-check: LegalDocument table must exist
    try:
        conn.execute("MATCH (d:LegalDocument) RETURN count(d) LIMIT 1")
    except Exception:
        print("  SKIP: LegalDocument table does not exist")
        return

    # Find LD with short descriptions (field assembly)
    r = conn.execute(
        "MATCH (ld:LegalDocument) "
        "WHERE ld.description IS NOT NULL AND size(ld.description) >= 10 "
        "AND size(ld.description) < 200 "
        "RETURN ld.id, ld.name, ld.description, ld.documentType "
        f"LIMIT {max_items}"
    )

    candidates = []
    while r.has_next():
        row = r.get_next()
        candidates.append({
            "id": str(row[0] or ""),
            "name": str(row[1] or ""),
            "desc": str(row[2] or ""),
            "type": str(row[3] or ""),
        })

    print(f"\n  Short descriptions (< 200 chars): {len(candidates)}")

    if not candidates:
        print("  No candidates. Done.")
        del conn; del db
        return

    if dry_run:
        print(f"\n  [DRY RUN] Would enhance {len(candidates)} LegalDocuments via Gemini")
        for c in candidates[:3]:
            print(f"    {c['id']}: {c['name'][:50]} ({len(c['desc'])} chars)")
        del conn; del db
        return

    # Batch enhance via Gemini
    enhanced = 0
    failed = 0
    write_count = 0
    BATCH = 10

    ld_start = time.time()
    LD_TIMEOUT = 1800  # 30 min max for entire LD phase

    for i in range(0, len(candidates), BATCH):
        if time.time() - ld_start > LD_TIMEOUT:
            print(f"\n  TIMEOUT: LD phase exceeded {LD_TIMEOUT}s, stopping")
            break
        batch = candidates[i:i + BATCH]
        items_text = "\n".join(
            f"- ID:{c['id']} | 名称:{c['name']} | 类型:{c['type']} | 现有描述:{c['desc']}"
            for c in batch
        )

        prompt = (
            "你是中国财税法规专家。以下是一批法律文档的元数据。"
            "请为每个文档生成一段简洁的中文描述（50-150字），说明该文档的"
            "主要内容、适用范围和实务意义。\n\n"
            f"{items_text}\n\n"
            "输出JSON数组，格式: [{\"id\": \"...\", \"description\": \"...\"}]\n"
            "只输出JSON，不要其他文字。"
        )

        response = _call_gemini(prompt, api_key)
        time.sleep(RATE_LIMIT)

        if not response:
            failed += len(batch)
            continue

        # Parse response
        try:
            # Strip markdown wrapper
            import re
            m = re.search(r'```(?:json)?\s*\n?(.*?)```', response, re.DOTALL)
            raw = m.group(1).strip() if m else response.strip()
            results = json.loads(raw)
        except Exception:
            failed += len(batch)
            continue

        for item in results:
            rid = item.get("id", "")
            desc = item.get("description", "")
            if not rid or not desc or len(desc) < 30:
                failed += 1
                continue
            safe_desc = desc.replace("'", "''")[:500]
            try:
                conn.execute(
                    f"MATCH (ld:LegalDocument) WHERE ld.id = '{rid}' "
                    f"SET ld.description = '{safe_desc}', "
                    f"ld.contentStatus = 'ai_enhanced'"
                )
                enhanced += 1
                write_count += 1
            except Exception:
                failed += 1

            if write_count % CHECKPOINT_INTERVAL == 0:
                del conn; del db
                db, conn = _reconnect_db()
                print(f"    Checkpoint at {write_count} writes")

        if (i // BATCH) % 10 == 0:
            print(f"    Batch {i // BATCH}: {enhanced} enhanced, {failed} failed")

    print(f"\n  DONE: {enhanced} enhanced, {failed} failed")
    del conn; del db


# ── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Content Cleanup Pipeline")
    parser.add_argument("--phase", choices=["lr", "ld", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-items", type=int, default=10000)
    args = parser.parse_args()

    print(f"\nContent Cleanup Pipeline — {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Phase: {args.phase} | Dry-run: {args.dry_run} | Max: {args.max_items}\n")

    if args.phase in ("lr", "all"):
        cleanup_lr(dry_run=args.dry_run, max_items=args.max_items)

    if args.phase in ("ld", "all"):
        cleanup_ld(dry_run=args.dry_run, max_items=args.max_items)

    print(f"\nPipeline complete — {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")


if __name__ == "__main__":
    main()
