import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// Hand-written guides and news. Rankings and model reviews are generated from
// benchmark data in src/lib/posts.ts.
const posts = defineCollection({
  loader: glob({ pattern: "*.md", base: "./src/content/posts" }),
  schema: z.object({
    title: z.string(),
    dek: z.string(),
    date: z.coerce.date(),
    category: z.enum(["Guides", "News"]),
    tags: z.array(z.string()),
    // Cover drawn in markup: a big word/number, or a small bar comparison of real numbers.
    cover: z
      .object({
        label: z.string(),
        big: z.string().optional(),
        compare: z.array(z.object({ label: z.string(), value: z.number() })).optional(),
      }),
  }),
});

export const collections = { posts };
