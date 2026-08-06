const contextualAnalysisMethodIds = new Set([
  "regression.predict",
  "regression.predict_pasted",
  "regression.predict_manual",
  "regression.linear_model_optimizer",
  "doe.general_factorial_design",
]);

export function isContextualAnalysisMethod(methodId: string): boolean {
  return contextualAnalysisMethodIds.has(methodId);
}
