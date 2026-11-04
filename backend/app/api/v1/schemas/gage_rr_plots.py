"""Versioned, finite-only saved Gage R&R presentation contract."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.statistics.gage_part_order import natural_part_id_key

NonNegativeFinite = Annotated[FiniteFloat, Field(ge=0)]


class GagePlotModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class GagePlotState(GagePlotModel):
    status: Literal["available", "unavailable"]
    unavailable_reason: Literal["non_finite_plot_summary", "invalid_dispersion_constant"] | None

    @model_validator(mode="after")
    def validate_state(self) -> "GagePlotState":
        if (self.status == "available") != (self.unavailable_reason is None):
            raise ValueError("gage_plot_state_invalid")
        return self


class GagePlotMeasurement(GagePlotModel):
    column_id: str
    display_name: str
    unit: str | None


class GageMeasurementRange(GagePlotModel):
    minimum: FiniteFloat
    maximum: FiniteFloat


class GagePlotCounts(GagePlotModel):
    n_total: int = Field(ge=0)
    n_used: int = Field(ge=0)
    n_excluded: int = Field(ge=0)
    part_count: int = Field(ge=2)
    operator_count: int = Field(ge=2)
    replicate_count: int = Field(ge=2)
    cell_count: int = Field(ge=4)
    raw_point_count: int = Field(ge=0)
    displayed_raw_point_count: int = Field(ge=0, le=5000)
    raw_point_limit: int = Field(ge=1, le=5000)
    raw_point_policy: Literal["deterministic_cell_stratified_source_row"]
    truncated: bool


class GagePartSummary(GagePlotModel):
    part_index: int = Field(ge=0)
    part_id: str | None = None
    n: int = Field(ge=1)
    mean: FiniteFloat | None


class GageOperatorSummary(GagePlotModel):
    operator_index: int = Field(ge=0)
    n: int = Field(ge=1)
    mean: FiniteFloat | None


class GageCellSummary(GagePlotModel):
    part_index: int = Field(ge=0)
    operator_index: int = Field(ge=0)
    n: int = Field(ge=2)
    mean: FiniteFloat | None
    range: NonNegativeFinite | None
    sample_sd: NonNegativeFinite | None


class GageComponentPlotItem(GagePlotModel):
    component: Literal["total_gage_rr", "repeatability", "reproducibility", "part_to_part"]
    final_variance: NonNegativeFinite | None
    standard_deviation: NonNegativeFinite | None
    percent_contribution: NonNegativeFinite | None
    percent_study_variation: NonNegativeFinite | None


class GageComponentsPlot(GagePlotState):
    items: list[GageComponentPlotItem] = Field(min_length=4, max_length=4)


class GageDispersionPoint(GagePlotModel):
    part_index: int = Field(ge=0)
    operator_index: int = Field(ge=0)
    n: int = Field(ge=2)
    value: NonNegativeFinite | None
    outside_limits: bool | None


class GageDispersionConstants(GagePlotModel):
    D3: NonNegativeFinite | None
    D4: NonNegativeFinite | None
    c4: Annotated[FiniteFloat, Field(gt=0, le=1)] | None
    B3: NonNegativeFinite | None
    B4: NonNegativeFinite | None


class GageDispersionPlot(GagePlotState):
    statistic: Literal["range", "sample_sd"]
    policy: Literal["within_cell_range_d3_d4_v1", "within_cell_sample_sd_c4_b3_b4_v1"]
    constant_precision: Literal["D3_D4_three_decimal_table", "c4_lgamma_full_precision"]
    warning_codes: list[Literal["within_cell_variation_zero"]] = Field(max_length=1)
    center: NonNegativeFinite | None
    lower_limit: NonNegativeFinite | None
    upper_limit: NonNegativeFinite | None
    constants: GageDispersionConstants
    points: list[GageDispersionPoint]


class GageXbarPoint(GagePlotModel):
    part_index: int = Field(ge=0)
    operator_index: int = Field(ge=0)
    n: int = Field(ge=2)
    value: FiniteFloat | None
    outside_repeatability_limits: bool | None


class GageXbarPlot(GagePlotState):
    center: FiniteFloat | None
    lower_limit: FiniteFloat | None
    upper_limit: FiniteFloat | None
    repeatability_variance: NonNegativeFinite | None
    limit_source: Literal["selected_anova_repeatability"]
    points: list[GageXbarPoint]


class GageRawPoint(GagePlotModel):
    part_index: int = Field(ge=0)
    operator_index: int = Field(ge=0)
    source_row_number: int = Field(ge=1)
    value: FiniteFloat


class GageResponseByPartPlot(GagePlotState):
    points: list[GageRawPoint] = Field(max_length=5000)


class GageOperatorBox(GagePlotModel):
    operator_index: int = Field(ge=0)
    n: int = Field(ge=1)
    mean: FiniteFloat | None
    q1: FiniteFloat | None
    median: FiniteFloat | None
    q3: FiniteFloat | None
    lower_fence: FiniteFloat | None
    upper_fence: FiniteFloat | None
    lower_whisker: FiniteFloat | None
    upper_whisker: FiniteFloat | None
    outlier_count: int = Field(ge=0)
    displayed_outlier_count: int = Field(ge=0)
    outliers: list[GageRawPoint] = Field(max_length=5000)


class GageResponseByOperatorPlot(GagePlotState):
    quantile_policy: Literal["type7_linear"]
    whisker_policy: Literal["observed_values_within_1_5_iqr_fences"]
    boxes: list[GageOperatorBox]


class GageInteractionPoint(GagePlotModel):
    part_index: int = Field(ge=0)
    operator_index: int = Field(ge=0)
    n: int = Field(ge=2)
    mean: FiniteFloat | None


class GageInteractionPlot(GagePlotState):
    interaction_pooled: bool
    points: list[GageInteractionPoint]


class GagePlotCalculationMetadata(GagePlotModel):
    policy_version: Literal["gage_rr_six_panel_v1", "gage_rr_six_panel_v2"]
    part_order: Literal[
        "sorted_full_stripped_identity", "natural_ascii_digit_runs_full_identity_v1"
    ]
    operator_order: Literal["sorted_full_stripped_identity"]
    identifier_policy: Literal[
        "zero_based_indices_original_labels_redacted",
        "part_ids_preserved_operator_replicate_redacted",
    ]
    summary_scope: Literal["all_used_observations_before_display_cap"]
    selected_interaction_policy: Literal["retain", "pooled"]
    replicate_mode: Literal["infer_from_rows", "explicit_column"]
    xbar_interpretation: Literal["part_discrimination_not_process_stability"]
    interaction_interpretation: Literal["observed_cell_means_even_when_pooled"]


class GageRrPlotBundle(GagePlotModel):
    schema_version: Literal[1, 2]
    measurement: GagePlotMeasurement
    measurement_range: GageMeasurementRange
    counts: GagePlotCounts
    parts: list[GagePartSummary]
    operators: list[GageOperatorSummary]
    cells: list[GageCellSummary]
    components: GageComponentsPlot
    dispersion: GageDispersionPlot
    xbar: GageXbarPlot
    response_by_part: GageResponseByPartPlot
    response_by_operator: GageResponseByOperatorPlot
    interaction: GageInteractionPlot
    calculation_metadata: GagePlotCalculationMetadata

    @model_validator(mode="after")
    def validate_identity_and_counts(self) -> "GageRrPlotBundle":
        metadata = self.calculation_metadata
        if self.schema_version == 1:
            if any("part_id" in item.model_fields_set for item in self.parts) or (
                metadata.policy_version != "gage_rr_six_panel_v1"
                or metadata.part_order != "sorted_full_stripped_identity"
                or metadata.identifier_policy != "zero_based_indices_original_labels_redacted"
            ):
                raise ValueError("gage_plot_legacy_identity_policy_invalid")
        else:
            identities = [item.part_id for item in self.parts]
            if any(value is None or not value or value != value.strip() for value in identities):
                raise ValueError("gage_plot_part_identity_invalid")
            full_ids = [value for value in identities if value is not None]
            if len(set(full_ids)) != len(full_ids) or full_ids != sorted(
                full_ids, key=natural_part_id_key
            ):
                raise ValueError("gage_plot_part_identity_order_invalid")
            if (
                metadata.policy_version != "gage_rr_six_panel_v2"
                or metadata.part_order != "natural_ascii_digit_runs_full_identity_v1"
                or metadata.identifier_policy != "part_ids_preserved_operator_replicate_redacted"
            ):
                raise ValueError("gage_plot_part_identity_policy_invalid")
        counts = self.counts
        cells = {(p, o) for p in range(counts.part_count) for o in range(counts.operator_count)}
        if (
            counts.n_total != counts.n_used + counts.n_excluded
            or counts.n_used != counts.cell_count * counts.replicate_count
            or counts.cell_count != len(cells)
            or counts.raw_point_count != counts.n_used
            or counts.displayed_raw_point_count != len(self.response_by_part.points)
            or counts.displayed_raw_point_count != min(counts.n_used, counts.raw_point_limit)
            or counts.truncated != (counts.displayed_raw_point_count < counts.raw_point_count)
            or self.measurement_range.minimum > self.measurement_range.maximum
        ):
            raise ValueError("gage_plot_counts_invalid")
        if [item.part_index for item in self.parts] != list(range(counts.part_count)) or [
            item.operator_index for item in self.operators
        ] != list(range(counts.operator_count)):
            raise ValueError("gage_plot_summary_indices_invalid")
        if any(
            item.n != counts.operator_count * counts.replicate_count for item in self.parts
        ) or any(item.n != counts.part_count * counts.replicate_count for item in self.operators):
            raise ValueError("gage_plot_summary_counts_invalid")
        if [item.component for item in self.components.items] != [
            "total_gage_rr",
            "repeatability",
            "reproducibility",
            "part_to_part",
        ]:
            raise ValueError("gage_plot_component_order_invalid")
        for points in (
            self.cells,
            self.dispersion.points,
            self.xbar.points,
            self.interaction.points,
        ):
            keys = [(item.part_index, item.operator_index) for item in points]
            if (
                len(keys) != len(cells)
                or set(keys) != cells
                or any(item.n != counts.replicate_count for item in points)
            ):
                raise ValueError("gage_plot_cell_indices_invalid")
        by_cell = {(cell.part_index, cell.operator_index): cell for cell in self.cells}
        for interaction_point in self.interaction.points:
            if (
                interaction_point.mean
                != by_cell[interaction_point.part_index, interaction_point.operator_index].mean
            ):
                raise ValueError("gage_plot_interaction_cell_mismatch")
        for xbar_point in self.xbar.points:
            if xbar_point.value != by_cell[xbar_point.part_index, xbar_point.operator_index].mean:
                raise ValueError("gage_plot_xbar_cell_mismatch")
        expected_statistic = "range" if counts.replicate_count <= 8 else "sample_sd"
        if self.dispersion.statistic != expected_statistic:
            raise ValueError("gage_plot_dispersion_statistic_invalid")
        for dispersion_point in self.dispersion.points:
            if dispersion_point.value != getattr(
                by_cell[dispersion_point.part_index, dispersion_point.operator_index],
                expected_statistic,
            ):
                raise ValueError("gage_plot_dispersion_cell_mismatch")
        raw = self.response_by_part.points
        if len({item.source_row_number for item in raw}) != len(raw) or any(
            (item.part_index, item.operator_index) not in cells
            or not self.measurement_range.minimum <= item.value <= self.measurement_range.maximum
            for item in raw
        ):
            raise ValueError("gage_plot_raw_identity_invalid")
        if [item.operator_index for item in self.response_by_operator.boxes] != list(
            range(counts.operator_count)
        ):
            raise ValueError("gage_plot_box_indices_invalid")
        raw_keys = {
            (item.source_row_number, item.operator_index, item.part_index, item.value)
            for item in raw
        }
        for box in self.response_by_operator.boxes:
            if box.n != counts.part_count * counts.replicate_count or (
                box.displayed_outlier_count != len(box.outliers)
                or box.displayed_outlier_count > box.outlier_count
                or box.outlier_count > box.n
                or any(
                    item.operator_index != box.operator_index
                    or (item.source_row_number, item.operator_index, item.part_index, item.value)
                    not in raw_keys
                    for item in box.outliers
                )
            ):
                raise ValueError("gage_plot_box_counts_invalid")
        if self.components.status == "available" and any(
            value is None or value < 0
            for item in self.components.items
            for value in (
                item.final_variance,
                item.standard_deviation,
                item.percent_contribution,
                item.percent_study_variation,
            )
        ):
            raise ValueError("gage_plot_available_components_invalid")
        for plot in (self.dispersion, self.xbar):
            if plot.status == "available":
                if (
                    plot.center is None
                    or plot.lower_limit is None
                    or plot.upper_limit is None
                    or not plot.lower_limit <= plot.center <= plot.upper_limit
                    or any(point.value is None for point in plot.points)
                ):
                    raise ValueError("gage_plot_available_limits_invalid")
                for point in plot.points:
                    assert point.value is not None
                    flag = (
                        point.outside_limits
                        if isinstance(point, GageDispersionPoint)
                        else point.outside_repeatability_limits
                    )
                    if flag != (point.value < plot.lower_limit or point.value > plot.upper_limit):
                        raise ValueError("gage_plot_limit_flag_invalid")
        if self.interaction.interaction_pooled != (
            self.calculation_metadata.selected_interaction_policy == "pooled"
        ):
            raise ValueError("gage_plot_interaction_policy_invalid")
        if self.interaction.status == "available" and any(
            point.mean is None for point in self.interaction.points
        ):
            raise ValueError("gage_plot_interaction_values_invalid")
        if self.response_by_part.status == "available" and any(
            part.mean is None for part in self.parts
        ):
            raise ValueError("gage_plot_part_values_invalid")
        if self.response_by_operator.status == "available":
            for box in self.response_by_operator.boxes:
                values = [
                    box.lower_fence,
                    box.lower_whisker,
                    box.q1,
                    box.median,
                    box.q3,
                    box.upper_whisker,
                    box.upper_fence,
                ]
                finite_values = [value for value in values if value is not None]
                if box.mean is None or len(finite_values) != len(values):
                    raise ValueError("gage_plot_box_values_invalid")
                low_fence, low_whisker, q1, median, q3, high_whisker, high_fence = finite_values
                if not (
                    low_fence <= q1 <= median <= q3 <= high_fence
                    and low_fence <= low_whisker <= high_whisker <= high_fence
                ):
                    raise ValueError("gage_plot_box_order_invalid")
        return self


def validate_gage_rr_plot_result(result: dict[str, Any]) -> None:
    """Validate new saved presentation without mutating historical payloads."""
    version = result.get("schema_version")
    if type(version) is not int:
        raise ValueError("gage_result_schema_unsupported")
    if version in (1, 2):
        return
    if version not in (3, 4):
        raise ValueError("gage_result_schema_unsupported")
    bundle = GageRrPlotBundle.model_validate(result.get("plot_bundle"))
    if bundle.schema_version != version - 2:
        raise ValueError("gage_plot_result_schema_mismatch")
    sample, design, components, selection, columns = (
        result.get(key)
        for key in ("sample", "design", "variance_components", "interaction_selection", "columns")
    )
    if not all(
        isinstance(value, dict) for value in (sample, design, components, selection, columns)
    ):
        raise ValueError("gage_plot_result_relationship_invalid")
    assert isinstance(sample, dict) and isinstance(design, dict) and isinstance(components, dict)
    assert isinstance(selection, dict) and isinstance(columns, dict)
    if any(
        getattr(bundle.counts, key) != sample.get(key)
        for key in ("n_total", "n_used", "n_excluded")
    ) or any(
        getattr(bundle.counts, key) != design.get(key)
        for key in ("part_count", "operator_count", "replicate_count")
    ):
        raise ValueError("gage_plot_result_counts_mismatch")
    for item in bundle.components.items:
        source = components.get(item.component)
        if not isinstance(source, dict) or any(
            getattr(item, key) != source.get(key)
            for key in (
                "final_variance",
                "standard_deviation",
                "percent_contribution",
                "percent_study_variation",
            )
        ):
            raise ValueError("gage_plot_result_components_mismatch")
    if bundle.interaction.interaction_pooled != selection.get(
        "pooled"
    ) or bundle.calculation_metadata.replicate_mode != result.get("replicate_mode"):
        raise ValueError("gage_plot_result_policy_mismatch")
    repeatability = components.get("repeatability")
    measurement = columns.get("measurement")
    if not isinstance(
        repeatability, dict
    ) or bundle.xbar.repeatability_variance != repeatability.get("final_variance"):
        raise ValueError("gage_plot_result_repeatability_mismatch")
    if not isinstance(measurement, dict) or any(
        getattr(bundle.measurement, key) != measurement.get(key)
        for key in ("column_id", "display_name", "unit")
    ):
        raise ValueError("gage_plot_result_measurement_mismatch")
