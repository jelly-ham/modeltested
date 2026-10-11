import { ranked, type Model, type Tier } from "./data";

/** "16gb-gpu" / "mac-32gb" */
export const hardwareSlug = (t: Tier) => (t.kind === "gpu" ? `${t.gb}gb-gpu` : `mac-${t.gb}gb`);

export const hardwareName = (t: Tier) => (t.kind === "gpu" ? `a ${t.gb} GB graphics card` : `a Mac with ${t.gb} GB of memory`);

/** Models that fit a tier at Q4 or better, best overall score first, with the version to download. */
export function fitsTier(t: Tier): { model: Model; quant: string; gb: number }[] {
  return ranked("overall")
    .filter((m) => m.memory?.best_quant_by_tier[t.id])
    .map((m) => {
      const quant = m.memory!.best_quant_by_tier[t.id]!;
      return { model: m, quant, gb: m.memory!.need_gb[quant] };
    });
}
