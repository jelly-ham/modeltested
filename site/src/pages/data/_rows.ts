import { data, ranked, minTiers } from "../../lib/data";

/** The public leaderboard, one flat row per model: what /data/leaderboard.json and .csv serve. */
export function rows() {
  return ranked("overall").map((m) => {
    const t = minTiers(m);
    return {
      rank: m.rank,
      model: m.name,
      slug: m.slug,
      org: m.org,
      params_b: m.params_b,
      overall: m.overall,
      coding: m.suites.coding?.score ?? null,
      documents: m.suites.extract?.score ?? null,
      decisions: m.suites.decisions?.score ?? null,
      hard: m.hard ?? null,
      q4_memory_gb: m.memory?.need_gb.Q4_K_M ?? null,
      smallest_gpu_gb: t.gpu?.gb ?? null,
      smallest_mac_gb: t.mac?.gb ?? null,
      hugging_face: m.hf_id,
      tested_on: m.status === "local" ? "Mac (Ollama, Q4)" : "OpenRouter",
      url: `https://modeltested.com/models/${m.slug}/`,
    };
  });
}

export const meta = () => ({
  source: "Model Tested (https://modeltested.com)",
  updated: data.generated,
  methodology: "https://modeltested.com/best-local-llms/methodology/",
  note: "Scores are out of 100. overall = coding + document extraction; decisions are not part of overall. Memory assumes an 8k-token context. Please link to modeltested.com when you use these numbers.",
});
