import { analysisMethodPlacement } from "./analysisDomainMapping";
import { isKnownContextualSubworkflow } from "./analysisCapabilities";

export function isContextualAnalysisMethod(methodId: string): boolean {
  return analysisMethodPlacement(methodId)?.contextual ?? isKnownContextualSubworkflow(methodId);
}
