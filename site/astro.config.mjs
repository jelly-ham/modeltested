import { defineConfig } from "astro/config";

// Canonical URLs and the sitemap use this origin; SITE_URL overrides it (e.g. for a staging deploy).
export default defineConfig({
  site: process.env.SITE_URL || "https://modeltested.com",
  trailingSlash: "always",
  build: { format: "directory" },
});
