import type { APIRoute } from "astro";
import { data, models, minTiers, quantRunFor, decisionHref, orgName } from "../../lib/data";
import { guidePosts, rankingPosts } from "../../lib/posts";

// Everything the MCP server (worker/mcp.js) answers from, built with the site so the two never disagree.
// Only public numbers: the same scores and estimates the pages show, no questions or answers.
export const GET: APIRoute = async ({ site }) => {
  const u = (p: string) => new URL(p, site).href;
  const model = (m: (typeof models)[number]) => {
    const t = minTiers(m);
    const q = quantRunFor(m);
    return {
      slug: m.slug,
      name: m.name,
      maker: orgName(m.org),
      params_b: m.params_b,
      active_params_b: m.active_params_b,
      rank: m.rank,
      overall: m.overall,
      coding: m.suites.coding?.score ?? null,
      documents: m.suites.extract?.score ?? null,
      decisions: m.suites.decisions?.score ?? null,
      hard: m.hard ?? null,
      tested_on: m.status === "local" ? `Mac (Ollama, ${m.quant ?? "Q4"})` : "OpenRouter, full precision",
      memory_gb: m.memory?.need_gb ?? null,
      best_quant_by_tier: m.memory?.best_quant_by_tier ?? null,
      smallest_gpu_gb: t.gpu?.gb ?? null,
      smallest_mac_gb: t.mac?.gb ?? null,
      quantized_run: q ? { name: q.name, quant: q.quant, overall: q.overall, change: q.delta, url: u(`/models/${q.slug}/`) } : null,
      hugging_face: m.hf_id ? `https://huggingface.co/${m.hf_id}` : null,
      ollama: m.ollama,
      license: m.license ?? null,
      added: m.added ?? null,
      url: u(`/models/${m.slug}/`),
    };
  };
  const posts = [...rankingPosts(), ...(await guidePosts())]
    .sort((a, b) => b.date.localeCompare(a.date))
    .map((p) => ({ title: p.title, summary: p.dek, date: p.date, tags: p.tags, url: u(p.url) }));
  const body = {
    source: "Model Tested (https://modeltested.com)",
    updated: data.generated,
    methodology: u("/best-local-llms/methodology/"),
    tiers: data.tiers,
    models: models.map(model),
    decisions: (data.decisions ?? []).map((r) => ({
      rank: r.rank,
      name: r.name,
      slug: r.slug,
      type: r.kind === "decision" ? "decision model" : r.kind === "local" ? "regular LLM" : "reference",
      maker: orgName(r.org),
      accuracy: r.accuracy,
      hard: r.hard ?? null,
      calibration: r.calibration,
      cost_per_1k_calls: r.cost_per_1k == null ? null : r.cost_per_1k < 0.01 ? "under $0.01" : `$${r.cost_per_1k.toFixed(2)}`,
      open_weights: r.open_weights ?? null,
      url: decisionHref(r) ? u(decisionHref(r)!) : null,
    })),
    posts,
  };
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
};
