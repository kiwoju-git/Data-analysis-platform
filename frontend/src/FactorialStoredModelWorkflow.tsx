import { useState } from "react";
import type { DoeFinalModelWorkflow } from "./api/types/doeModelWorkflow";
import type { FactorialViewDesign } from "./doe/factorialView";
import { isGeneralFactorial } from "./doe/factorialView";
import { FactorialAnalysisAssetsPanel } from "./FactorialAnalysisAssetsPanel";
import { FactorialPredictionPanel } from "./FactorialPredictionPanel";

export function FactorialStoredModelWorkflow({ design, analysisId, model }: { design: FactorialViewDesign; analysisId: string; model?: DoeFinalModelWorkflow | null }) {
  const [revision, setRevision] = useState(0);
  const allowed = isGeneralFactorial(design) || (!design.fractional && !design.screening);
  return <>
    {model && allowed ? <FactorialPredictionPanel key={analysisId} design={design} analysisId={analysisId} basis={model.prediction_basis} onSaved={() => setRevision((value) => value + 1)} /> : null}
    <FactorialAnalysisAssetsPanel key={`assets-${analysisId}`} designId={design.design_id} analysisId={analysisId} refreshKey={revision} />
  </>;
}
