import type { NormalityResult } from "./api";

export function andersonPValueLabel(
  anderson: NormalityResult["columns"][number]["anderson_darling"],
): string {
  if (anderson.p_value === undefined) return "제공되지 않음 (legacy result)";
  if (anderson.p_value === null) return "-";
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 6 }).format(
    anderson.p_value,
  );
}
