import { getCollection } from "astro:content";
import { data, models, ranked, family, minTiers, solved, nCodingTasks, whole, type Model } from "./data";

/** A cover is a small chart (or a big word) drawn from real numbers. */
export type Cover =
  | { kind: "bars"; label: string; rows: { name: string; value: number }[] }
  | { kind: "cells"; label: string; solved: number; total: number }
  | { kind: "model"; label: string; overall: number; rank: number; of: number; coding: number; docs: number }
  | { kind: "compare"; label: string; items: { label: string; value: number }[] }
  | { kind: "word"; label: string; big: string };

export type Post = {
  url: string;
  title: string;
  dek: string;
  date: string; // YYYY-MM-DD
  category: "Rankings" | "Reviews" | "Guides" | "News";
  tags: string[];
  cover: Cover;
  order: number; // tie-break within a day: lower first
};

export const slugTag = (t: string) => t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

/** One plain-English phrase that sums up a model, picked from its scores. */
export function verdict(m: Model): string {
  const c = m.suites.coding?.score ?? 0;
  const d = m.suites.extract?.score ?? 0;
  if (m.rank <= 3) return "one of the best local models we've tested";
  if (c >= 90 && d < 80) return "great at code, weaker with documents";
  if (d >= 90 && c < 70) return "reads documents well, weaker at code";
  if (m.overall >= 80) return "a solid all-rounder";
  if (m.overall >= 60) return "decent, with trade-offs";
  return "not one we'd recommend right now";
}

export function hardwareLine(m: Model): string {
  const t = minTiers(m);
  const parts = [];
  if (t.gpu) parts.push(`${String(t.gpu.gb).startsWith("8") ? "an" : "a"} ${t.gpu.gb} GB graphics card`);
  if (t.mac) parts.push(`a Mac with ${t.mac.gb} GB`);
  return parts.length ? `Runs on ${parts.join(" or ")}.` : "Needs more memory than most home computers have.";
}

function reviewPost(m: Model): Post {
  const c = m.suites.coding?.score ?? 0;
  const d = m.suites.extract?.score ?? 0;
  const gpu = minTiers(m).gpu;
  const tags = ["Reviews", family(m), gpu ? `${gpu.gb} GB GPU` : null, c >= 90 ? "Coding" : null].filter(Boolean) as string[];
  return {
    url: `/models/${m.slug}/`,
    title: `${m.name} review: ${verdict(m)}`,
    dek: `It scored ${whole(m.overall)} out of 100, #${m.rank} of ${models.length}. It solved ${solved(c)} of ${nCodingTasks()} coding jobs and scored ${whole(d)} on reading documents. ${hardwareLine(m)}`,
    date: m.added ?? data.generated,
    category: "Reviews",
    tags,
    cover: { kind: "model", label: m.name, overall: m.overall, rank: m.rank, of: models.length, coding: c, docs: d },
    order: 10 + m.rank,
  };
}

export function rankingPosts(): Post[] {
  const top = ranked("overall").slice(0, 5);
  const coders = ranked("coding");
  return [
    {
      url: "/best-local-llms/",
      title: "The best local LLMs right now",
      dek: `We tested ${models.length} AI models you can run on your own computer. Here's the best one for every graphics card and Mac.`,
      date: data.generated,
      category: "Rankings",
      tags: ["Rankings", "Local LLMs"],
      cover: { kind: "bars", label: "Top 5 · overall score", rows: top.map((m) => ({ name: m.name, value: m.overall })) },
      order: 0,
    },
    {
      url: "/best-local-llms/coding/",
      title: "Best local LLM for coding: we ran the code",
      dek: `${models.length} models, ${nCodingTasks()} programming jobs, each checked against tests the model never saw. Here's who writes code that works.`,
      date: data.generated,
      category: "Rankings",
      tags: ["Rankings", "Coding", "Local LLMs"],
      cover: { kind: "cells", label: "Best coder · jobs solved", solved: solved(coders[0]?.suites.coding?.score), total: nCodingTasks() },
      order: 1,
    },
  ];
}

export async function guidePosts(): Promise<Post[]> {
  const entries = await getCollection("posts");
  return entries.map((e) => {
    const cv = e.data.cover;
    const cover: Cover = cv.compare
      ? { kind: "compare", label: cv.label, items: cv.compare }
      : { kind: "word", label: cv.label, big: cv.big ?? "" };
    return {
      url: `/posts/${e.id}/`,
      title: e.data.title,
      dek: e.data.dek,
      date: e.data.date.toISOString().slice(0, 10),
      category: e.data.category,
      tags: e.data.tags,
      cover,
      order: e.data.category === "News" ? 2 : 5,
    };
  });
}

export async function allPosts(): Promise<Post[]> {
  const posts = [...rankingPosts(), ...(await guidePosts()), ...models.map(reviewPost)];
  return posts.sort((a, b) => b.date.localeCompare(a.date) || a.order - b.order);
}

export async function allTags(): Promise<{ tag: string; slug: string; count: number }[]> {
  const counts = new Map<string, number>();
  for (const p of await allPosts()) for (const t of p.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, slug: slugTag(tag), count }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}

export const shortDate = (iso: string) =>
  new Date(iso + "T00:00:00Z").toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" }).toUpperCase();
