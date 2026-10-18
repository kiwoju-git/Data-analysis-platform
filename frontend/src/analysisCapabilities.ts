import { limits, subworkflows } from "./generated/analysisCapabilities.json";

// Build-time contract facts, never a substitute for live method/source eligibility.
export const ANALYSIS_CAPABILITY_LIMITS = Object.freeze(limits);

const contextualSubworkflowIds = new Set(subworkflows.map((workflow) => workflow.method_id));

export function isKnownContextualSubworkflow(methodId: string): boolean {
  return contextualSubworkflowIds.has(methodId);
}
