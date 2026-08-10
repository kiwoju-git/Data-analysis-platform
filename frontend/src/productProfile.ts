export type StatisticalTwinProfile = "full" | "presentation" | "presentation-regression";

const presentationModuleIds = {
  presentation: ["exploration", "hypothesis"],
  "presentation-regression": ["exploration", "hypothesis", "regression"],
} as const;

export function resolveStatisticalTwinProfile(value: unknown): StatisticalTwinProfile {
  return value === "presentation" || value === "presentation-regression" ? value : "full";
}

export function analysisModuleIdsForProfile(
  profile: StatisticalTwinProfile,
): readonly string[] | null {
  return profile === "full" ? null : presentationModuleIds[profile];
}

export function isAnalysisModuleAvailableInProfile(
  moduleId: string,
  profile: StatisticalTwinProfile,
): boolean {
  const moduleIds = analysisModuleIdsForProfile(profile);
  return moduleIds === null || moduleIds.some((candidate) => candidate === moduleId);
}

export function presentationScopeText(profile: StatisticalTwinProfile): string | null {
  if (profile === "presentation") {
    return "공개 시연 범위: 홈 · 데이터셋 · 탐색적 분석 · 가설 검정";
  }
  if (profile === "presentation-regression") {
    return "공개 시연 범위: 홈 · 데이터셋 · 탐색적 분석 · 가설 검정 · 상관관계 및 회귀분석";
  }
  return null;
}

export const statisticalTwinProfile = resolveStatisticalTwinProfile(
  import.meta.env.VITE_STATISTICAL_TWIN_PROFILE,
);

export const isPresentationProfile = statisticalTwinProfile !== "full";
