import { lazy } from "react";

export const PearsonCorrelationPanel = lazy(() =>
  import("./RegressionAnalysisPanels").then((module) => ({
    default: module.PearsonCorrelationPanel,
  })),
);

export const XyCorrelationPanel = lazy(() =>
  import("./RegressionAnalysisPanels").then((module) => ({
    default: module.XyCorrelationPanel,
  })),
);

export const LinearModelPanel = lazy(() =>
  import("./RegressionAnalysisPanels").then((module) => ({
    default: module.LinearModelPanel,
  })),
);

export const RegressionPredictionWorkspace = lazy(() =>
  import("./RegressionAnalysisPanels").then((module) => ({
    default: module.RegressionPredictionWorkspace,
  })),
);

export const AttributeControlChartPanel = lazy(() =>
  import("./QualityAnalysisPanels").then((module) => ({
    default: module.AttributeControlChartPanel,
  })),
);

export const RunChartPanel = lazy(() =>
  import("./QualityAnalysisPanels").then((module) => ({
    default: module.RunChartPanel,
  })),
);

export const CapabilityPanel = lazy(() =>
  import("./QualityAnalysisPanels").then((module) => ({
    default: module.CapabilityPanel,
  })),
);

export const GageRrPreflightPanel = lazy(() =>
  import("./QualityAnalysisPanels").then((module) => ({
    default: module.GageRrPreflightPanel,
  })),
);

export const GageRunChartPanel = lazy(() =>
  import("./QualityAnalysisPanels").then((module) => ({
    default: module.GageRunChartPanel,
  })),
);

export const SubgroupChartPanel = lazy(() =>
  import("./QualityAnalysisPanels").then((module) => ({
    default: module.SubgroupChartPanel,
  })),
);

export const IndividualsChartPanel = lazy(() =>
  import("./QualityAnalysisPanels").then((module) => ({
    default: module.IndividualsChartPanel,
  })),
);

export const FactorialDesignPanel = lazy(() =>
  import("./DoeAnalysisPanels").then((module) => ({
    default: module.FactorialDesignPanel,
  })),
);

export const ResponseSurfacePanel = lazy(() =>
  import("./DoeAnalysisPanels").then((module) => ({
    default: module.ResponseSurfacePanel,
  })),
);

export const ResponseOptimizerWorkspace = lazy(() =>
  import("./DoeAnalysisPanels").then((module) => ({
    default: module.ResponseOptimizerWorkspace,
  })),
);

export const BayesianOptimizationPanel = lazy(() =>
  import("./DoeAnalysisPanels").then((module) => ({
    default: module.BayesianOptimizationPanel,
  })),
);
