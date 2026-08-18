import type { AnalysisDomainId } from "./analysisDomains";
import type { TranslationKey } from "./i18n/translate";

export interface AnalysisDomainGuide {
  domainId: AnalysisDomainId;
  guidanceKey: TranslationKey;
}
export const ANALYSIS_DOMAIN_GUIDANCE: readonly AnalysisDomainGuide[] = [
  { domainId: "basic-exploration", guidanceKey: "analysisGuidance.basic" },
  { domainId: "mean-equivalence", guidanceKey: "analysisGuidance.mean" },
  { domainId: "proportions-categorical", guidanceKey: "analysisGuidance.categorical" },
  { domainId: "correlation-regression-prediction", guidanceKey: "analysisGuidance.regression" },
  { domainId: "doe-optimization", guidanceKey: "analysisGuidance.doe" },
  { domainId: "ai-ml-experimental-design", guidanceKey: "analysisGuidance.ai" },
  { domainId: "quality-process-monitoring", guidanceKey: "analysisGuidance.quality" },
  { domainId: "measurement-variability", guidanceKey: "analysisGuidance.measurement" },
] as const;

export function domainGuidanceKey(domainId: AnalysisDomainId): TranslationKey {
  return ANALYSIS_DOMAIN_GUIDANCE.find((guide) => guide.domainId === domainId)!.guidanceKey;
}
