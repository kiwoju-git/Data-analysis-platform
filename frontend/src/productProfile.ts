import { t } from "./i18n/translate";
import type { AppLocale } from "./i18n/types";

export type StatisticalTwinProfile =
  | "full"
  | "presentation"
  | "presentation-regression"
  | "presentation-four-domains";

const fourDomainMethodIds = new Set([
  "eda.descriptive",
  "eda.graphical_summary",
  "eda.normality",
  "hypothesis.one_sample_t",
  "hypothesis.paired_t",
  "hypothesis.two_sample_t",
  "hypothesis.one_way_anova",
  "hypothesis.equivalence_tost",
  "hypothesis.two_sample_equivalence_tost",
  "hypothesis.paired_equivalence_tost",
  "hypothesis.one_sample_wilcoxon",
  "hypothesis.mann_whitney",
  "hypothesis.kruskal_wallis",
  "categorical.one_proportion",
  "categorical.two_proportion",
  "categorical.chi_square_association",
  "regression.pearson",
  "regression.xy_correlation",
  "regression.linear_model",
  "regression.partial_least_squares",
  "regression.predict",
  "regression.predict_pasted",
  "regression.linear_model_optimizer",
]);

const presentationModuleIds = {
  presentation: ["exploration", "hypothesis"],
  "presentation-regression": ["exploration", "hypothesis", "regression"],
  "presentation-four-domains": [
    "exploration",
    "hypothesis",
    "categorical",
    "regression",
  ],
} as const;

export function resolveStatisticalTwinProfile(value: unknown): StatisticalTwinProfile {
  return value === "presentation" ||
    value === "presentation-regression" ||
    value === "presentation-four-domains"
    ? value
    : "full";
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

export function isAnalysisDomainAvailableInProfile(
  domainId: string,
  profile: StatisticalTwinProfile,
): boolean {
  if (profile === "full") return true;
  const domainIds =
    profile === "presentation"
      ? ["basic-exploration", "mean-equivalence"]
      : profile === "presentation-regression"
        ? [
            "basic-exploration",
            "mean-equivalence",
            "correlation-regression-prediction",
          ]
        : [
            "basic-exploration",
            "mean-equivalence",
            "proportions-categorical",
            "correlation-regression-prediction",
          ];
  return domainIds.includes(domainId);
}

export function isAnalysisMethodAvailableInProfile(
  methodId: string,
  profile: StatisticalTwinProfile,
): boolean {
  return profile !== "presentation-four-domains" || fourDomainMethodIds.has(methodId);
}

export function isPresentationProductProfile(profile: StatisticalTwinProfile): boolean {
  return profile !== "full";
}

export function presentationScopeText(
  profile: StatisticalTwinProfile,
  locale: AppLocale,
): string | null {
  if (profile === "presentation") {
    return t("profile.scopeCore", {}, locale);
  }
  if (profile === "presentation-regression") {
    return t("profile.scopeRegression", {}, locale);
  }
  if (profile === "presentation-four-domains") {
    return t("profile.scopeFourDomains", {}, locale);
  }
  return null;
}

export const statisticalTwinProfile = resolveStatisticalTwinProfile(
  import.meta.env.VITE_STATISTICAL_TWIN_PROFILE,
);

export const isPresentationProfile = isPresentationProductProfile(statisticalTwinProfile);
