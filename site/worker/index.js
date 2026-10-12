// Serves the static site and one small API: page view counts (/api/views?path=/posts/x/).
// Counts live in a single SQLite-backed Durable Object; no IPs or cookies are stored.
import { DurableObject } from "cloudflare:workers";

const COUNTED = /^\/(posts|models|decision-models|hardware|best-local-llms|best-decision-models)(\/[a-z0-9-]+)*\/$/;
const BOT = /bot|crawl|spider|slurp|headless|lighthouse|preview|curl|wget|python|httpclient|java\/|go-http/i;

export class ViewCounter extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS views (path TEXT PRIMARY KEY, n INTEGER NOT NULL)");
  }
  hit(path) {
    this.ctx.storage.sql.exec("INSERT INTO views (path, n) VALUES (?, 1) ON CONFLICT(path) DO UPDATE SET n = n + 1", path);
    return this.get(path);
  }
  get(path) {
    const rows = this.ctx.storage.sql.exec("SELECT n FROM views WHERE path = ?", path).toArray();
    return rows.length ? rows[0].n : 0;
  }
}

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/views") return env.ASSETS.fetch(request);

    const path = url.searchParams.get("path") || "";
    if (path.length > 200 || !COUNTED.test(path)) return json({ error: "not a counted page" }, 400);
    const counter = env.VIEWS.get(env.VIEWS.idFromName("all"));
    const isBot = BOT.test(request.headers.get("user-agent") || "");

    if (request.method === "POST" && !isBot) {
      // Only count pages that exist, so nobody can fill the table with made-up paths.
      const page = await env.ASSETS.fetch(new Request(new URL(path, url.origin)));
      if (page.status !== 200) return json({ error: "no such page" }, 404);
      return json({ path, views: await counter.hit(path) });
    }
    return json({ path, views: await counter.get(path) });
  },
};
