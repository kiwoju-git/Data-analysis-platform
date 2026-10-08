import type { AnalysisPlannedWorkflow } from "./analysisDomains";

export function visiblePlannedWorkflows(workflows: readonly AnalysisPlannedWorkflow[] = []): AnalysisPlannedWorkflow[] {
  return workflows.filter((workflow) => workflow.visibility !== "roadmap_only");
}
