export type DoeFactorDomainKind = "continuous" | "discrete_numeric";

export interface DoeFactorDomainDraft {
  domainKind?: DoeFactorDomainKind;
  step?: string;
  displayDecimals?: string;
}

export const continuousFactorDomainDraft: DoeFactorDomainDraft = {
  domainKind: "continuous",
  step: "",
  displayDecimals: "",
};

export function formatDoeFactorValue(
  value: number,
  displayDecimals: number | null | undefined,
): string {
  if (!Number.isFinite(value)) return "-";
  if (displayDecimals == null) {
    return value.toLocaleString("ko-KR", { maximumSignificantDigits: 8 });
  }
  return value.toLocaleString("ko-KR", {
    minimumFractionDigits: displayDecimals,
    maximumFractionDigits: displayDecimals,
    useGrouping: false,
  });
}

export function parseDoeFactorDomainDraft(
  draft: DoeFactorDomainDraft,
  low: number,
  high: number,
):
  | {
      domain_kind: DoeFactorDomainKind;
      step: number | null;
      display_decimals: number | null;
      level_count: number | null;
    }
  | null {
  const displayDecimalsText = draft.displayDecimals ?? "";
  const displayDecimals = displayDecimalsText.trim() === ""
    ? null
    : Number(displayDecimalsText);
  if (
    displayDecimals !== null &&
    (!Number.isInteger(displayDecimals) || displayDecimals < 0 || displayDecimals > 12)
  ) {
    return null;
  }
  if ((draft.domainKind ?? "continuous") === "continuous") {
    return {
      domain_kind: "continuous",
      step: null,
      display_decimals: displayDecimals,
      level_count: null,
    };
  }
  const step = Number(draft.step ?? "");
  if (!Number.isFinite(step) || step <= 0) return null;
  const intervals = (high - low) / step;
  const rounded = Math.round(intervals);
  if (Math.abs(intervals - rounded) > 1e-10 * Math.max(1, Math.abs(intervals))) {
    return null;
  }
  const levelCount = rounded + 1;
  if (levelCount < 2 || levelCount > 10_001) return null;
  return {
    domain_kind: "discrete_numeric",
    step,
    display_decimals: displayDecimals,
    level_count: levelCount,
  };
}
