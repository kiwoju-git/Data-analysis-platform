export type CcdType = "circumscribed" | "inscribed" | "face_centered";

export function strictRsmInteger(value: string): number | null {
  if (!/^\d+$/.test(value.trim())) return null;
  const number = Number(value.trim());
  return Number.isSafeInteger(number) ? number : null;
}

export function recommendedCenterPoints(factorCount: number): number | null {
  return ({ 2: 5, 3: 6, 4: 7, 5: 10 } as Record<number, number>)[factorCount] ?? null;
}

export function ccdBoundsPreview(low: number, high: number, factorCount: number, kind: CcdType) {
  if (![low, high].every(Number.isFinite) || low >= high || factorCount < 2 || factorCount > 5) return null;
  const alpha = kind === "face_centered" ? 1 : (2 ** factorCount) ** 0.25;
  const center = low / 2 + high / 2;
  const half = high / 2 - low / 2;
  const scale = kind === "inscribed" ? half / alpha : half;
  const bounds = { center, scale, alpha, factorialLow: center - scale, factorialHigh: center + scale,
    axialLow: center - alpha * scale, axialHigh: center + alpha * scale };
  return Object.values(bounds).every(Number.isFinite) && scale > 0 ? bounds : null;
}
