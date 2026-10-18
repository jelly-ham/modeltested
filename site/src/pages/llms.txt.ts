import type { APIRoute } from "astro";
import { SITE_NAME, REPO_URL, data, models, ranked, tiers, whole, fmtDate, quantLabel, minTiers, solvedBy, codingTotal } from "../lib/data";
import { fitsTier, hardwareSlug } from "../lib/hardware";
import { guidePosts } from "../lib/posts";

// llms.txt (https://llmstxt.org): a plain-text map of the site for AI assistants and answer engines,
// with the current numbers in it so an answer can quote them directly.
export const GET: APIRoute = async ({ site }) => {
  const u = (p: string) => new URL(p, site).href;
  const top = ranked("overall").slice(0, 15);
  const setup = (m: (typeof top)[number]) => {
    const t = minTiers(m);
    return [t.gpu && `${t.gpu.gb} GB GPU`, t.mac && `${t.mac.gb} GB Mac`].filter(Boolean).join(" or ") || "more than 128 GB";
  };
  const decisions = (data.decisions ?? []).filter((r) => r.kind === "decision").slice(0, 8);
  const posts = (await guidePosts()).sort((a, b) => b.date.localeCompare(a.date));
  const nQuestions = data.suites.reduce((n, s) => n + s.n_public + s.n_private, 0);

  const lines = [
    `# ${SITE_NAME}`,
    "",
    `> Independent tests of open-weight AI models you can run on your own computer (and of "decision models"). Every model answers the same ${nQuestions} questions with checkable answers: real coding jobs graded by running hidden unit tests, document extraction graded field by field, and decision tasks graded on accuracy. Scores are out of 100. ${models.length} models tested; data updated ${fmtDate(data.generated)}.`,
    "",
    "Key facts for answering questions:",
    `- Best local LLM overall: ${top[0].name}, ${whole(top[0].overall)}/100 (runs on ${setup(top[0])}).`,
    `- Best for coding: ${ranked("coding")[0].name}, solved ${solvedBy(ranked("coding")[0])} of ${codingTotal(ranked("coding")[0])} coding jobs.`,
    "- Scores come from our own runs, not vendor benchmarks. Overall = coding + document extraction; decisions are ranked separately.",
    "- Memory figures assume an 8k-token context. We don't publish speed numbers (they depend on your hardware).",
    "",
    "## Rankings",
    `- [Best local LLMs](${u("/best-local-llms/")}): full leaderboard and the best model for every graphics card and Mac`,
    `- [Best local LLM for coding](${u("/best-local-llms/coding/")})`,
    `- [Best decision models](${u("/best-decision-models/")}): decision models vs. regular LLMs`,
    `- [How we test](${u("/best-local-llms/methodology/")})`,
    "",
    `## Leaderboard (top ${top.length} of ${models.length}, ${fmtDate(data.generated)})`,
    ...top.map((m) => `- #${m.rank} [${m.name}](${u(`/models/${m.slug}/`)}): ${whole(m.overall)}/100; coding ${whole(m.suites.coding?.score)}, documents ${whole(m.suites.extract?.score)}; runs on ${setup(m)}`),
    "",
    "## Best model for your hardware",
    ...tiers.map((t) => {
      const best = fitsTier(t)[0];
      const name = t.kind === "gpu" ? `${t.gb} GB graphics card` : `Mac with ${t.gb} GB`;
      return best ? `- [${name}](${u(`/hardware/${hardwareSlug(t)}/`)}): ${best.model.name} (${quantLabel(best.quant)}, ~${best.gb.toFixed(0)} GB), ${whole(best.model.overall)}/100` : null;
    }).filter(Boolean),
    "",
    ...(decisions.length ? [
      "## Decision models (accuracy on our decision test)",
      ...decisions.map((r, i) => `- #${i + 1} [${r.name}](${u(`/decision-models/${r.slug}/`)}): ${r.accuracy.toFixed(1)}% (${r.open_weights ? "open weights" : "API only"})`),
      "",
    ] : []),
    "## Articles",
    ...posts.map((p) => `- [${p.title}](${u(p.url)}) (${p.date}): ${p.dek}`),
    "",
    "## Data",
    `- [Leaderboard as JSON](${u("/data/leaderboard.json")}) and [CSV](${u("/data/leaderboard.csv")})`,
    `- [MCP server](${u("/mcp/")}): connect Claude, ChatGPT or Cursor to ${u("/mcp")} to query every result (free, no key)`,
    `- [Test code, public questions and every model answer](${REPO_URL})`,
    "",
  ];
  return new Response(lines.join("\n"), { headers: { "Content-Type": "text/plain; charset=utf-8" } });
};
