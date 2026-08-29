export const DOE_FACTOR_CAPABILITIES = {
  productMaximum: 10,
  factorialAuthoring: 10,
  generalFactorialAuthoring: 10,
  latinHypercube: 10,
  bayesianStudy: 10,
  responseSurfaceCcd: 5,
} as const;

export const DOE_RUN_CAPABILITIES = {
  factorial: 256,
  generalFactorial: 256,
} as const;

export function factorialCornerRunCount(factorCount: number, replicates = 1): number {
  return 2 ** factorCount * replicates;
}

export function generalFactorialRunCount(
  levelCounts: readonly number[],
  replicates = 1,
): number {
  return levelCounts.reduce((total, levelCount) => total * levelCount, 1) * replicates;
}
