import board from "../data/leaderboard.json";

export const SITE_NAME = "Model Tested";
export const TAGLINE = "Every new AI model, put through real tasks.";
export const REPO_URL = "https://github.com/jelly-ham/modeltested";

export type SuiteScore = { score: number | null; public: number | null; private: number | null; done: number; total: number };
export type Model = {
  slug: string;
  name: string;
  org: string | null;
  openrouter_id: string;
  hf_id: string | null;
  params_b: number | null;
  active_params_b: number | null;
  ollama: string | null;
  license?: string | null;
  added?: string | null;
  overall: number;
  rank: number;
  suites: Record<string, SuiteScore>;
  providers: string[];
  memory: { context: number; kv_cache_gb: number; need_gb: Record<string, number>; best_quant_by_tier: Record<string, string | null> } | null;
};
export type Tier = { id: string; label: string; kind: "gpu" | "mac"; gb: number; usable_gb: number };

export const data = board as unknown as {
  generated: string;
  suites: { id: string; name: string; description: string; n_public: number; n_private: number }[];
  tiers: Tier[];
  memory_assumptions: { context: number; overhead_gb: number; quants: Record<string, number> };
  models: Model[];
  pending: string[];
  changelog: { date: string; slug: string; name: string; event: string; overall: number; rank: number; of: number }[];
};

export const models = data.models;
export const tiers = data.tiers;

export function monthYear(iso: string = data.generated): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-US", { month: "long", year: "numeric", timeZone: "UTC" });
}

export function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
}

export function size(m: Model): string {
  if (!m.params_b) return "—";
  const total = m.params_b >= 10 ? Math.round(m.params_b) : Math.round(m.params_b * 10) / 10;
  return m.active_params_b ? `${total}B (${m.active_params_b}B active)` : `${total}B`;
}

export function score(m: Model, by: string): number {
  return by === "overall" ? m.overall : (m.suites[by]?.score ?? 0);
}

export function ranked(by: string = "overall"): Model[] {
  return [...models].sort((a, b) => score(b, by) - score(a, by) || (a.params_b ?? 0) - (b.params_b ?? 0));
}

/** Models that fit a tier (at Q4 or better), best first. */
export function forTier(tierId: string, by: string = "overall"): { model: Model; quant: string }[] {
  return ranked(by)
    .filter((m) => m.memory?.best_quant_by_tier[tierId])
    .map((m) => ({ model: m, quant: m.memory!.best_quant_by_tier[tierId]! }));
}

/** Smallest GPU and Mac tier the model fits on. */
export function minTiers(m: Model): { gpu: Tier | null; mac: Tier | null } {
  const fit = (kind: string) => tiers.find((t) => t.kind === kind && m.memory?.best_quant_by_tier[t.id]) ?? null;
  return { gpu: fit("gpu"), mac: fit("mac") };
}

export function bySlug(slug: string): Model | undefined {
  return models.find((m) => m.slug === slug);
}

export const pct = (x: number | null | undefined) => (x == null ? "—" : x.toFixed(1));
