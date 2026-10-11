import type { APIRoute } from "astro";
import { allPosts } from "../lib/posts";
import { SITE_NAME, TAGLINE } from "../lib/data";

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export const GET: APIRoute = async ({ site }) => {
  const items = (await allPosts())
    .slice(0, 50)
    .map((p) => {
      const url = new URL(p.url, site).href;
      return `<item><title>${esc(p.title)}</title><link>${url}</link><guid>${url}</guid><pubDate>${new Date(p.date + "T12:00:00Z").toUTCString()}</pubDate><category>${esc(p.category)}</category><description>${esc(p.dek)}</description></item>`;
    })
    .join("");
  const body = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>${esc(SITE_NAME)}</title><link>${new URL("/", site).href}</link><description>${esc(TAGLINE)}</description>${items}</channel></rss>`;
  return new Response(body, { headers: { "Content-Type": "application/rss+xml; charset=utf-8" } });
};
