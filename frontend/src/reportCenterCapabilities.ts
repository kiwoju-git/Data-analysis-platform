export interface ReportCreationCapabilities {
  json: boolean;
  csv: boolean;
  html: boolean;
}

export interface ReportWorkflowCapability {
  methodId: string;
  label: string;
  storedResult: string;
  json: string;
  csv: string;
  html: string;
  workflowPath: string;
}

const dedicatedMethodIds = new Set([
  "regression.predict",
  "regression.response_optimizer",
  "doe.factorial_design",
  "doe.response_surface",
  "doe.bayesian_optimization",
]);

export function reportCreationCapabilities(methodId: string): ReportCreationCapabilities {
  if (dedicatedMethodIds.has(methodId)) return { json: false, csv: false, html: false };
  return { json: true, csv: true, html: true };
}

export const reportWorkflowCapabilities: readonly ReportWorkflowCapability[] = [
  {
    methodId: "generic-analysis-run",
    label: "일반 분석 실행",
    storedResult: "지원",
    json: "지원",
    csv: "지원",
    html: "지원",
    workflowPath: "/reports",
  },
  {
    methodId: "regression.predict",
    label: "Predict",
    storedResult: "전용 화면에서 지원",
    json: "현재 지원되지 않음",
    csv: "전용 화면에서 full prediction CSV 지원",
    html: "현재 지원되지 않음",
    workflowPath: "/analysis/regression/regression.predict",
  },
  {
    methodId: "regression.response_optimizer",
    label: "Response Optimizer",
    storedResult: "전용 화면에서 지원",
    json: "현재 지원되지 않음",
    csv: "현재 지원되지 않음",
    html: "현재 지원되지 않음",
    workflowPath: "/analysis/regression/regression.response_optimizer",
  },
  {
    methodId: "doe.factorial_design",
    label: "Factorial DOE",
    storedResult: "전용 화면에서 지원",
    json: "현재 지원되지 않음",
    csv: "현재 지원되지 않음",
    html: "설계 화면에서 지원",
    workflowPath: "/analysis/doe/doe.factorial_design",
  },
  {
    methodId: "doe.response_surface",
    label: "RSM",
    storedResult: "전용 화면에서 지원",
    json: "현재 지원되지 않음",
    csv: "현재 지원되지 않음",
    html: "현재 지원되지 않음",
    workflowPath: "/analysis/doe/doe.response_surface",
  },
  {
    methodId: "doe.bayesian_optimization",
    label: "Bayesian Optimization",
    storedResult: "전용 화면에서 지원",
    json: "현재 지원되지 않음",
    csv: "현재 지원되지 않음",
    html: "현재 지원되지 않음",
    workflowPath: "/analysis/doe/doe.bayesian_optimization",
  },
] as const;
