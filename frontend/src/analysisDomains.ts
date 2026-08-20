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
  presentation?: "card" | "notice";
  showInSidebar?: boolean;
}

export type AnalysisContextualWorkflow = AnalysisPlannedWorkflow;

export type AnalysisDomainLandingMode = "flat_methods" | "family_cards";
export type AnalysisDomainSidebarMode = "flat_methods" | "family_tree";
export type AnalysisFamilyLayout = "compact" | "wide" | "direct_single" | "planned";

export interface AnalysisDomainFamily {
  columnSpan?: 1 | 2;
  contextualMethodIds?: readonly string[];
  contextualWorkflows?: readonly AnalysisContextualWorkflow[];
  descriptionKey: TranslationKey;
  id: string;
  labelKey: TranslationKey;
  layout?: AnalysisFamilyLayout;
  methodIds: readonly string[];
  plannedWorkflows?: readonly AnalysisPlannedWorkflow[];
}

export interface AnalysisDomainDefinition {
  contextualSummaryKey?: TranslationKey;
  descriptionKey: TranslationKey;
  directContextualMethodIds?: readonly string[];
  directContextualWorkflows?: readonly AnalysisContextualWorkflow[];
  directMethodIds?: readonly string[];
  directPlannedWorkflows?: readonly AnalysisPlannedWorkflow[];
  families: readonly AnalysisDomainFamily[];
  id: AnalysisDomainId;
  labelKey: TranslationKey;
  landingMode: AnalysisDomainLandingMode;
  order: number;
  selectionGuideKeys?: readonly TranslationKey[];
  sidebarMode: AnalysisDomainSidebarMode;
}

export const ANALYSIS_DOMAINS: readonly AnalysisDomainDefinition[] = [
  {
    id: "basic-exploration",
    order: 1,
    landingMode: "flat_methods",
    sidebarMode: "flat_methods",
    labelKey: "analysisDomains.basic.label",
    descriptionKey: "analysisDomains.basic.description",
    directMethodIds: ["eda.descriptive", "eda.graphical_summary", "eda.normality"],
    directPlannedWorkflows: [
      {
        id: "eda.multivariate_review",
        labelKey: "analysisPlanned.multivariateReview.label",
        descriptionKey: "analysisPlanned.multivariateReview.description",
        showInSidebar: true,
      },
    ],
    families: [],
  },
  {
    id: "mean-equivalence",
    order: 2,
    landingMode: "family_cards",
    sidebarMode: "family_tree",
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
      },
      {
        id: "analysis-of-variance",
        labelKey: "analysisFamilies.anova.label",
        descriptionKey: "analysisFamilies.anova.description",
        methodIds: ["hypothesis.one_way_anova"],
        layout: "direct_single",
      },
      {
        id: "equivalence-tests",
        labelKey: "analysisFamilies.equivalence.label",
        descriptionKey: "analysisFamilies.equivalence.description",
        methodIds: [
          "hypothesis.equivalence_tost",
          "hypothesis.two_sample_equivalence_tost",
          "hypothesis.paired_equivalence_tost",
        ],
        columnSpan: 2,
        layout: "wide",
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
        columnSpan: 2,
        layout: "wide",
      },
      {
        id: "comparability-assessment",
        labelKey: "analysisFamilies.comparability.label",
        descriptionKey: "analysisFamilies.comparability.description",
        methodIds: [],
        layout: "planned",
        plannedWorkflows: [
          {
            id: "hypothesis.comparability_assessment",
            labelKey: "analysisPlanned.comparability.label",
            descriptionKey: "analysisPlanned.comparability.description",
            showInSidebar: true,
          },
        ],
      },
    ],
    selectionGuideKeys: [
      "analysisContext.twoSampleGuide.mean",
      "analysisContext.twoSampleGuide.rank",
      "analysisContext.twoSampleGuide.equivalence",
    ],
  },
  {
    id: "proportions-categorical",
    order: 3,
    landingMode: "family_cards",
    sidebarMode: "family_tree",
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
        layout: "direct_single",
      },
    ],
  },
  {
    id: "correlation-regression-prediction",
    order: 4,
    landingMode: "flat_methods",
    sidebarMode: "flat_methods",
    labelKey: "analysisDomains.regression.label",
    descriptionKey: "analysisDomains.regression.description",
    directMethodIds: [
      "regression.pearson",
      "regression.xy_correlation",
      "regression.linear_model",
    ],
    directContextualMethodIds: ["regression.predict"],
    directContextualWorkflows: [
      {
        id: "regression.linear_model_optimizer",
        labelKey: "analysisContext.regressionOptimizer.label",
        descriptionKey: "analysisContext.regressionOptimizer.description",
      },
    ],
    directPlannedWorkflows: [
      {
        id: "regression.partial_least_squares",
        labelKey: "analysisPlanned.pls.label",
        descriptionKey: "analysisPlanned.pls.description",
        showInSidebar: true,
      },
    ],
    contextualSummaryKey: "analysisContext.regressionModelActions",
    families: [],
  },
  {
    id: "doe-optimization",
    order: 5,
    landingMode: "flat_methods",
    sidebarMode: "flat_methods",
    labelKey: "analysisDomains.doe.label",
    descriptionKey: "analysisDomains.doe.description",
    directMethodIds: [
      "doe.factorial_design",
      "doe.general_factorial_design",
      "doe.response_surface",
      "doe.response_optimizer",
    ],
    families: [],
  },
  {
    id: "ai-ml-experimental-design",
    order: 6,
    landingMode: "flat_methods",
    sidebarMode: "flat_methods",
    labelKey: "analysisDomains.ai.label",
    descriptionKey: "analysisDomains.ai.description",
    directMethodIds: ["doe.latin_hypercube", "doe.bayesian_optimization"],
    directContextualWorkflows: [
      {
        id: "gaussian-process-surrogate",
        labelKey: "analysisContext.gaussianProcess.label",
        descriptionKey: "analysisContext.gaussianProcess.description",
        presentation: "card",
        showInSidebar: true,
      },
    ],
    families: [],
  },
  {
    id: "quality-process-monitoring",
    order: 7,
    landingMode: "family_cards",
    sidebarMode: "family_tree",
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
        layout: "direct_single",
      },
      {
        id: "process-capability",
        labelKey: "analysisFamilies.capability.label",
        descriptionKey: "analysisFamilies.capability.description",
        methodIds: ["quality.capability"],
        layout: "direct_single",
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
            showInSidebar: true,
          },
        ],
      },
    ],
  },
  {
    id: "measurement-variability",
    order: 8,
    landingMode: "family_cards",
    sidebarMode: "family_tree",
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
