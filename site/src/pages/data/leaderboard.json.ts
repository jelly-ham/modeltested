import type { APIRoute } from "astro";
import { rows, meta } from "./_rows";

export const GET: APIRoute = () =>
  new Response(JSON.stringify({ ...meta(), models: rows() }, null, 1), { headers: { "Content-Type": "application/json" } });
