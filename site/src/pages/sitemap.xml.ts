import type { APIRoute } from "astro";
import { data, models } from "../lib/data";

export const GET: APIRoute = ({ site }) => {
  const paths = ["/", "/best-local-llms/", "/best-local-llms/coding/", "/best-local-llms/methodology/", ...models.map((m) => `/models/${m.slug}/`)];
  const urls = paths
    .map((p) => `<url><loc>${new URL(p, site).href}</loc><lastmod>${data.generated}</lastmod></url>`)
    .join("");
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`, {
    headers: { "Content-Type": "application/xml" },
  });
};
