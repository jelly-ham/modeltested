import board from "../data/leaderboard.json";

export const SITE_NAME = "Model Tested";
export const TAGLINE = "We test AI models on real work and tell you which ones are worth using.";
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
  return `${total}B`;
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

/** Plain-language names for the test suites (the methodology page keeps the technical ones). */
const SUITE_LABELS: Record<string, { name: string; short: string; blurb: string }> = {
  coding: { name: "Coding", short: "Coding", blurb: "Small programming jobs. We run the code to see if it really works." },
  extract: { name: "Reading documents", short: "Documents", blurb: "Pulling the right numbers, dates and names out of emails, bills and forms. Some need a bit of math." },
};
export const suiteLabel = (id: string) => SUITE_LABELS[id] ?? { name: id, short: id, blurb: "" };

/** "Q4_K_M" -> "Q4". Models that ship in a single native format (e.g. MXFP4) just have a "standard" download. */
export const quantLabel = (q: string | null | undefined) => (!q ? "" : /^Q\d/.test(q) ? q.replace(/_.*$/, "") : "standard");

export function tierLabel(t: Tier): string {
  return t.kind === "gpu" ? `${t.gb} GB graphics card` : `Mac with ${t.gb} GB`;
}

export const whole = (x: number | null | undefined) => (x == null ? "?" : String(Math.round(x)));

/** "extract-expense-thread" -> "Expense thread" */
export function questionTitle(id: string): string {
  const t = id.replace(/^(code|extract)-/, "").replace(/-/g, " ").replace(/\bsla\b/g, "SLA");
  return t.charAt(0).toUpperCase() + t.slice(1);
}

const ORG_NAMES: Record<string, string> = {
  openai: "OpenAI", google: "Google", qwen: "Alibaba's Qwen team", "meta-llama": "Meta", mistralai: "Mistral AI",
  microsoft: "Microsoft", nvidia: "NVIDIA", "z-ai": "Zhipu AI", "ibm-granite": "IBM", deepseek: "DeepSeek",
  moonshotai: "Moonshot AI", liquid: "Liquid AI", tencent: "Tencent", allenai: "Ai2", baidu: "Baidu", cohere: "Cohere",
};
export const orgName = (org: string | null) => (org ? ORG_NAMES[org] ?? org : null);

/** Model family, used as a topic tag. */
const FAMILIES: Record<string, string> = {
  qwen: "Qwen", google: "Gemma", openai: "gpt-oss", "meta-llama": "Llama", mistralai: "Mistral", microsoft: "Phi",
  nvidia: "Nemotron", "z-ai": "GLM", "ibm-granite": "Granite", liquid: "LFM", deepseek: "DeepSeek",
};
export const family = (m: Model) => (m.org ? FAMILIES[m.org] ?? orgName(m.org) : null);

export const nCodingTasks = () => {
  const s = data.suites.find((x) => x.id === "coding");
  return s ? s.n_public + s.n_private : 0;
};
/** Coding score (percent) -> jobs solved. */
export const solved = (codingScore: number | null | undefined) => Math.round(((codingScore ?? 0) / 100) * nCodingTasks());
