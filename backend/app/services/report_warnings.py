"""Code-based report warning labels; unknown and contextual messages stay intact.

Coverage: hypothesis/categorical common warnings, standalone GP, and PCA.
This is a plain-text display boundary, not a payload translation mechanism.
Callers must escape this text and display the original warning code separately.
"""

from types import MappingProxyType

_TRANSLATIONS: dict[str, tuple[str, str]] = {
    "one_sample_t_design_assumption": (
        "독립성 및 표본 설계는 데이터만으로 자동 검증하지 않습니다.",
        "Independence and sampling design cannot be verified automatically from the data alone.",
    ),
    "one_sample_t_not_auto_switched": (
        "정규성 진단 결과로 1-표본 t-검정을 자동 전환하지 않습니다.",
        "The one-sample t-test is not switched automatically based on normality diagnostics.",
    ),
    "paired_t_design_assumption": (
        "각 행은 같은 subject/pair의 두 측정이라는 설계 가정을 사용자가 확인해야 합니다.",
        "Confirm that each row contains two measurements from the same subject or pair.",
    ),
    "paired_t_not_auto_switched": (
        "정규성 진단 결과로 대응표본 t-검정을 자동 전환하지 않습니다.",
        "The paired t-test is not switched automatically based on normality diagnostics.",
    ),
    "incomplete_pairs_excluded": (
        "한쪽 측정이 없는 incomplete pair는 complete-pair 정책으로 제외했습니다.",
        "Pairs missing either measurement were excluded under the complete-pair policy.",
    ),
    "non_numeric_pairs_excluded": (
        "두 측정 중 숫자로 해석할 수 없는 값이 있는 pair는 제외했습니다.",
        "Pairs containing a non-numeric measurement were excluded.",
    ),
    "missing_values_excluded": (
        "저장된 결측 처리 정책에 따라 행을 제외했습니다.",
        "Rows were excluded under the recorded missing-data policy.",
    ),
    "non_numeric_values_excluded": (
        "반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
        "Response values that could not be interpreted as numbers were excluded.",
    ),
    "equivalence_bounds_user_defined": (
        "동등성 한계는 분야 지식이나 허용 오차로 사용자가 사전에 지정해야 합니다.",
        "Specify equivalence bounds in advance using domain knowledge or an acceptable tolerance.",
    ),
    "equivalence_tost_design_assumption": (
        "TOST의 독립성 또는 짝지음 설계 가정을 확인해야 합니다.",
        "Confirm the independence or pairing assumptions appropriate to the stored TOST design.",
    ),
    "non_significance_is_not_equivalence": (
        "일반 차이검정의 비유의성은 동등성 근거가 아닙니다.",
        "A non-significant difference test is not evidence of equivalence.",
    ),
    "one_sample_wilcoxon_symmetry_assumption": (
        "차이값 분포의 대칭성은 설계/분포 가정이며 자동 검증하지 않습니다.",
        "Symmetry of the difference distribution is an assumption, not automatically verified.",
    ),
    "one_sample_wilcoxon_not_median_test": (
        "대칭성 가정 없이 1-표본 Wilcoxon을 단순 중앙값 검정으로 설명하지 않습니다.",
        "Without the symmetry assumption, "
        "the one-sample Wilcoxon test is not simply a median test.",
    ),
    "one_sample_wilcoxon_not_auto_switched": (
        "정규성 진단 결과로 1-표본 Wilcoxon을 자동 선택하지 않습니다.",
        "The one-sample Wilcoxon test is not selected automatically from normality diagnostics.",
    ),
    "zero_differences_detected": (
        "귀무 위치와 같은 값이 있어 zero difference 처리 방식을 함께 확인해야 합니다.",
        "Some differences from the null location are zero; review the zero-difference policy.",
    ),
    "signed_rank_ties_detected": (
        "절대 차이의 동점이 있어 p값 계산 방법과 순위 해석을 확인해야 합니다.",
        "Tied absolute differences require review of the P-value method and rank interpretation.",
    ),
    "one_sample_wilcoxon_auto_asymptotic_due_to_zeros_or_ties": (
        "auto 방식에서 영차이 또는 동점 때문에 점근 p값을 사용했습니다.",
        "Automatic calculation used an asymptotic P value because of zero differences or ties.",
    ),
    "small_nonzero_n": (
        "귀무 위치와 다른 관측값 수가 작아 p값 계산 방법과 설계를 확인해야 합니다.",
        "Few nonzero differences are available; review the P-value method and study design.",
    ),
    "two_sample_t_not_auto_switched": (
        "정규성/등분산 진단 결과로 2-표본 t-검정 방식을 자동 전환하지 않습니다.",
        "The two-sample t-test method is not switched automatically from diagnostic results.",
    ),
    "pooled_variance_assumption_selected": (
        "pooled Student 방식은 사용자가 명시적으로 선택한 경우에만 사용합니다.",
        "The pooled Student method is used only when explicitly selected by the user.",
    ),
    "constant_group": (
        "하나 이상의 그룹에서 반응 값이 모두 동일합니다.",
        "At least one group has a constant response.",
    ),
    "group_size_imbalance": (
        "그룹 크기 불균형이 큽니다. 설계와 영향점을 함께 확인하세요.",
        "Group sizes are substantially imbalanced; review the design and influential observations.",
    ),
    "small_group_size": (
        "그룹 표본 수가 작습니다. 해당 방법의 가정과 근사 정확도를 확인하세요.",
        "Group samples are small; review this method's assumptions and approximation accuracy.",
    ),
    "mann_whitney_not_median_test": (
        "Mann-Whitney U 결과를 단순 중앙값 차이 검정으로 해석하지 않습니다.",
        "The Mann-Whitney U result is not generally a test of median differences.",
    ),
    "mann_whitney_ties_detected": (
        "동률 값이 있어 p-value 방식과 rank 해석을 함께 확인해야 합니다.",
        "Ties are present; review the P-value method and rank interpretation.",
    ),
    "mann_whitney_auto_asymptotic_due_to_ties": (
        "auto 방식에서 동률 값 때문에 asymptotic p-value를 사용했습니다.",
        "Automatic calculation used an asymptotic P value because of ties.",
    ),
    "kruskal_wallis_not_median_test": (
        "Kruskal-Wallis 결과를 단순 중앙값 차이 검정으로 해석하지 않습니다.",
        "The Kruskal-Wallis result is not generally a test of median differences.",
    ),
    "dunn_holm_after_significant": (
        "overall 검정이 유의한 경우에만 Dunn 사후검정과 Holm 보정을 수행했습니다.",
        "Dunn post-hoc comparisons with Holm correction were run after a significant omnibus test.",
    ),
    "posthoc_skipped_overall_not_significant": (
        "전체 검정이 유의하지 않아 사후검정을 실행하지 않았습니다.",
        "Post-hoc comparisons were not run because the omnibus test was not significant.",
    ),
    "kruskal_wallis_ties_detected": (
        "동률 값이 있어 tie correction과 rank 해석을 함께 확인해야 합니다.",
        "Ties are present; review the tie correction and rank interpretation.",
    ),
    "one_way_anova_normality_assumption": (
        "잔차 정규성은 별도 진단과 설계 맥락으로 확인해야 합니다.",
        "Assess residual normality using separate diagnostics and the study-design context.",
    ),
    "one_way_anova_equal_variance_assumption": (
        "표준 일원분산분석은 등분산 가정을 사용합니다.",
        "Standard one-way ANOVA assumes equal variances.",
    ),
    "one_way_anova_unequal_variance_selected": (
        "그룹별 분산이 다를 수 있는 Welch 일원분산분석을 사용했습니다.",
        "Welch one-way ANOVA allows unequal group variances.",
    ),
    "one_way_anova_not_auto_switched": (
        "진단 결과만으로 Welch ANOVA나 비모수 검정으로 자동 전환하지 않습니다.",
        "Diagnostic results alone do not automatically switch to Welch ANOVA or a rank test.",
    ),
    "tukey_kramer_after_standard_anova": (
        "등분산 표준 ANOVA와 Tukey-Kramer 비교를 수행했습니다.",
        "Tukey-Kramer comparisons accompany the equal-variance standard ANOVA.",
    ),
    "two_group_anova_equivalent_to_t_test": (
        "그룹이 2개인 ANOVA는 표준 2표본 t-검정과 동등한 구조입니다.",
        "Standard ANOVA with two groups is equivalent to the standard two-sample t-test.",
    ),
    "one_proportion_binary_design_assumption": (
        "각 행이 독립적인 이진 사건/비사건 관측인지 확인해야 합니다.",
        "Confirm that rows represent independent binary event/non-event observations.",
    ),
    "two_proportion_binary_design_assumption": (
        "반응 컬럼이 이진 사건/비사건 관측인지 확인해야 합니다.",
        "Confirm that the response contains binary event/non-event observations.",
    ),
    "one_proportion_exact_binomial": (
        "p-value는 exact binomial test로 계산했습니다.",
        "The P value was calculated using the exact binomial test.",
    ),
    "event_level_not_observed": (
        "선택한 사건 수준이 사용 데이터에서 관측되지 않았습니다.",
        "The selected event level was not observed in the usable data.",
    ),
    "all_events_or_no_events": (
        "사용 데이터가 모두 사건 또는 모두 비사건입니다.",
        "The usable data contain either all events or no events.",
    ),
    "single_observed_level": (
        "사용 데이터에서 하나의 수준만 관측되었습니다.",
        "Only one level was observed in the usable data.",
    ),
    "two_proportion_fisher_exact": (
        "p-value는 2x2 Fisher exact test로 계산했습니다.",
        "The P value was calculated using the 2 by 2 Fisher exact test.",
    ),
    "small_expected_counts": (
        "기대 빈도가 작은 셀이 있습니다. 선택한 검정의 가정과 적합성을 확인하세요.",
        "Some expected counts are small; review the assumptions of the selected test.",
    ),
    "zero_cell_effect_ci_unavailable": (
        "0 cell이 있어 일부 효과크기 CI를 계산하지 않았습니다.",
        "Some effect-size confidence intervals are unavailable because of zero cells.",
    ),
    "pearson_chi_square_no_continuity_correction": (
        "Pearson 카이제곱 검정은 연속성 보정 없이 계산했습니다.",
        "The Pearson chi-square test was calculated without a continuity correction.",
    ),
    "two_by_two_table": (
        "2x2 교차표입니다. Fisher exact 검정 필요 여부를 함께 확인하세요.",
        "This is a 2 by 2 table; consider whether a Fisher exact test is appropriate.",
    ),
    "fisher_exact_recommended_for_sparse_2x2": (
        "희소한 2x2 교차표입니다. Fisher exact 검정은 권고이며 자동 실행하지 않았습니다.",
        "For this sparse 2 by 2 table, Fisher exact is a recommendation, not an executed test.",
    ),
    "large_contingency_table": (
        "교차표 셀 수가 많아 residual 해석과 표본 크기를 함께 확인하세요.",
        "The contingency table has many cells; consider sample size when interpreting residuals.",
    ),
    "gp_kernel_selection_not_external_validation": (
        "Kernel 선택에 사용한 CV 성능은 독립적인 외부 검증 성능이 아닙니다.",
        "The CV performance used to select the kernel is not independent external validation.",
    ),
    "gp_kernel_candidate_failed": (
        "일부 kernel 후보가 실패하여 선택 대상에서 제외되었습니다.",
        "Some kernel candidates failed and were excluded from selection.",
    ),
    "gp_predictive_not_causal": (
        "Gaussian Process 예측 관계는 관찰 데이터만으로 인과 효과를 의미하지 않습니다.",
        "A Gaussian Process predictive relationship does not imply causation "
        "from observational data.",
    ),
    "gp_nominal_only_signal": (
        "숫자형 예측변수가 없어 신호 진폭과 범주 일치 커널만 사용합니다. "
        "숫자형 kernel preset들은 이 모형에서 서로 다른 커널 계열을 뜻하지 않습니다.",
        "There are no numeric predictors: the signal uses amplitude and categorical "
        "equality only. Numeric kernel presets do not represent distinct kernel "
        "families for this model.",
    ),
    "gp_uncertainty_conditional_on_kernel": (
        "예측 불확실성은 선택한 kernel과 적합된 hyperparameter에 조건부입니다.",
        "Predictive uncertainty is conditional on the selected kernel and fitted hyperparameters.",
    ),
    "gp_not_converged": (
        "하나 이상의 Gaussian Process 적합이 안정적으로 수렴하지 않았습니다.",
        "At least one Gaussian Process fit did not converge reliably.",
    ),
    "gp_hyperparameter_near_bound": (
        "하나 이상의 kernel hyperparameter가 탐색 경계에 가깝습니다.",
        "At least one kernel hyperparameter is near its search bound.",
    ),
    "gp_amplitude_near_bound": (
        "신호 amplitude가 탐색 경계에 가깝습니다.",
        "The signal amplitude is near its search bound.",
    ),
    "gp_length_scale_near_bound": (
        "하나 이상의 ARD length scale이 탐색 경계에 가깝습니다.",
        "At least one ARD length scale is near its search bound.",
    ),
    "gp_noise_level_near_bound": (
        "추정 관측 noise가 탐색 경계에 가깝습니다.",
        "Estimated observation noise is near its search bound.",
    ),
    "gp_negative_cv_r_squared": (
        "교차검증 예측 R²가 음수입니다.",
        "The cross-validated predicted R-squared is negative.",
    ),
    "gp_interval_undercoverage": (
        "교차검증 95% 예측구간의 경험적 포함률이 낮습니다.",
        "Empirical coverage of the cross-validated 95% prediction intervals is low.",
    ),
    "gp_training_cv_gap": (
        "학습 성능과 교차검증 성능 차이가 큽니다.",
        "There is a large gap between training and cross-validation performance.",
    ),
    "pca_complete_case_rows_excluded": (
        "선택 변수에 결측 또는 비수치 값이 있는 행을 제외했습니다.",
        "Rows with missing or non-numeric selected values were excluded.",
    ),
    "pca_chart_points_limited": (
        "차트는 결정적인 제한 미리보기이며 계산에는 모든 사용 가능한 행을 사용합니다.",
        "Charts use a deterministic bounded preview; calculations use every usable row.",
    ),
    "pca_variables_not_less_than_rows": (
        "변수 수가 사용 행 수 이상이므로 일부 성분의 순위가 제한됩니다.",
        "The number of variables is not less than the usable row count; "
        "some components are rank limited.",
    ),
}
for _code in (
    "two_sample_t_independence_assumption",
    "mann_whitney_independence_assumption",
    "kruskal_wallis_independence_assumption",
    "one_way_anova_independence_assumption",
    "two_proportion_independence_assumption",
    "chi_square_independence_assumption",
):
    _TRANSLATIONS[_code] = (
        "독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
        "Independence is a design assumption and cannot be verified from the data alone.",
    )

REPORT_WARNING_TRANSLATIONS = MappingProxyType(_TRANSLATIONS)


def report_warning_text(code: str, message: str, locale: str = "ko") -> str:
    """Localize known semantics, without erasing unknown or contextual source text."""
    known = REPORT_WARNING_TRANSLATIONS.get(code)
    if known is None:
        return message or code
    translated = known[0 if locale == "ko" else 1]
    if not message or message == code or message in known:
        return translated
    original_label = "원문" if locale == "ko" else "Original message"
    return f"{translated} {original_label}: {message}"
