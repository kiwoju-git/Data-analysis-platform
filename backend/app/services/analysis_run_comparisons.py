from uuid import UUID

from fastapi import status

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunComparisonCompatibility,
    AnalysisRunComparisonDifference,
    AnalysisRunComparisonResponse,
    AnalysisRunComparisonSideResponse,
    AnalysisRunMethodSpecificComparison,
    DescriptiveColumnComparison,
    DescriptiveMetricComparison,
    DescriptiveStatisticsComparison,
    EquivalenceTostComparison,
    EquivalenceTostMetricComparison,
    EquivalenceTostSettingComparison,
    KruskalWallisComparison,
    KruskalWallisMetricComparison,
    KruskalWallisSettingComparison,
    OneSampleTMetricComparison,
    OneSampleTSettingComparison,
    OneSampleTTestComparison,
    OneWayAnovaComparison,
    OneWayAnovaMetricComparison,
    OneWayAnovaSettingComparison,
    PairedTMetricComparison,
    PairedTSettingComparison,
    PairedTTestComparison,
    TwoSampleTMetricComparison,
    TwoSampleTSettingComparison,
    TwoSampleTTestComparison,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_results import StoredAnalysisRunResult, load_analysis_run_result


def compare_analysis_runs(
    settings: Settings,
    left_analysis_id: UUID,
    right_analysis_id: UUID,
) -> AnalysisRunComparisonResponse:
    if left_analysis_id == right_analysis_id:
        raise ApiError(
            code="analysis_comparison_requires_two_runs",
            message="서로 다른 두 분석 실행을 선택해야 합니다.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    left = load_analysis_run_result(settings, left_analysis_id)
    right = load_analysis_run_result(settings, right_analysis_id)
    left_side = _to_comparison_side(left)
    right_side = _to_comparison_side(right)
    compatibility = AnalysisRunComparisonCompatibility(
        same_method_id=left_side.method_id == right_side.method_id,
        same_method_version=left_side.method_version == right_side.method_version,
        same_dataset_version_id=left_side.dataset_version_id == right_side.dataset_version_id,
        same_summary_type=left_side.summary_type == right_side.summary_type,
    )
    comparable = (
        compatibility.same_method_id
        and compatibility.same_method_version
        and compatibility.same_summary_type
    )
    return AnalysisRunComparisonResponse(
        left=left_side,
        right=right_side,
        comparable=comparable,
        compatibility=compatibility,
        differences=_comparison_differences(left_side, right_side),
        method_specific=_method_specific_comparison(left, right, comparable=comparable),
    )


def _to_comparison_side(
    stored: StoredAnalysisRunResult,
) -> AnalysisRunComparisonSideResponse:
    envelope = stored.envelope
    record = stored.record
    return AnalysisRunComparisonSideResponse(
        analysis_id=envelope.analysis_id,
        method_id=envelope.method_id,
        method_version=envelope.method_version,
        dataset_version_id=envelope.dataset_version_id,
        status=envelope.status,
        stale=record.stale,
        result_sha256=record.result_sha256 or "",
        warning_count=len(envelope.warnings),
        summary_type=_analysis_result_summary_type(envelope),
        row_count_total=envelope.provenance.row_count_total,
        row_count_included=envelope.provenance.row_count_included,
        source_schema_hash=envelope.provenance.source_schema_hash,
        filter_snapshot_sha256=envelope.provenance.filter_snapshot_sha256,
        row_snapshot_sha256=envelope.provenance.row_snapshot_sha256,
        created_at=record.created_at,
        completed_at=record.completed_at,
    )


def _analysis_result_summary_type(envelope: AnalysisResultEnvelope) -> str | None:
    if isinstance(envelope.result, dict):
        summary_type = envelope.result.get("summary_type")
        if isinstance(summary_type, str):
            return summary_type
    return None


def _comparison_differences(
    left: AnalysisRunComparisonSideResponse,
    right: AnalysisRunComparisonSideResponse,
) -> list[AnalysisRunComparisonDifference]:
    fields = (
        "method_id",
        "method_version",
        "dataset_version_id",
        "status",
        "stale",
        "result_sha256",
        "warning_count",
        "summary_type",
        "row_count_total",
        "row_count_included",
        "source_schema_hash",
        "filter_snapshot_sha256",
        "row_snapshot_sha256",
    )
    differences: list[AnalysisRunComparisonDifference] = []
    for field in fields:
        left_value = getattr(left, field)
        right_value = getattr(right, field)
        if left_value == right_value:
            continue
        differences.append(
            AnalysisRunComparisonDifference(
                field=field,
                left=_comparison_value(left_value),
                right=_comparison_value(right_value),
            ),
        )
    return differences


def _method_specific_comparison(
    left: StoredAnalysisRunResult,
    right: StoredAnalysisRunResult,
    *,
    comparable: bool,
) -> AnalysisRunMethodSpecificComparison | None:
    if not comparable:
        return None
    if (
        left.envelope.method_id == "eda.descriptive"
        and right.envelope.method_id == "eda.descriptive"
        and _analysis_result_summary_type(left.envelope) == "descriptive_statistics"
        and _analysis_result_summary_type(right.envelope) == "descriptive_statistics"
    ):
        descriptive = _descriptive_statistics_comparison(left.envelope, right.envelope)
        if descriptive is not None:
            return AnalysisRunMethodSpecificComparison(
                descriptive_statistics=descriptive,
            )
    if (
        left.envelope.method_id == "hypothesis.one_sample_t"
        and right.envelope.method_id == "hypothesis.one_sample_t"
        and _analysis_result_summary_type(left.envelope) == "one_sample_t_test"
        and _analysis_result_summary_type(right.envelope) == "one_sample_t_test"
    ):
        one_sample_t = _one_sample_t_test_comparison(left.envelope, right.envelope)
        if one_sample_t is not None:
            return AnalysisRunMethodSpecificComparison(
                one_sample_t_test=one_sample_t,
            )
    if (
        left.envelope.method_id == "hypothesis.two_sample_t"
        and right.envelope.method_id == "hypothesis.two_sample_t"
        and _analysis_result_summary_type(left.envelope) == "two_sample_t_test"
        and _analysis_result_summary_type(right.envelope) == "two_sample_t_test"
    ):
        two_sample_t = _two_sample_t_test_comparison(left.envelope, right.envelope)
        if two_sample_t is not None:
            return AnalysisRunMethodSpecificComparison(
                two_sample_t_test=two_sample_t,
            )
    if (
        left.envelope.method_id == "hypothesis.paired_t"
        and right.envelope.method_id == "hypothesis.paired_t"
        and _analysis_result_summary_type(left.envelope) == "paired_t_test"
        and _analysis_result_summary_type(right.envelope) == "paired_t_test"
    ):
        paired_t = _paired_t_test_comparison(left.envelope, right.envelope)
        if paired_t is not None:
            return AnalysisRunMethodSpecificComparison(
                paired_t_test=paired_t,
            )
    if (
        left.envelope.method_id == "hypothesis.equivalence_tost"
        and right.envelope.method_id == "hypothesis.equivalence_tost"
        and _analysis_result_summary_type(left.envelope) == "equivalence_tost"
        and _analysis_result_summary_type(right.envelope) == "equivalence_tost"
    ):
        equivalence_tost = _equivalence_tost_comparison(left.envelope, right.envelope)
        if equivalence_tost is not None:
            return AnalysisRunMethodSpecificComparison(
                equivalence_tost=equivalence_tost,
            )
    if (
        left.envelope.method_id == "hypothesis.one_way_anova"
        and right.envelope.method_id == "hypothesis.one_way_anova"
        and _analysis_result_summary_type(left.envelope) == "one_way_anova"
        and _analysis_result_summary_type(right.envelope) == "one_way_anova"
    ):
        one_way_anova = _one_way_anova_comparison(left.envelope, right.envelope)
        if one_way_anova is not None:
            return AnalysisRunMethodSpecificComparison(
                one_way_anova=one_way_anova,
            )
    if (
        left.envelope.method_id == "hypothesis.kruskal_wallis"
        and right.envelope.method_id == "hypothesis.kruskal_wallis"
        and _analysis_result_summary_type(left.envelope) == "kruskal_wallis_test"
        and _analysis_result_summary_type(right.envelope) == "kruskal_wallis_test"
    ):
        kruskal_wallis = _kruskal_wallis_comparison(left.envelope, right.envelope)
        if kruskal_wallis is not None:
            return AnalysisRunMethodSpecificComparison(
                kruskal_wallis=kruskal_wallis,
            )
    return None


def _descriptive_statistics_comparison(
    left: AnalysisResultEnvelope,
    right: AnalysisResultEnvelope,
) -> DescriptiveStatisticsComparison | None:
    left_columns = _descriptive_columns_by_id(left)
    right_columns = _descriptive_columns_by_id(right)
    if not left_columns and not right_columns:
        return None

    common_column_ids = sorted(set(left_columns).intersection(right_columns))
    return DescriptiveStatisticsComparison(
        summary_type="descriptive_statistics",
        columns=[
            _descriptive_column_comparison(
                column_id,
                left_columns[column_id],
                right_columns[column_id],
            )
            for column_id in common_column_ids
        ],
        left_only_column_ids=sorted(set(left_columns).difference(right_columns)),
        right_only_column_ids=sorted(set(right_columns).difference(left_columns)),
    )


def _descriptive_columns_by_id(
    envelope: AnalysisResultEnvelope,
) -> dict[str, dict[str, object]]:
    if not isinstance(envelope.result, dict):
        return {}
    columns = envelope.result.get("columns")
    if not isinstance(columns, list):
        return {}

    by_id: dict[str, dict[str, object]] = {}
    for column in columns:
        if not isinstance(column, dict):
            continue
        column_id = column.get("column_id")
        if isinstance(column_id, str) and column_id not in by_id:
            by_id[column_id] = {str(key): value for key, value in column.items()}
    return by_id


def _descriptive_column_comparison(
    column_id: str,
    left: dict[str, object],
    right: dict[str, object],
) -> DescriptiveColumnComparison:
    return DescriptiveColumnComparison(
        column_id=column_id,
        display_name=_descriptive_display_name(left, right, column_id),
        metrics=[
            _descriptive_metric_comparison(metric, left.get(metric), right.get(metric))
            for metric in (
                "n_total",
                "n_used",
                "n_missing",
                "n_non_numeric",
                "mean",
                "std",
                "min",
                "q1",
                "median",
                "q3",
                "max",
            )
        ],
    )


def _descriptive_display_name(
    left: dict[str, object],
    right: dict[str, object],
    fallback: str,
) -> str:
    left_name = left.get("display_name")
    if isinstance(left_name, str):
        return left_name
    right_name = right.get("display_name")
    if isinstance(right_name, str):
        return right_name
    return fallback


def _descriptive_metric_comparison(
    metric: str,
    left: object,
    right: object,
) -> DescriptiveMetricComparison:
    left_value = _comparison_number(left)
    right_value = _comparison_number(right)
    delta = None
    if left_value is not None and right_value is not None:
        delta = float(right_value) - float(left_value)
    return DescriptiveMetricComparison(
        metric=metric,
        left=left_value,
        right=right_value,
        delta=delta,
    )


def _one_sample_t_test_comparison(
    left: AnalysisResultEnvelope,
    right: AnalysisResultEnvelope,
) -> OneSampleTTestComparison | None:
    if not isinstance(left.result, dict) or not isinstance(right.result, dict):
        return None

    left_response = _comparison_mapping(left.result.get("response"))
    right_response = _comparison_mapping(right.result.get("response"))
    left_response_column_id = _comparison_string(left_response.get("column_id"))
    right_response_column_id = _comparison_string(right_response.get("column_id"))
    return OneSampleTTestComparison(
        summary_type="one_sample_t_test",
        left_response_column_id=left_response_column_id,
        right_response_column_id=right_response_column_id,
        response_display_name=_one_sample_t_response_display_name(
            left_response,
            right_response,
        ),
        same_response_column=left_response_column_id == right_response_column_id,
        settings=[
            _one_sample_t_setting_comparison(setting, left.result, right.result)
            for setting in (
                "alternative",
                "alpha",
                "confidence_level",
                "null_mean",
                "missing_policy",
            )
        ],
        metrics=[
            _one_sample_t_metric_comparison(metric, left.result, right.result)
            for metric in (
                "n_total",
                "n_used",
                "n_missing",
                "n_non_numeric",
                "sample.n",
                "sample.mean",
                "sample.std",
                "sample.median",
                "sample.min",
                "sample.max",
                "contrast.estimate",
                "contrast.standard_error",
                "contrast.df",
                "contrast.statistic",
                "contrast.p_value",
                "contrast.confidence_interval.lower",
                "contrast.confidence_interval.upper",
                "contrast.effect_size.cohen_dz",
                "contrast.effect_size.hedges_g",
            )
        ],
    )


def _comparison_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _comparison_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _one_sample_t_response_display_name(
    left: dict[str, object],
    right: dict[str, object],
) -> str | None:
    left_name = _comparison_string(left.get("display_name"))
    if left_name is not None:
        return left_name
    return _comparison_string(right.get("display_name"))


def _one_sample_t_setting_comparison(
    setting: str,
    left: dict[str, object],
    right: dict[str, object],
) -> OneSampleTSettingComparison:
    left_value = _comparison_scalar(left.get(setting))
    right_value = _comparison_scalar(right.get(setting))
    return OneSampleTSettingComparison(
        setting=setting,
        left=left_value,
        right=right_value,
        same=left_value == right_value,
    )


def _one_sample_t_metric_comparison(
    metric: str,
    left: dict[str, object],
    right: dict[str, object],
) -> OneSampleTMetricComparison:
    left_value = _comparison_number(_comparison_path_value(left, metric.split(".")))
    right_value = _comparison_number(_comparison_path_value(right, metric.split(".")))
    delta = None
    if left_value is not None and right_value is not None:
        delta = float(right_value) - float(left_value)
    return OneSampleTMetricComparison(
        metric=metric,
        left=left_value,
        right=right_value,
        delta=delta,
    )


def _two_sample_t_test_comparison(
    left: AnalysisResultEnvelope,
    right: AnalysisResultEnvelope,
) -> TwoSampleTTestComparison | None:
    if not isinstance(left.result, dict) or not isinstance(right.result, dict):
        return None

    left_response = _comparison_mapping(left.result.get("response"))
    right_response = _comparison_mapping(right.result.get("response"))
    left_group = _comparison_mapping(left.result.get("group"))
    right_group = _comparison_mapping(right.result.get("group"))
    left_response_column_id = _comparison_string(left_response.get("column_id"))
    right_response_column_id = _comparison_string(right_response.get("column_id"))
    left_group_column_id = _comparison_string(left_group.get("column_id"))
    right_group_column_id = _comparison_string(right_group.get("column_id"))
    left_group_labels = _two_sample_t_group_labels(left.result)
    right_group_labels = _two_sample_t_group_labels(right.result)
    return TwoSampleTTestComparison(
        summary_type="two_sample_t_test",
        left_response_column_id=left_response_column_id,
        right_response_column_id=right_response_column_id,
        response_display_name=_comparison_display_name(
            left_response,
            right_response,
        ),
        same_response_column=left_response_column_id == right_response_column_id,
        left_group_column_id=left_group_column_id,
        right_group_column_id=right_group_column_id,
        group_display_name=_comparison_display_name(left_group, right_group),
        same_group_column=left_group_column_id == right_group_column_id,
        same_group_label_set=set(left_group_labels) == set(right_group_labels),
        same_group_label_order=left_group_labels == right_group_labels,
        settings=[
            _two_sample_t_setting_comparison(setting, left.result, right.result)
            for setting in (
                "alternative",
                "alpha",
                "confidence_level",
                "variance_assumption",
                "null_difference",
                "missing_policy",
            )
        ],
        metrics=[
            _two_sample_t_metric_comparison(metric, left.result, right.result)
            for metric in (
                "n_total",
                "n_used",
                "n_excluded_missing_response",
                "n_excluded_missing_group",
                "n_excluded_non_numeric_response",
                "group_count",
                "groups.0.n",
                "groups.0.mean",
                "groups.0.std",
                "groups.1.n",
                "groups.1.mean",
                "groups.1.std",
                "contrast.estimate",
                "contrast.standard_error",
                "contrast.df",
                "contrast.statistic",
                "contrast.p_value",
                "contrast.confidence_interval.lower",
                "contrast.confidence_interval.upper",
                "contrast.effect_size.cohen_d",
                "contrast.effect_size.hedges_g",
            )
        ],
    )


def _comparison_display_name(
    left: dict[str, object],
    right: dict[str, object],
) -> str | None:
    left_name = _comparison_string(left.get("display_name"))
    if left_name is not None:
        return left_name
    return _comparison_string(right.get("display_name"))


def _two_sample_t_group_labels(result: dict[str, object]) -> list[str]:
    groups = result.get("groups")
    if not isinstance(groups, list):
        return []
    labels: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        label = group.get("group_label")
        if isinstance(label, str):
            labels.append(label)
    return labels


def _two_sample_t_setting_comparison(
    setting: str,
    left: dict[str, object],
    right: dict[str, object],
) -> TwoSampleTSettingComparison:
    left_value = _comparison_scalar(left.get(setting))
    right_value = _comparison_scalar(right.get(setting))
    return TwoSampleTSettingComparison(
        setting=setting,
        left=left_value,
        right=right_value,
        same=left_value == right_value,
    )


def _two_sample_t_metric_comparison(
    metric: str,
    left: dict[str, object],
    right: dict[str, object],
) -> TwoSampleTMetricComparison:
    left_value = _comparison_number(_comparison_path_value(left, metric.split(".")))
    right_value = _comparison_number(_comparison_path_value(right, metric.split(".")))
    delta = None
    if left_value is not None and right_value is not None:
        delta = float(right_value) - float(left_value)
    return TwoSampleTMetricComparison(
        metric=metric,
        left=left_value,
        right=right_value,
        delta=delta,
    )


def _paired_t_test_comparison(
    left: AnalysisResultEnvelope,
    right: AnalysisResultEnvelope,
) -> PairedTTestComparison | None:
    if not isinstance(left.result, dict) or not isinstance(right.result, dict):
        return None

    left_before = _comparison_mapping(left.result.get("before"))
    right_before = _comparison_mapping(right.result.get("before"))
    left_after = _comparison_mapping(left.result.get("after"))
    right_after = _comparison_mapping(right.result.get("after"))
    left_before_column_id = _comparison_string(left_before.get("column_id"))
    right_before_column_id = _comparison_string(right_before.get("column_id"))
    left_after_column_id = _comparison_string(left_after.get("column_id"))
    right_after_column_id = _comparison_string(right_after.get("column_id"))
    return PairedTTestComparison(
        summary_type="paired_t_test",
        left_before_column_id=left_before_column_id,
        right_before_column_id=right_before_column_id,
        before_display_name=_comparison_display_name(left_before, right_before),
        same_before_column=left_before_column_id == right_before_column_id,
        left_after_column_id=left_after_column_id,
        right_after_column_id=right_after_column_id,
        after_display_name=_comparison_display_name(left_after, right_after),
        same_after_column=left_after_column_id == right_after_column_id,
        settings=[
            _paired_t_setting_comparison(setting, left.result, right.result)
            for setting in (
                "alternative",
                "alpha",
                "confidence_level",
                "null_difference",
                "missing_policy",
                "difference_definition",
            )
        ],
        metrics=[
            _paired_t_metric_comparison(metric, left.result, right.result)
            for metric in (
                "n_total",
                "n_used",
                "n_incomplete_pairs",
                "n_missing_before",
                "n_missing_after",
                "n_non_numeric_pairs",
                "n_non_numeric_before",
                "n_non_numeric_after",
                "paired_sample.n",
                "paired_sample.before_mean",
                "paired_sample.after_mean",
                "paired_sample.mean_difference",
                "paired_sample.median_difference",
                "paired_sample.difference_std",
                "paired_sample.min_difference",
                "paired_sample.max_difference",
                "paired_sample.positive_difference_count",
                "paired_sample.negative_difference_count",
                "paired_sample.zero_difference_count",
                "contrast.estimate",
                "contrast.standard_error",
                "contrast.df",
                "contrast.statistic",
                "contrast.p_value",
                "contrast.confidence_interval.lower",
                "contrast.confidence_interval.upper",
                "contrast.effect_size.cohen_dz",
                "contrast.effect_size.hedges_g",
            )
        ],
    )


def _paired_t_setting_comparison(
    setting: str,
    left: dict[str, object],
    right: dict[str, object],
) -> PairedTSettingComparison:
    left_value = _comparison_scalar(left.get(setting))
    right_value = _comparison_scalar(right.get(setting))
    return PairedTSettingComparison(
        setting=setting,
        left=left_value,
        right=right_value,
        same=left_value == right_value,
    )


def _paired_t_metric_comparison(
    metric: str,
    left: dict[str, object],
    right: dict[str, object],
) -> PairedTMetricComparison:
    left_value = _comparison_number(_comparison_path_value(left, metric.split(".")))
    right_value = _comparison_number(_comparison_path_value(right, metric.split(".")))
    delta = None
    if left_value is not None and right_value is not None:
        delta = float(right_value) - float(left_value)
    return PairedTMetricComparison(
        metric=metric,
        left=left_value,
        right=right_value,
        delta=delta,
    )


def _equivalence_tost_comparison(
    left: AnalysisResultEnvelope,
    right: AnalysisResultEnvelope,
) -> EquivalenceTostComparison | None:
    if not isinstance(left.result, dict) or not isinstance(right.result, dict):
        return None

    left_response = _comparison_mapping(left.result.get("response"))
    right_response = _comparison_mapping(right.result.get("response"))
    left_response_column_id = _comparison_string(left_response.get("column_id"))
    right_response_column_id = _comparison_string(right_response.get("column_id"))
    return EquivalenceTostComparison(
        summary_type="equivalence_tost",
        left_response_column_id=left_response_column_id,
        right_response_column_id=right_response_column_id,
        response_display_name=_comparison_display_name(
            left_response,
            right_response,
        ),
        same_response_column=left_response_column_id == right_response_column_id,
        settings=[
            _equivalence_tost_setting_comparison(setting, left.result, right.result)
            for setting in (
                "design",
                "input_mode",
                "alpha",
                "confidence_level",
                "reference_mean",
                "missing_policy",
                "equivalence_bounds.lower",
                "equivalence_bounds.upper",
                "equivalence_bounds.scale",
                "equivalence_bounds.estimate_definition",
                "tests.lower.reject_null",
                "tests.upper.reject_null",
                "tost.equivalent",
                "tost.ci_inside_equivalence_bounds",
            )
        ],
        metrics=[
            _equivalence_tost_metric_comparison(metric, left.result, right.result)
            for metric in (
                "n_total",
                "n_used",
                "n_missing",
                "n_non_numeric",
                "sample.n",
                "sample.mean",
                "sample.std",
                "estimate.value",
                "estimate.standard_error",
                "estimate.df",
                "tests.lower.statistic",
                "tests.lower.p_value",
                "tests.upper.statistic",
                "tests.upper.p_value",
                "tost.p_value",
                "confidence_interval.lower",
                "confidence_interval.upper",
                "effect_size.cohen_dz",
                "effect_size.hedges_g",
            )
        ],
    )


def _equivalence_tost_setting_comparison(
    setting: str,
    left: dict[str, object],
    right: dict[str, object],
) -> EquivalenceTostSettingComparison:
    left_value = _comparison_scalar(_comparison_path_value(left, setting.split(".")))
    right_value = _comparison_scalar(_comparison_path_value(right, setting.split(".")))
    return EquivalenceTostSettingComparison(
        setting=setting,
        left=left_value,
        right=right_value,
        same=left_value == right_value,
    )


def _equivalence_tost_metric_comparison(
    metric: str,
    left: dict[str, object],
    right: dict[str, object],
) -> EquivalenceTostMetricComparison:
    left_value = _comparison_number(_comparison_path_value(left, metric.split(".")))
    right_value = _comparison_number(_comparison_path_value(right, metric.split(".")))
    delta = None
    if left_value is not None and right_value is not None:
        delta = float(right_value) - float(left_value)
    return EquivalenceTostMetricComparison(
        metric=metric,
        left=left_value,
        right=right_value,
        delta=delta,
    )


def _one_way_anova_comparison(
    left: AnalysisResultEnvelope,
    right: AnalysisResultEnvelope,
) -> OneWayAnovaComparison | None:
    if not isinstance(left.result, dict) or not isinstance(right.result, dict):
        return None

    left_response = _comparison_mapping(left.result.get("response"))
    right_response = _comparison_mapping(right.result.get("response"))
    left_group = _comparison_mapping(left.result.get("group"))
    right_group = _comparison_mapping(right.result.get("group"))
    left_response_column_id = _comparison_string(left_response.get("column_id"))
    right_response_column_id = _comparison_string(right_response.get("column_id"))
    left_group_column_id = _comparison_string(left_group.get("column_id"))
    right_group_column_id = _comparison_string(right_group.get("column_id"))
    left_group_labels = _one_way_anova_group_labels(left.result)
    right_group_labels = _one_way_anova_group_labels(right.result)
    return OneWayAnovaComparison(
        summary_type="one_way_anova",
        left_response_column_id=left_response_column_id,
        right_response_column_id=right_response_column_id,
        response_display_name=_comparison_display_name(
            left_response,
            right_response,
        ),
        same_response_column=left_response_column_id == right_response_column_id,
        left_group_column_id=left_group_column_id,
        right_group_column_id=right_group_column_id,
        group_display_name=_comparison_display_name(left_group, right_group),
        same_group_column=left_group_column_id == right_group_column_id,
        same_group_label_set=set(left_group_labels) == set(right_group_labels),
        same_group_label_order=left_group_labels == right_group_labels,
        settings=[
            _one_way_anova_setting_comparison(setting, left.result, right.result)
            for setting in (
                "method",
                "anova_type",
                "alpha",
                "confidence_level",
                "posthoc_method",
                "posthoc_policy",
                "missing_policy",
                "posthoc.performed",
                "posthoc.method",
                "posthoc.reason",
            )
        ],
        metrics=[
            _one_way_anova_metric_comparison(metric, left.result, right.result)
            for metric in (
                "n_total",
                "n_used",
                "n_excluded_missing_response",
                "n_excluded_missing_group",
                "n_excluded_non_numeric_response",
                "group_count",
                "groups.0.n",
                "groups.0.mean",
                "groups.0.std",
                "groups.0.mean_confidence_interval.lower",
                "groups.0.mean_confidence_interval.upper",
                "groups.1.n",
                "groups.1.mean",
                "groups.1.std",
                "groups.1.mean_confidence_interval.lower",
                "groups.1.mean_confidence_interval.upper",
                "groups.2.n",
                "groups.2.mean",
                "groups.2.std",
                "groups.2.mean_confidence_interval.lower",
                "groups.2.mean_confidence_interval.upper",
                "anova_table.grand_mean",
                "anova_table.ss_between",
                "anova_table.ss_within",
                "anova_table.df_between",
                "anova_table.df_within",
                "anova_table.ms_between",
                "anova_table.ms_within",
                "test.f_statistic",
                "test.p_value",
                "test.effect_size.eta_squared",
                "test.effect_size.omega_squared",
                "posthoc.q_critical",
                "posthoc.comparison_count",
            )
        ],
    )


def _one_way_anova_group_labels(result: dict[str, object]) -> list[str]:
    groups = result.get("groups")
    if not isinstance(groups, list):
        return []
    labels: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        label = group.get("group_label")
        if isinstance(label, str):
            labels.append(label)
    return labels


def _one_way_anova_setting_comparison(
    setting: str,
    left: dict[str, object],
    right: dict[str, object],
) -> OneWayAnovaSettingComparison:
    left_value = _comparison_scalar(_comparison_path_value(left, setting.split(".")))
    right_value = _comparison_scalar(_comparison_path_value(right, setting.split(".")))
    return OneWayAnovaSettingComparison(
        setting=setting,
        left=left_value,
        right=right_value,
        same=left_value == right_value,
    )


def _one_way_anova_metric_comparison(
    metric: str,
    left: dict[str, object],
    right: dict[str, object],
) -> OneWayAnovaMetricComparison:
    left_value = _comparison_number(_one_way_anova_metric_value(metric, left))
    right_value = _comparison_number(_one_way_anova_metric_value(metric, right))
    delta = None
    if left_value is not None and right_value is not None:
        delta = float(right_value) - float(left_value)
    return OneWayAnovaMetricComparison(
        metric=metric,
        left=left_value,
        right=right_value,
        delta=delta,
    )


def _one_way_anova_metric_value(metric: str, result: dict[str, object]) -> object:
    if metric == "posthoc.comparison_count":
        posthoc = result.get("posthoc")
        if not isinstance(posthoc, dict):
            return None
        comparisons = posthoc.get("comparisons")
        if not isinstance(comparisons, list):
            return None
        return len(comparisons)
    return _comparison_path_value(result, metric.split("."))


def _kruskal_wallis_comparison(
    left: AnalysisResultEnvelope,
    right: AnalysisResultEnvelope,
) -> KruskalWallisComparison | None:
    if not isinstance(left.result, dict) or not isinstance(right.result, dict):
        return None

    left_response = _comparison_mapping(left.result.get("response"))
    right_response = _comparison_mapping(right.result.get("response"))
    left_group = _comparison_mapping(left.result.get("group"))
    right_group = _comparison_mapping(right.result.get("group"))
    left_response_column_id = _comparison_string(left_response.get("column_id"))
    right_response_column_id = _comparison_string(right_response.get("column_id"))
    left_group_column_id = _comparison_string(left_group.get("column_id"))
    right_group_column_id = _comparison_string(right_group.get("column_id"))
    left_group_labels = _group_labels_from_result(left.result)
    right_group_labels = _group_labels_from_result(right.result)
    return KruskalWallisComparison(
        summary_type="kruskal_wallis_test",
        left_response_column_id=left_response_column_id,
        right_response_column_id=right_response_column_id,
        response_display_name=_comparison_display_name(
            left_response,
            right_response,
        ),
        same_response_column=left_response_column_id == right_response_column_id,
        left_group_column_id=left_group_column_id,
        right_group_column_id=right_group_column_id,
        group_display_name=_comparison_display_name(left_group, right_group),
        same_group_column=left_group_column_id == right_group_column_id,
        same_group_label_set=set(left_group_labels) == set(right_group_labels),
        same_group_label_order=left_group_labels == right_group_labels,
        settings=[
            _kruskal_wallis_setting_comparison(setting, left.result, right.result)
            for setting in (
                "method",
                "alpha",
                "posthoc_method",
                "posthoc_policy",
                "missing_policy",
                "has_ties",
                "posthoc.performed",
                "posthoc.method",
                "posthoc.multiplicity_method",
                "posthoc.reason",
            )
        ],
        metrics=[
            _kruskal_wallis_metric_comparison(metric, left.result, right.result)
            for metric in (
                "n_total",
                "n_used",
                "n_excluded_missing_response",
                "n_excluded_missing_group",
                "n_excluded_non_numeric_response",
                "group_count",
                "tie_correction",
                "groups.0.n",
                "groups.0.mean",
                "groups.0.median",
                "groups.0.rank_sum",
                "groups.0.mean_rank",
                "groups.1.n",
                "groups.1.mean",
                "groups.1.median",
                "groups.1.rank_sum",
                "groups.1.mean_rank",
                "groups.2.n",
                "groups.2.mean",
                "groups.2.median",
                "groups.2.rank_sum",
                "groups.2.mean_rank",
                "test.h_statistic",
                "test.df",
                "test.p_value",
                "test.effect_size.epsilon_squared",
                "test.effect_size.tie_correction",
                "posthoc.comparison_count",
            )
        ],
    )


def _group_labels_from_result(result: dict[str, object]) -> list[str]:
    groups = result.get("groups")
    if not isinstance(groups, list):
        return []
    labels: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        label = group.get("group_label")
        if isinstance(label, str):
            labels.append(label)
    return labels


def _kruskal_wallis_setting_comparison(
    setting: str,
    left: dict[str, object],
    right: dict[str, object],
) -> KruskalWallisSettingComparison:
    left_value = _comparison_scalar(_comparison_path_value(left, setting.split(".")))
    right_value = _comparison_scalar(_comparison_path_value(right, setting.split(".")))
    return KruskalWallisSettingComparison(
        setting=setting,
        left=left_value,
        right=right_value,
        same=left_value == right_value,
    )


def _kruskal_wallis_metric_comparison(
    metric: str,
    left: dict[str, object],
    right: dict[str, object],
) -> KruskalWallisMetricComparison:
    left_value = _comparison_number(_kruskal_wallis_metric_value(metric, left))
    right_value = _comparison_number(_kruskal_wallis_metric_value(metric, right))
    delta = None
    if left_value is not None and right_value is not None:
        delta = float(right_value) - float(left_value)
    return KruskalWallisMetricComparison(
        metric=metric,
        left=left_value,
        right=right_value,
        delta=delta,
    )


def _kruskal_wallis_metric_value(metric: str, result: dict[str, object]) -> object:
    if metric == "posthoc.comparison_count":
        posthoc = result.get("posthoc")
        if not isinstance(posthoc, dict):
            return None
        comparisons = posthoc.get("comparisons")
        if not isinstance(comparisons, list):
            return None
        return len(comparisons)
    return _comparison_path_value(result, metric.split("."))


def _comparison_path_value(root: dict[str, object], path: list[str]) -> object:
    value: object = root
    for key in path:
        if isinstance(value, list):
            try:
                value = value[int(key)]
            except (IndexError, ValueError):
                return None
            continue
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _comparison_number(value: object) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    return None


def _comparison_scalar(value: object) -> str | int | float | bool | None:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _comparison_value(value: object) -> str | int | bool | None:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str | int | bool) or value is None:
        return value
    return str(value)
