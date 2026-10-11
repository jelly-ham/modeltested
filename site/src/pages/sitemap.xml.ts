import type { APIRoute } from "astro";
import { data, tiers } from "../lib/data";
import { hardwareSlug } from "../lib/hardware";
import { allPosts, allTags } from "../lib/posts";

export const GET: APIRoute = async ({ site }) => {
  const posts = await allPosts();
  const entries = [
    { path: "/", date: data.generated },
    { path: "/posts/", date: data.generated },
    { path: "/best-local-llms/methodology/", date: data.generated },
    ...posts.map((p) => ({ path: p.url, date: p.category === "Guides" || p.category === "News" ? p.date : data.generated })),
    ...(await allTags()).map((t) => ({ path: `/topics/${t.slug}/`, date: data.generated })),
    ...tiers.map((t) => ({ path: `/hardware/${hardwareSlug(t)}/`, date: data.generated })),
  ];
  const urls = entries.map((e) => `<url><loc>${new URL(e.path, site).href}</loc><lastmod>${e.date}</lastmod></url>`).join("");
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`, {
    headers: { "Content-Type": "application/xml" },
  });
};
