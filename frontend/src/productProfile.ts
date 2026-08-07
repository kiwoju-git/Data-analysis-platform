export type StatisticalTwinProfile = "full" | "presentation";

export function resolveStatisticalTwinProfile(value: unknown): StatisticalTwinProfile {
  return value === "presentation" ? "presentation" : "full";
}

export const statisticalTwinProfile = resolveStatisticalTwinProfile(
  import.meta.env.VITE_STATISTICAL_TWIN_PROFILE,
);

export const isPresentationProfile = statisticalTwinProfile === "presentation";
