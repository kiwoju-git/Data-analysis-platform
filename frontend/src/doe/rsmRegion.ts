import type { ResponseSurfaceDesignResponse } from "../api";

export type RsmRegionMode = "axial_bounds" | "factorial_cube" | "custom" | "legacy_input_bounds_v1";
export interface RsmBounds { lower: number; upper: number }
export interface RsmResolvedRegion {
  factorName: string;
  inputBoundsRole: "factorial" | "axial" | "factorial_and_axial";
  input: RsmBounds; factorial: RsmBounds; axial: RsmBounds; observed: RsmBounds; effective: RsmBounds;
  center: number; scale: number; anchor: number; step: number | null;
}

export function resolveRsmRegion(
  design: ResponseSurfaceDesignResponse,
  mode: RsmRegionMode = "axial_bounds",
  customBounds?: Record<string, RsmBounds>,
): RsmResolvedRegion[] {
  return design.factors.map((factor) => {
    const alpha = design.options.alpha;
    const center = factor.low / 2 + factor.high / 2;
    const legacyScale = (factor.high / 2 - factor.low / 2) / alpha;
    const coding = design.coding?.[factor.name] ?? {
      center, scale: legacyScale, alpha,
      input_bounds_role: alpha === 1 ? "factorial_and_axial" as const : "axial" as const,
      factorial_low: center - legacyScale, factorial_high: center + legacyScale,
      axial_low: factor.low, axial_high: factor.high,
    };
    const input = { lower: factor.low, upper: factor.high };
    const factorial = { lower: coding.factorial_low, upper: coding.factorial_high };
    const axial = { lower: coding.axial_low, upper: coding.axial_high };
    const values = design.runs.map((run) => run.factor_levels[factor.name]);
    const observed = { lower: Math.min(...values), upper: Math.max(...values) };
    const effective = mode === "factorial_cube" ? factorial : mode === "legacy_input_bounds_v1" ? input
      : mode === "custom" ? customBounds?.[factor.name] : axial;
    if (!effective || ![effective.lower, effective.upper, coding.center, coding.scale].every(Number.isFinite)
      || effective.lower >= effective.upper || effective.lower < axial.lower || effective.upper > axial.upper) {
      throw new Error("doe_rsm_region_bounds_invalid");
    }
    if (factor.domain_kind === "discrete_numeric" &&
      (!isRsmOnLattice(effective.lower, factor.low, factor.step) ||
        !isRsmOnLattice(effective.upper, factor.low, factor.step))) {
      throw new Error("doe_rsm_region_bounds_not_executable");
    }
    return { factorName: factor.name, inputBoundsRole: coding.input_bounds_role, input, factorial, axial,
      observed, effective, center: coding.center, scale: coding.scale, anchor: factor.low, step: factor.step ?? null };
  });
}

export function isRsmExecutable(value: number, region: RsmResolvedRegion): boolean {
  if (!Number.isFinite(value) || value < region.effective.lower || value > region.effective.upper) return false;
  if (region.step === null) return true;
  return isRsmOnLattice(value, region.anchor, region.step);
}

function decimalParts(value: number): { coefficient: bigint; exponent: number } {
  const [mantissa, exponent = "0"] = String(value).split("e");
  const [integer, fraction = ""] = mantissa.split(".");
  return { coefficient: BigInt(integer + fraction), exponent: Number(exponent) - fraction.length };
}

export function decimalLatticeValue(anchor: number, step: number, index: number): number | null {
  if (!Number.isFinite(anchor) || !Number.isFinite(step) || step <= 0 ||
      !Number.isSafeInteger(index) || index < 0 || index > 10000) return null;
  const a = decimalParts(anchor), s = decimalParts(step);
  const exponent = Math.min(a.exponent, s.exponent);
  const coefficient = a.coefficient * 10n ** BigInt(a.exponent - exponent) +
    BigInt(index) * s.coefficient * 10n ** BigInt(s.exponent - exponent);
  const value = Number(`${coefficient}e${exponent}`);
  return Number.isFinite(value) ? value : null;
}

export function isRsmOnLattice(value: number, anchor: number, step: number | null | undefined): boolean {
  if (!Number.isFinite(value) || !Number.isFinite(anchor) || step == null || !Number.isFinite(step) || step <= 0) return false;
  // Match the backend Decimal(str(value)) policy; binary division widens the
  // accepted grid at large offsets and loses accuracy with small decimal steps.
  const parts = [value, anchor, step].map(decimalParts);
  const exponent = Math.min(...parts.map((part) => part.exponent));
  const [coordinate, origin, spacing] = parts.map((part) =>
    part.coefficient * 10n ** BigInt(part.exponent - exponent));
  const difference = coordinate - origin;
  const remainder = (difference < 0n ? -difference : difference) % spacing;
  const nearest = remainder < spacing - remainder ? remainder : spacing - remainder;
  return nearest * 1_000_000_000_000n <= spacing;
}
