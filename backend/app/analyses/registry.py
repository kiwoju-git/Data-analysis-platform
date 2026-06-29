from app.api.v1.schemas.analyses import (
    AnalysisExecutionMode,
    AnalysisMethodDescriptor,
    AnalysisMethodListResponse,
    AnalysisModuleDescriptor,
    AnalysisModuleId,
    MethodAvailability,
)

METHOD_VERSION = "0.1.0"

MODULES: tuple[AnalysisModuleDescriptor, ...] = (
    AnalysisModuleDescriptor(
        module_id=AnalysisModuleId.EXPLORATION,
        label_ko="탐색적 분석",
        label_en="Exploratory Analysis",
        order=10,
    ),
    AnalysisModuleDescriptor(
        module_id=AnalysisModuleId.HYPOTHESIS,
        label_ko="가설 검정",
        label_en="Hypothesis Tests",
        order=20,
    ),
    AnalysisModuleDescriptor(
        module_id=AnalysisModuleId.CATEGORICAL,
        label_ko="범주형 데이터 분석",
        label_en="Categorical Data Analysis",
        order=30,
    ),
    AnalysisModuleDescriptor(
        module_id=AnalysisModuleId.REGRESSION,
        label_ko="상관관계 및 회귀분석",
        label_en="Correlation And Regression",
        order=40,
    ),
    AnalysisModuleDescriptor(
        module_id=AnalysisModuleId.QUALITY,
        label_ko="품질 관리",
        label_en="Quality Control",
        order=50,
    ),
    AnalysisModuleDescriptor(
        module_id=AnalysisModuleId.DOE,
        label_ko="실험 계획법",
        label_en="Design Of Experiments",
        order=60,
    ),
)


def analysis_method_catalog() -> AnalysisMethodListResponse:
    module_order = {module.module_id: module.order for module in MODULES}
    return AnalysisMethodListResponse(
        modules=sorted(MODULES, key=lambda module: module.order),
        methods=sorted(METHODS, key=lambda method: (module_order[method.module_id], method.order)),
    )


def get_analysis_method(method_id: str) -> AnalysisMethodDescriptor | None:
    return METHOD_BY_ID.get(method_id)


def _planned(
    *,
    method_id: str,
    module_id: AnalysisModuleId,
    label_ko: str,
    label_en: str,
    order: int,
    requires_dataset: bool = True,
    disabled_reason: str = "아직 구현되지 않은 Gate의 계획된 메서드입니다.",
) -> AnalysisMethodDescriptor:
    return AnalysisMethodDescriptor(
        method_id=method_id,
        method_version=METHOD_VERSION,
        module_id=module_id,
        label_ko=label_ko,
        label_en=label_en,
        availability=MethodAvailability.PLANNED,
        execution_mode=AnalysisExecutionMode.INLINE,
        requires_dataset=requires_dataset,
        order=order,
        disabled_reason=disabled_reason,
    )


def _available(
    *,
    method_id: str,
    module_id: AnalysisModuleId,
    label_ko: str,
    label_en: str,
    order: int,
    requires_dataset: bool = True,
) -> AnalysisMethodDescriptor:
    return AnalysisMethodDescriptor(
        method_id=method_id,
        method_version=METHOD_VERSION,
        module_id=module_id,
        label_ko=label_ko,
        label_en=label_en,
        availability=MethodAvailability.AVAILABLE,
        execution_mode=AnalysisExecutionMode.INLINE,
        requires_dataset=requires_dataset,
        order=order,
        disabled_reason=None,
    )


def _disabled(
    *,
    method_id: str,
    module_id: AnalysisModuleId,
    label_ko: str,
    label_en: str,
    order: int,
    disabled_reason: str,
    requires_dataset: bool = True,
) -> AnalysisMethodDescriptor:
    return AnalysisMethodDescriptor(
        method_id=method_id,
        method_version=METHOD_VERSION,
        module_id=module_id,
        label_ko=label_ko,
        label_en=label_en,
        availability=MethodAvailability.DISABLED,
        execution_mode=AnalysisExecutionMode.INLINE,
        requires_dataset=requires_dataset,
        order=order,
        disabled_reason=disabled_reason,
    )


METHODS: tuple[AnalysisMethodDescriptor, ...] = (
    _available(
        method_id="eda.descriptive",
        module_id=AnalysisModuleId.EXPLORATION,
        label_ko="기술통계",
        label_en="Display Descriptive Statistics",
        order=10,
    ),
    _available(
        method_id="eda.graphical_summary",
        module_id=AnalysisModuleId.EXPLORATION,
        label_ko="그래프 요약",
        label_en="Graphical Summary",
        order=20,
    ),
    _available(
        method_id="eda.normality",
        module_id=AnalysisModuleId.EXPLORATION,
        label_ko="정규성 검정",
        label_en="Normality Test",
        order=30,
    ),
    _planned(
        method_id="eda.equal_variances",
        module_id=AnalysisModuleId.EXPLORATION,
        label_ko="등분산 검정",
        label_en="Test for Equal Variances",
        order=40,
        disabled_reason=(
            "SciPy 기반 Levene/Brown-Forsythe 호환성 검증과 기준 fixture가 완료된 뒤 "
            "실행할 수 있습니다."
        ),
    ),
    _planned(
        method_id="hypothesis.one_sample_t",
        module_id=AnalysisModuleId.HYPOTHESIS,
        label_ko="1-표본 t-검정",
        label_en="1-Sample t-Test",
        order=10,
    ),
    _planned(
        method_id="hypothesis.paired_t",
        module_id=AnalysisModuleId.HYPOTHESIS,
        label_ko="대응표본 t-검정",
        label_en="Paired t-Test",
        order=20,
    ),
    _planned(
        method_id="hypothesis.two_sample_t",
        module_id=AnalysisModuleId.HYPOTHESIS,
        label_ko="2-표본 t-검정",
        label_en="2-Sample t-Test",
        order=30,
    ),
    _planned(
        method_id="hypothesis.one_way_anova",
        module_id=AnalysisModuleId.HYPOTHESIS,
        label_ko="일원분산분석",
        label_en="One-Way ANOVA",
        order=40,
    ),
    _planned(
        method_id="hypothesis.equivalence_tost",
        module_id=AnalysisModuleId.HYPOTHESIS,
        label_ko="동등성 검정",
        label_en="Equivalence Test (TOST)",
        order=50,
    ),
    _planned(
        method_id="hypothesis.one_sample_wilcoxon",
        module_id=AnalysisModuleId.HYPOTHESIS,
        label_ko="1-표본 Wilcoxon",
        label_en="1-Sample Wilcoxon Signed-Rank",
        order=60,
    ),
    _planned(
        method_id="hypothesis.mann_whitney",
        module_id=AnalysisModuleId.HYPOTHESIS,
        label_ko="Mann-Whitney U",
        label_en="Mann-Whitney U",
        order=70,
    ),
    _planned(
        method_id="hypothesis.kruskal_wallis",
        module_id=AnalysisModuleId.HYPOTHESIS,
        label_ko="Kruskal-Wallis",
        label_en="Kruskal-Wallis",
        order=80,
    ),
    _planned(
        method_id="categorical.one_proportion",
        module_id=AnalysisModuleId.CATEGORICAL,
        label_ko="1-비율",
        label_en="1-Proportion",
        order=10,
    ),
    _planned(
        method_id="categorical.two_proportion",
        module_id=AnalysisModuleId.CATEGORICAL,
        label_ko="2-비율",
        label_en="2-Proportion",
        order=20,
    ),
    _planned(
        method_id="categorical.chi_square_association",
        module_id=AnalysisModuleId.CATEGORICAL,
        label_ko="카이제곱 독립성 검정",
        label_en="Chi-square Test for Association",
        order=30,
    ),
    _planned(
        method_id="regression.pearson",
        module_id=AnalysisModuleId.REGRESSION,
        label_ko="Pearson 상관",
        label_en="Pearson Correlation",
        order=10,
    ),
    _planned(
        method_id="regression.xy_correlation",
        module_id=AnalysisModuleId.REGRESSION,
        label_ko="X-Y 상관행렬",
        label_en="X-Y Correlation",
        order=20,
    ),
    _planned(
        method_id="regression.linear_model",
        module_id=AnalysisModuleId.REGRESSION,
        label_ko="회귀모형 적합",
        label_en="Fit Regression Model",
        order=30,
    ),
    _disabled(
        method_id="regression.predict",
        module_id=AnalysisModuleId.REGRESSION,
        label_ko="예측",
        label_en="Predict",
        order=40,
        disabled_reason="앱이 생성한 회귀 모델 manifest가 구현된 뒤 활성화됩니다.",
    ),
    _disabled(
        method_id="regression.response_optimizer",
        module_id=AnalysisModuleId.REGRESSION,
        label_ko="반응 최적화",
        label_en="Response Optimizer",
        order=50,
        disabled_reason="검증된 회귀 또는 DOE 반응표면 모델이 필요합니다.",
    ),
    _planned(
        method_id="quality.attribute_control_chart",
        module_id=AnalysisModuleId.QUALITY,
        label_ko="계수형 관리도",
        label_en="Control Chart",
        order=10,
    ),
    _planned(
        method_id="quality.individuals_chart",
        module_id=AnalysisModuleId.QUALITY,
        label_ko="개별값 관리도",
        label_en="Variables Charts for Individuals",
        order=20,
    ),
    _planned(
        method_id="quality.subgroup_chart",
        module_id=AnalysisModuleId.QUALITY,
        label_ko="부분군 관리도",
        label_en="Variables Charts for Subgroups",
        order=30,
    ),
    _planned(
        method_id="quality.run_chart",
        module_id=AnalysisModuleId.QUALITY,
        label_ko="런 차트",
        label_en="Run Chart",
        order=40,
    ),
    _planned(
        method_id="quality.capability",
        module_id=AnalysisModuleId.QUALITY,
        label_ko="공정능력 분석",
        label_en="Capability Analysis",
        order=50,
    ),
    _planned(
        method_id="quality.gage_rr",
        module_id=AnalysisModuleId.QUALITY,
        label_ko="Gage R&R",
        label_en="Gage R&R Study",
        order=60,
    ),
    _planned(
        method_id="quality.gage_run_chart",
        module_id=AnalysisModuleId.QUALITY,
        label_ko="Gage Run Chart",
        label_en="Gage Run Chart",
        order=70,
    ),
    _planned(
        method_id="doe.factorial_design",
        module_id=AnalysisModuleId.DOE,
        label_ko="실험 계획 생성",
        label_en="Design of Experiments",
        order=10,
        requires_dataset=False,
    ),
    _planned(
        method_id="doe.response_surface",
        module_id=AnalysisModuleId.DOE,
        label_ko="반응표면법",
        label_en="Response Surface Method",
        order=20,
        requires_dataset=False,
    ),
)

METHOD_BY_ID = {method.method_id: method for method in METHODS}
