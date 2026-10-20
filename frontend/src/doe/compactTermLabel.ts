import type { DoeAnalysisTerm } from "../api/types/doeModelWorkflow";

export function compactTermLabel(
  term: DoeAnalysisTerm, coding: "coded" | "treatment", factorNames: readonly string[],
): string | null {
  if (coding === "coded" && term.kind === "quadratic" && /^factor_[1-9]\d*\^2$/.test(term.term_id)) {
    const index = Number(term.term_id.slice(7, -2)) - 1;
    return index >= 0 && index < factorNames.length && index < 26
      ? `${String.fromCharCode(65 + index)}²` : null;
  }
  if (!["main_effect", "interaction"].includes(term.kind)) return null;
  const indices = coding === "coded"
    ? /^factor_[1-9]\d*(?::factor_[1-9]\d*)*$/.test(term.term_id)
      ? term.term_id.split(":").map((id) => Number(id.slice(7)) - 1) : []
    : term.factor_ids.map((name) => factorNames.indexOf(name));
  if (!indices.length || indices.some((index) => index < 0 || index >= factorNames.length || index >= 26)) return null;
  return indices.map((index) => String.fromCharCode(65 + index)).join("");
}
