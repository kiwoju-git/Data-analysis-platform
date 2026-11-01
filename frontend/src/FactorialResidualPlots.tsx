import type { DoeFinalModelWorkflow } from "./api/types/doeModelWorkflow";
import { DoeResidualPlots } from "./doe/DoeResidualPlots";

export function FactorialResidualPlots({ plots }: { plots: DoeFinalModelWorkflow["residual_plots"] }) {
  return <DoeResidualPlots plots={plots} />;
}
