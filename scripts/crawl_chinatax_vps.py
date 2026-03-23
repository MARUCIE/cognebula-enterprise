"""Crawl 936 chinatax URLs via fleet-page-fetch on VPS."""
import hashlib, json, logging, os, re, time, random
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("ct_crawl")

DATA_DIR = "/home/kg/cognebula-enterprise/data"
OUTPUT_JSONL = os.path.join(DATA_DIR, "recrawl", "chinatax_fulltext.jsonl")
FETCH_URL = "http://100.106.223.39:19801/fetch"
DELAY_MIN = 5
DELAY_MAX = 10


def load_urls_needing_content():
    urls = {}
    for fpath in [
        os.path.join(DATA_DIR, "raw/chinatax-full/chinatax_api.json"),
        os.path.join(DATA_DIR, "raw/20260315-fgk-deep/chinatax_api.json"),
        os.path.join(DATA_DIR, "raw/2026-03-15-fgk-extra/chinatax_api.json"),
    ]:
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            data = json.load(f)
        for item in data:
            url = item.get("url", "")
            title = item.get("title", "")
            content = item.get("content", "")
            if url and title and len(content) < 100:
                if url not in urls:
                    urls[url] = {"title": title, "id": item.get("id", "")}
    return urls


def fetch_via_fleet(url):
    """Fetch URL via fleet-page-fetch local endpoint."""
    try:
        req_data = json.dumps({"url": url}).encode()
        req = urllib.request.Request(
            FETCH_URL, data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            result = json.loads(resp.read())
            markdown = result.get("markdown", "") or result.get("content", "") or result.get("text", "")
            # Clean
            markdown = re.sub(r'!\[.*?\]\(.*?\)', '', markdown)
            markdown = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', markdown)
            markdown = re.sub(r'#{1,6}\s*', '', markdown)
            markdown = re.sub(r'\*{1,3}', '', markdown)
            markdown = re.sub(r'\n{3,}', '\n\n', markdown)
            return markdown.strip()
    except Exception as e:
        log.warning("  fetch error: %s", str(e)[:80])
    return ""


def main():
    # Check fleet-page-fetch is running
    try:
        req = urllib.request.Request("http://100.106.223.39:19801/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read())
            if not health.get("ok"):
                log.error("fleet-page-fetch not healthy")
                return
    except:
        log.error("fleet-page-fetch not reachable on localhost:19801")
        return

    urls = load_urls_needing_content()
    log.info("URLs needing content: %d", len(urls))

    # Load existing results
    existing = set()
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL) as f:
            for line in f:
                try:
                    item = json.loads(line)
                    existing.add(item.get("url", ""))
                except:
                    pass
    log.info("Already crawled: %d", len(existing))

    todo = {u: v for u, v in urls.items() if u not in existing}
    log.info("Remaining: %d", len(todo))

    out_f = open(OUTPUT_JSONL, "a", buffering=1)  # Line-buffered
    fetched = 0
    good = 0

    for i, (url, meta) in enumerate(todo.items()):
        title = meta["title"]
        content = fetch_via_fleet(url)

        if len(content) >= 100:
            item = {
                "id": meta["id"] or hashlib.sha256(url.encode()).hexdigest()[:16],
                "title": title,
                "content": content[:5000],
                "url": url,
                "source": "chinatax_fulltext",
            }
            line = json.dumps(item, ensure_ascii=False) + "\n"
            out_f.write(line)
            out_f.flush()
            good += 1
            log.info("  [%d/%d] OK %s (%dc)", i+1, len(todo), title[:35], len(content))
        else:
            log.info("  [%d/%d] FAIL %s (%dc)", i+1, len(todo), title[:35], len(content))

        fetched += 1
        if fetched % 50 == 0:
            out_f.flush()
            log.info("  === CHECKPOINT: %d fetched, %d good (%.0f%%) ===", fetched, good, 100*good/fetched)

        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    out_f.close()
    log.info("\n=== DONE ===")
    log.info("Fetched: %d | Good: %d (%.0f%%)", fetched, good, 100*good/max(fetched, 1))


if __name__ == "__main__":
    main()
