import type { APIRoute } from "astro";
import { rows } from "./_rows";

const cell = (v: unknown) => {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export const GET: APIRoute = () => {
  const r = rows();
  const cols = Object.keys(r[0]);
  const body = [cols.join(","), ...r.map((x) => cols.map((c) => cell((x as Record<string, unknown>)[c])).join(","))].join("\n") + "\n";
  return new Response(body, { headers: { "Content-Type": "text/csv; charset=utf-8" } });
};
