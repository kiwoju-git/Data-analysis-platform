import type { TranslationKey } from "./i18n/translate";

export type AnalysisDomainId =
  | "basic-exploration"
  | "mean-equivalence"
  | "proportions-categorical"
  | "correlation-regression-prediction"
  | "doe-optimization"
  | "ai-ml-experimental-design"
  | "quality-process-monitoring"
  | "measurement-variability";

export interface AnalysisPlannedWorkflow {
  descriptionKey: TranslationKey;
  id: string;
  labelKey: TranslationKey;
}

export type AnalysisContextualWorkflow = AnalysisPlannedWorkflow;

export interface AnalysisDomainFamily {
  contextualMethodIds?: readonly string[];
  contextualWorkflows?: readonly AnalysisContextualWorkflow[];
  descriptionKey: TranslationKey;
  id: string;
  labelKey: TranslationKey;
  methodIds: readonly string[];
  plannedWorkflows?: readonly AnalysisPlannedWorkflow[];
}

export interface AnalysisDomainDefinition {
  descriptionKey: TranslationKey;
  families: readonly AnalysisDomainFamily[];
  id: AnalysisDomainId;
  labelKey: TranslationKey;
  order: number;
}

export const ANALYSIS_DOMAINS: readonly AnalysisDomainDefinition[] = [
  {
    id: "basic-exploration",
    order: 1,
    labelKey: "analysisDomains.basic.label",
    descriptionKey: "analysisDomains.basic.description",
    families: [
      {
        id: "distribution-summary",
        labelKey: "analysisFamilies.distribution.label",
        descriptionKey: "analysisFamilies.distribution.description",
        methodIds: ["eda.descriptive", "eda.graphical_summary", "eda.normality"],
      },
      {
        id: "multivariate-exploration",
        labelKey: "analysisFamilies.multivariateExploration.label",
        descriptionKey: "analysisFamilies.multivariateExploration.description",
        methodIds: [],
        plannedWorkflows: [
          {
            id: "eda.multivariate_review",
            labelKey: "analysisPlanned.multivariateReview.label",
            descriptionKey: "analysisPlanned.multivariateReview.description",
          },
        ],
      },
    ],
  },
  {
    id: "mean-equivalence",
    order: 2,
    labelKey: "analysisDomains.mean.label",
    descriptionKey: "analysisDomains.mean.description",
    families: [
      {
        id: "t-tests",
        labelKey: "analysisFamilies.tTests.label",
        descriptionKey: "analysisFamilies.tTests.description",
        methodIds: [
          "hypothesis.one_sample_t",
          "hypothesis.paired_t",
          "hypothesis.two_sample_t",
        ],
        contextualWorkflows: [
          {
            id: "two-sample-comparison-guide",
            labelKey: "analysisContext.twoSampleGuide.label",
            descriptionKey: "analysisContext.twoSampleGuide.description",
          },
        ],
      },
      {
        id: "analysis-of-variance",
        labelKey: "analysisFamilies.anova.label",
        descriptionKey: "analysisFamilies.anova.description",
        methodIds: ["hypothesis.one_way_anova"],
      },
      {
        id: "equivalence-tests",
        labelKey: "analysisFamilies.equivalence.label",
        descriptionKey: "analysisFamilies.equivalence.description",
        methodIds: [
          "hypothesis.equivalence_tost",
          "hypothesis.paired_equivalence_tost",
          "hypothesis.two_sample_equivalence_tost",
        ],
      },
      {
        id: "comparability-assessment",
        labelKey: "analysisFamilies.comparability.label",
        descriptionKey: "analysisFamilies.comparability.description",
        methodIds: [],
        plannedWorkflows: [
          {
            id: "hypothesis.comparability_assessment",
            labelKey: "analysisPlanned.comparability.label",
            descriptionKey: "analysisPlanned.comparability.description",
          },
        ],
      },
      {
        id: "nonparametric-tests",
        labelKey: "analysisFamilies.nonparametric.label",
        descriptionKey: "analysisFamilies.nonparametric.description",
        methodIds: [
          "hypothesis.one_sample_wilcoxon",
          "hypothesis.mann_whitney",
          "hypothesis.kruskal_wallis",
        ],
      },
    ],
  },
  {
    id: "proportions-categorical",
    order: 3,
    labelKey: "analysisDomains.categorical.label",
    descriptionKey: "analysisDomains.categorical.description",
    families: [
      {
        id: "proportion-tests",
        labelKey: "analysisFamilies.proportions.label",
        descriptionKey: "analysisFamilies.proportions.description",
        methodIds: ["categorical.one_proportion", "categorical.two_proportion"],
      },
      {
        id: "categorical-association",
        labelKey: "analysisFamilies.association.label",
        descriptionKey: "analysisFamilies.association.description",
        methodIds: ["categorical.chi_square_association"],
      },
    ],
  },
  {
    id: "correlation-regression-prediction",
    order: 4,
    labelKey: "analysisDomains.regression.label",
    descriptionKey: "analysisDomains.regression.description",
    families: [
      {
        id: "correlation",
        labelKey: "analysisFamilies.correlation.label",
        descriptionKey: "analysisFamilies.correlation.description",
        methodIds: ["regression.pearson", "regression.xy_correlation"],
      },
      {
        id: "regression-modeling",
        labelKey: "analysisFamilies.regression.label",
        descriptionKey: "analysisFamilies.regression.description",
        methodIds: ["regression.linear_model"],
      },
      {
        id: "prediction-optimization",
        labelKey: "analysisFamilies.predictionOptimization.label",
        descriptionKey: "analysisFamilies.predictionOptimization.description",
        methodIds: [],
        contextualMethodIds: ["regression.predict"],
        contextualWorkflows: [
          {
            id: "regression.linear_model_optimizer",
            labelKey: "analysisContext.regressionOptimizer.label",
            descriptionKey: "analysisContext.regressionOptimizer.description",
          },
        ],
      },
      {
        id: "latent-variable-regression",
        labelKey: "analysisFamilies.latentRegression.label",
        descriptionKey: "analysisFamilies.latentRegression.description",
        methodIds: [],
        plannedWorkflows: [
          {
            id: "regression.partial_least_squares",
            labelKey: "analysisPlanned.pls.label",
            descriptionKey: "analysisPlanned.pls.description",
          },
        ],
      },
    ],
  },
  {
    id: "doe-optimization",
    order: 5,
    labelKey: "analysisDomains.doe.label",
    descriptionKey: "analysisDomains.doe.description",
    families: [
      {
        id: "factorial-designs",
        labelKey: "analysisFamilies.factorial.label",
        descriptionKey: "analysisFamilies.factorial.description",
        methodIds: ["doe.factorial_design"],
        contextualMethodIds: ["doe.general_factorial_design"],
      },
      {
        id: "response-surface",
        labelKey: "analysisFamilies.responseSurface.label",
        descriptionKey: "analysisFamilies.responseSurface.description",
        methodIds: ["doe.response_surface"],
      },
      {
        id: "response-optimization",
        labelKey: "analysisFamilies.responseOptimization.label",
        descriptionKey: "analysisFamilies.responseOptimization.description",
        methodIds: ["doe.response_optimizer"],
      },
    ],
  },
  {
    id: "ai-ml-experimental-design",
    order: 6,
    labelKey: "analysisDomains.ai.label",
    descriptionKey: "analysisDomains.ai.description",
    families: [
      {
        id: "space-filling-design",
        labelKey: "analysisFamilies.spaceFilling.label",
        descriptionKey: "analysisFamilies.spaceFilling.description",
        methodIds: ["doe.latin_hypercube"],
      },
      {
        id: "sequential-optimization",
        labelKey: "analysisFamilies.sequential.label",
        descriptionKey: "analysisFamilies.sequential.description",
        methodIds: ["doe.bayesian_optimization"],
      },
      {
        id: "surrogate-stage",
        labelKey: "analysisFamilies.surrogate.label",
        descriptionKey: "analysisFamilies.surrogate.description",
        methodIds: [],
        contextualWorkflows: [
          {
            id: "gaussian-process-surrogate",
            labelKey: "analysisContext.gaussianProcess.label",
            descriptionKey: "analysisContext.gaussianProcess.description",
          },
        ],
      },
    ],
  },
  {
    id: "quality-process-monitoring",
    order: 7,
    labelKey: "analysisDomains.quality.label",
    descriptionKey: "analysisDomains.quality.description",
    families: [
      {
        id: "control-charts",
        labelKey: "analysisFamilies.controlCharts.label",
        descriptionKey: "analysisFamilies.controlCharts.description",
        methodIds: [
          "quality.attribute_control_chart",
          "quality.subgroup_chart",
          "quality.individuals_chart",
        ],
      },
      {
        id: "process-behavior",
        labelKey: "analysisFamilies.processBehavior.label",
        descriptionKey: "analysisFamilies.processBehavior.description",
        methodIds: ["quality.run_chart"],
      },
      {
        id: "process-capability",
        labelKey: "analysisFamilies.capability.label",
        descriptionKey: "analysisFamilies.capability.description",
        methodIds: ["quality.capability"],
      },
      {
        id: "multivariate-monitoring",
        labelKey: "analysisFamilies.multivariateMonitoring.label",
        descriptionKey: "analysisFamilies.multivariateMonitoring.description",
        methodIds: [],
        plannedWorkflows: [
          {
            id: "quality.multivariate_monitoring",
            labelKey: "analysisPlanned.multivariateMonitoring.label",
            descriptionKey: "analysisPlanned.multivariateMonitoring.description",
          },
        ],
      },
    ],
  },
  {
    id: "measurement-variability",
    order: 8,
    labelKey: "analysisDomains.measurement.label",
    descriptionKey: "analysisDomains.measurement.description",
    families: [
      {
        id: "variance-comparison",
        labelKey: "analysisFamilies.variance.label",
        descriptionKey: "analysisFamilies.variance.description",
        methodIds: ["eda.equal_variances"],
        plannedWorkflows: [
          {
            id: "quality.two_variances",
            labelKey: "analysisPlanned.twoVariances.label",
            descriptionKey: "analysisPlanned.twoVariances.description",
          },
        ],
      },
      {
        id: "measurement-systems",
        labelKey: "analysisFamilies.measurementSystems.label",
        descriptionKey: "analysisFamilies.measurementSystems.description",
        methodIds: ["quality.gage_rr", "quality.gage_run_chart"],
      },
    ],
  },
] as const;
