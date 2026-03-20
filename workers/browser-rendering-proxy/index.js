// Cloudflare Worker proxy for Browser Rendering API
// Uses @cloudflare/puppeteer for browser control
// Auth: X-API-KEY header

import puppeteer from "@cloudflare/puppeteer";

const API_KEY = "cognebula-br-2026";

export default {
  async fetch(request, env) {
    const authKey = request.headers.get("X-API-KEY");
    if (authKey !== API_KEY) {
      return json({ error: "unauthorized" }, 401);
    }

    const url = new URL(request.url);
    const path = url.pathname;

    try {
      if (path === "/scrape" && request.method === "POST") {
        return await handleScrape(request, env);
      } else if (path === "/crawl" && request.method === "POST") {
        return await handleCrawl(request, env);
      } else if (path === "/markdown" && request.method === "POST") {
        return await handleMarkdown(request, env);
      } else if (path === "/health") {
        return json({ status: "ok", service: "cognebula-browser-proxy", version: "2.0" });
      } else {
        return json({ endpoints: ["/scrape", "/crawl", "/markdown", "/health"] }, 404);
      }
    } catch (e) {
      return json({ error: e.message, stack: e.stack?.split("\n").slice(0, 3) }, 500);
    }
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function handleScrape(request, env) {
  const body = await request.json();
  const targetUrl = body.url;
  const selectors = body.selectors || [];

  const browser = await puppeteer.launch(env.BROWSER);
  const page = await browser.newPage();

  await page.goto(targetUrl, { waitUntil: "networkidle0", timeout: 30000 });

  const title = await page.title();
  const results = [];

  for (const sel of selectors) {
    const selector = typeof sel === "string" ? sel : sel.selector;
    try {
      const elements = await page.$$eval(selector, (els) =>
        els.map((el) => ({
          text: el.innerText?.trim().substring(0, 500),
          href: el.getAttribute("href"),
          tag: el.tagName.toLowerCase(),
        }))
      );
      results.push({ selector, count: elements.length, elements: elements.slice(0, 100) });
    } catch (e) {
      results.push({ selector, count: 0, error: e.message });
    }
  }

  await browser.close();
  return json({ success: true, url: targetUrl, title, results });
}

async function handleMarkdown(request, env) {
  const body = await request.json();
  const targetUrl = body.url;

  const browser = await puppeteer.launch(env.BROWSER);
  const page = await browser.newPage();
  await page.goto(targetUrl, { waitUntil: "networkidle0", timeout: 30000 });

  const title = await page.title();
  const text = await page.evaluate(() => document.body.innerText);

  await browser.close();
  return json({ success: true, url: targetUrl, title, text: text.substring(0, 50000) });
}

async function handleCrawl(request, env) {
  const body = await request.json();
  const startUrl = body.url;
  const maxPages = Math.min(body.limit || 10, 20);
  const maxDepth = Math.min(body.depth || 1, 2);

  const visited = new Set();
  const queue = [{ url: startUrl, depth: 0 }];
  const results = [];

  const browser = await puppeteer.launch(env.BROWSER);

  while (queue.length > 0 && results.length < maxPages) {
    const { url: pageUrl, depth: currentDepth } = queue.shift();
    if (visited.has(pageUrl)) continue;
    visited.add(pageUrl);

    try {
      const page = await browser.newPage();
      await page.goto(pageUrl, { waitUntil: "networkidle0", timeout: 20000 });

      const title = await page.title();
      const text = await page.evaluate(() => document.body.innerText);

      if (currentDepth < maxDepth) {
        const baseHost = new URL(startUrl).hostname;
        const links = await page.evaluate(() =>
          Array.from(document.querySelectorAll("a[href]"))
            .map((a) => a.href)
            .filter((h) => h.startsWith("http"))
        );
        for (const link of links.slice(0, 50)) {
          try {
            if (new URL(link).hostname === baseHost && !visited.has(link)) {
              queue.push({ url: link, depth: currentDepth + 1 });
            }
          } catch {}
        }
      }

      await page.close();
      results.push({ url: pageUrl, title, text: text.substring(0, 3000), depth: currentDepth, status: "ok" });
    } catch (e) {
      results.push({ url: pageUrl, depth: currentDepth, status: "error", error: e.message });
    }
  }

  await browser.close();
  return json({ success: true, total: results.length, results });
}
