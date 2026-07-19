from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPECTED_PATH = (
    REPOSITORY_ROOT / "examples" / "tutorial" / "tutorial_expected_results.json"
)
DEFAULT_TUTORIAL_PATH = REPOSITORY_ROOT / "docs" / "studio_end_to_end_tutorial_ko.md"


@dataclass(frozen=True)
class RenderedResult:
    lines: tuple[str, ...]
    field_paths: tuple[str, ...]


def _number(value: Any, digits: int = 4) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.{digits}f}"


def _probability(value: Any) -> str:
    number = float(value)
    if number != 0 and abs(number) < 0.0001:
        return f"{number:.3e}"
    return f"{number:.6f}"


def _source_line(section: dict[str, Any]) -> str:
    return (
        f"- **검증 source:** `{section['method_id']}` v{section['method_version']} · "
        f"input SHA-256 `{section['input_file_sha256']}`"
    )


def _render(
    section: dict[str, Any], *lines: str, paths: tuple[str, ...]
) -> RenderedResult:
    return RenderedResult(lines=(_source_line(section), *lines), field_paths=paths)


def _eda_descriptive(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    y = result["yield_pct"]
    tensile = result["tensile_strength_mpa"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - `yield_pct`: N={y['n_used']}, mean={_number(y['mean'])}, "
            f"SD={_number(y['std'])}, Q1={_number(y['q1'])}, median={_number(y['median'])}, "
            f"Q3={_number(y['q3'])}, range {_number(y['min'])}~{_number(y['max'])}"
        ),
        (
            f"  - `tensile_strength_mpa`: N={tensile['n_used']}, "
            f"mean={_number(tensile['mean'])}, SD={_number(tensile['std'])}, "
            f"Q1={_number(tensile['q1'])}, median={_number(tensile['median'])}, "
            f"Q3={_number(tensile['q3'])}, "
            f"range {_number(tensile['min'])}~{_number(tensile['max'])}"
        ),
        paths=("result.yield_pct.*", "result.tensile_strength_mpa.*"),
    )


def _eda_graphical(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    y = result["yield_pct"]
    tensile = result["tensile_strength_mpa"]
    return _render(
        section,
        "- **그래프 요약 예상값:**",
        (
            f"  - `yield_pct`: N={y['n_used']}, missing={y['n_missing']}, "
            f"histogram bins={y['histogram_bin_count']}, boxplot outliers={y['boxplot_outlier_count']}, "
            f"range {_number(y['minimum'])}~{_number(y['maximum'])}"
        ),
        (
            f"  - `tensile_strength_mpa`: N={tensile['n_used']}, "
            f"missing={tensile['n_missing']}, histogram bins={tensile['histogram_bin_count']}, "
            f"boxplot outliers={tensile['boxplot_outlier_count']}, "
            f"range {_number(tensile['minimum'])}~{_number(tensile['maximum'])}"
        ),
        paths=("result.yield_pct.*", "result.tensile_strength_mpa.*"),
    )


def _two_sample_t(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    left, right = result["groups"]
    ci = result["confidence_interval"]
    return _render(
        section,
        "- **예상 실제 결과 (Welch, 표시 반올림):**",
        (
            f"  - {left['label']}: N={left['n']}, mean={_number(left['mean'])}; "
            f"{right['label']}: N={right['n']}, mean={_number(right['mean'])}"
        ),
        (
            f"  - mean difference={_number(result['mean_difference'])}, "
            f"95% CI [{_number(ci['lower'])}, {_number(ci['upper'])}], "
            f"p={_probability(result['p_value'])}, Hedges g={_number(result['hedges_g'])}"
        ),
        paths=(
            "result.groups",
            "result.mean_difference",
            "result.confidence_interval",
            "result.p_value",
            "result.hedges_g",
        ),
    )


def _anova(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    group_n = result["group_n"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - N={result['n_used']}; group N="
            f"Line-A {group_n['Line-A']}, Line-B {group_n['Line-B']}, Line-C {group_n['Line-C']}"
        ),
        (
            f"  - F({result['df_between']}, {result['df_within']})={_number(result['f_statistic'])}, "
            f"p={_probability(result['p_value'])}, eta-squared={_number(result['eta_squared'], 5)}, "
            f"omega-squared={_number(result['omega_squared'], 5)}, "
            f"post-hoc={'수행됨' if result['posthoc_performed'] else '수행되지 않음'}"
        ),
        paths=(
            "result.n_used",
            "result.group_n",
            "result.df_between",
            "result.df_within",
            "result.f_statistic",
            "result.p_value",
            "result.eta_squared",
            "result.omega_squared",
            "result.posthoc_performed",
        ),
    )


def _one_proportion(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    ci = result["confidence_interval"]
    return _render(
        section,
        "- **예상 실제 결과 (Wilson 95% CI, 표시 반올림):**",
        (
            f"  - event `{result['event_level']}`={result['event_count']}/{result['n']}, "
            f"proportion={_number(result['sample_proportion'])}, "
            f"CI [{_number(ci['lower'])}, {_number(ci['upper'])}]"
        ),
        f"  - p={_probability(result['p_value'])}, Cohen h={_number(result['cohen_h'])}",
        paths=(
            "result.event_level",
            "result.event_count",
            "result.n",
            "result.sample_proportion",
            "result.confidence_interval",
            "result.p_value",
            "result.cohen_h",
        ),
    )


def _chi_square(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    expected = result["expected_count_summary"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - N={result['n_used']}, chi-square({result['df']})={_number(result['chi_square'])}, "
            f"p={_probability(result['p_value'])}, Cramer's V={_number(result['cramers_v'])}"
        ),
        (
            f"  - minimum expected={_number(expected['min_expected'])}, "
            f"cells below 5={expected['cells_below_5']}/{expected['cell_count']}"
        ),
        paths=(
            "result.n_used",
            "result.chi_square",
            "result.df",
            "result.p_value",
            "result.cramers_v",
            "result.expected_count_summary",
        ),
    )


def _pearson(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    ci = result["confidence_interval"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - N={result['n_used']}, r={_number(result['correlation'], 5)}, "
            f"95% CI [{_number(ci['lower'], 5)}, {_number(ci['upper'], 5)}], "
            f"p={_probability(result['p_value'])}, r-squared={_number(result['r_squared'], 5)}"
        ),
        paths=(
            "result.n_used",
            "result.correlation",
            "result.confidence_interval",
            "result.p_value",
            "result.r_squared",
        ),
    )


def _xy(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    return _render(
        section,
        "- **X-Y 행렬 예상값:**",
        (
            f"  - X={result['x_column_count']}개, Y={result['y_column_count']}개, "
            f"pairs={result['pair_count']}; 모든 tutorial pair N={result['pairs'][0]['n_used']}"
        ),
        paths=(
            "result.x_column_count",
            "result.y_column_count",
            "result.pair_count",
            "result.pairs[*].n_used",
        ),
    )


def _linear(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    signs = {item["term"]: item["sign"] for item in result["coefficients"]}
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - N={result['n_used']}, exclusions={result['n_excluded']}, "
            f"R-squared={_number(result['r_squared'], 5)}, "
            f"adjusted R-squared={_number(result['adjusted_r_squared'], 5)}"
        ),
        (
            "  - coefficient sign: "
            f"temperature `{signs['temperature_c']}`, temperature^2 `{signs['temperature_c^2']}`, "
            f"pressure^2 `{signs['pressure_bar^2']}`, interaction `{signs['temperature_c:pressure_bar']}`; "
            f"model asset={'생성됨' if result['model_asset_created'] else '생성되지 않음'}"
        ),
        paths=(
            "result.n_used",
            "result.n_excluded",
            "result.r_squared",
            "result.adjusted_r_squared",
            "result.coefficients",
            "result.model_asset_created",
        ),
    )


def _prediction(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    rows = result["first_five"]
    lines = [
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - preflight ready={_number(result['preflight_ready'])}, "
            f"total/usable/predicted/excluded={result['row_count_total']}/{result['row_count_usable']}/"
            f"{result['row_count_predicted']}/{result['row_count_excluded']}, "
            f"extrapolation warnings={result['extrapolation_warning_count']}, CSV rows={result['csv_row_count']}"
        ),
    ]
    for row in rows:
        mean_ci = row["mean_confidence_interval"]
        prediction_interval = row["prediction_interval"]
        lines.append(
            f"  - row {row['row_index']}: mean={_number(row['predicted_mean'])}, "
            f"mean CI [{_number(mean_ci['lower'])}, {_number(mean_ci['upper'])}], "
            f"prediction interval [{_number(prediction_interval['lower'])}, "
            f"{_number(prediction_interval['upper'])}]"
        )
    return _render(
        section,
        *lines,
        paths=(
            "result.preflight_ready",
            "result.row_count_*",
            "result.extrapolation_warning_count",
            "result.csv_row_count",
            "result.first_five",
        ),
    )


def _run_chart(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        f"  - N={result['n_used']}, center median={_number(result['center_line'])}, points={result['point_count']}, signals={result['signal_count']}",
        paths=(
            "result.n_used",
            "result.center_line",
            "result.point_count",
            "result.signal_count",
        ),
    )


def _capability(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    spec = result["spec_limits"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - N={result['n_used']}, LSL/Target/USL={_number(spec['lsl'], 0)}/"
            f"{_number(spec['target'], 0)}/{_number(spec['usl'], 0)}"
        ),
        (
            f"  - Cp={_number(result['cp'])}, Cpk={_number(result['cpk'])}, "
            f"Pp={_number(result['pp'])}, Ppk={_number(result['ppk'])}"
        ),
        paths=(
            "result.n_used",
            "result.spec_limits",
            "result.cp",
            "result.cpk",
            "result.pp",
            "result.ppk",
        ),
    )


def _attribute_chart(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - Phase I center={_number(result['phase_1_center_line'], 7)}, "
            f"points={result['phase_1_point_count']}, signals={result['phase_1_signal_count']}, "
            f"limit-set promoted={_number(result['limit_set_promoted'])}"
        ),
        (
            f"  - Phase II points={result['phase_2_target_point_count']}, "
            f"signals={result['phase_2_signal_count']}, dispersion available="
            f"{_number(result['phase_2_dispersion_available'])}, "
            f"ratio={_number(result['phase_2_dispersion_ratio'], 5)}"
        ),
        paths=("result.phase_1_*", "result.limit_set_promoted", "result.phase_2_*"),
    )


def _gage(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - N={result['n_used']}, balanced={_number(result['balanced'])}, "
            f"repeatability %study={_number(result['repeatability']['percent_study_variation'])}, "
            f"reproducibility={_number(result['reproducibility']['percent_study_variation'])}"
        ),
        (
            f"  - total Gage R&R={_number(result['total_gage_rr']['percent_study_variation'])}, "
            f"part-to-part={_number(result['part_to_part']['percent_study_variation'])}, ndc={result['ndc']}"
        ),
        paths=(
            "result.n_used",
            "result.balanced",
            "result.repeatability.percent_study_variation",
            "result.reproducibility.percent_study_variation",
            "result.total_gage_rr.percent_study_variation",
            "result.part_to_part.percent_study_variation",
            "result.ndc",
        ),
    )


def _factorial(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    effects = result["effect_ordering"][:4]
    effect_text = ", ".join(
        f"`{item['term_id']}` {_number(item['effect'])}" for item in effects
    )
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        f"  - N={result['n_observations']}, residual df={result['df_residual']}, selected interaction `{result['selected_interaction']}`",
        f"  - effect order: {effect_text}",
        paths=(
            "result.n_observations",
            "result.df_residual",
            "result.selected_interaction",
            "result.effect_ordering",
        ),
    )


def _rsm(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    point = result["stationary_point"]
    lack = result["lack_of_fit"]["lack_of_fit"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - R-squared={_number(result['r_squared'], 5)}, "
            f"adjusted={_number(result['adjusted_r_squared'], 5)}, warnings={result['warning_count']}"
        ),
        (
            f"  - stationary `{point['classification']}`: temperature={_number(point['actual_coordinates']['temperature_c'])}, "
            f"pressure={_number(point['actual_coordinates']['pressure_bar'])}, "
            f"predicted={_number(point['predicted_response'])}, inside region="
            f"{_number(point['within_factorial_cube'])}"
        ),
        f"  - lack-of-fit F={_number(lack['f_statistic'])}, p={_probability(lack['p_value'])}",
        paths=(
            "result.r_squared",
            "result.adjusted_r_squared",
            "result.warning_count",
            "result.stationary_point",
            "result.lack_of_fit.lack_of_fit",
        ),
    )


def _optimizer(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    coordinates = result["actual_coordinates"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - goal `{result['goal']}`, temperature={_number(coordinates['temperature_c'])}, "
            f"pressure={_number(coordinates['pressure_bar'])}, predicted={_number(result['predicted_response'])}"
        ),
        (
            f"  - composite desirability={_number(result['composite_desirability'])}, "
            f"termination `{result['termination_reason']}`, global optimum guaranteed="
            f"{_number(result['global_optimum_guaranteed'])}"
        ),
        paths=(
            "result.goal",
            "result.actual_coordinates",
            "result.predicted_response",
            "result.composite_desirability",
            "result.termination_reason",
            "result.global_optimum_guaranteed",
        ),
    )


def _bayesian(section: dict[str, Any]) -> RenderedResult:
    result = section["result"]
    coordinates = result["actual_coordinates"]
    return _render(
        section,
        "- **예상 실제 결과 (표시 반올림):**",
        (
            f"  - completed observations={result['completed_observation_count']}, "
            f"recommended temperature={_number(coordinates['temperature_c'])}, "
            f"pressure={_number(coordinates['pressure_bar'])}"
        ),
        (
            f"  - predicted mean={_number(result['predicted_mean'])}, posterior SD="
            f"{_number(result['predicted_standard_deviation'])}, EI={_number(result['expected_improvement'])}, "
            f"trial `{result['trial_state']}`"
        ),
        paths=(
            "result.completed_observation_count",
            "result.actual_coordinates",
            "result.predicted_mean",
            "result.predicted_standard_deviation",
            "result.expected_improvement",
            "result.trial_state",
        ),
    )


RENDERERS: dict[str, Callable[[dict[str, Any]], RenderedResult]] = {
    "eda.descriptive": _eda_descriptive,
    "eda.graphical_summary": _eda_graphical,
    "hypothesis.two_sample_t": _two_sample_t,
    "hypothesis.one_way_anova": _anova,
    "categorical.one_proportion": _one_proportion,
    "categorical.chi_square_association": _chi_square,
    "regression.pearson": _pearson,
    "regression.xy_correlation": _xy,
    "regression.linear_model": _linear,
    "regression.predict": _prediction,
    "quality.run_chart": _run_chart,
    "quality.capability": _capability,
    "quality.attribute_control_chart": _attribute_chart,
    "quality.gage_rr": _gage,
    "doe.factorial_design": _factorial,
    "doe.response_surface": _rsm,
    "regression.response_optimizer": _optimizer,
    "doe.bayesian_optimization": _bayesian,
}


def _marker_block(method_id: str, rendered: RenderedResult) -> str:
    return "\n".join(
        (
            f"<!-- TUTORIAL_RESULT:{method_id}:start -->",
            *rendered.lines,
            f"<!-- TUTORIAL_RESULT:{method_id}:end -->",
        )
    )


def _replace_or_check(
    tutorial_text: str,
    expected: dict[str, Any],
    *,
    write: bool,
) -> tuple[str, list[str]]:
    updated = tutorial_text
    errors: list[str] = []
    results = expected.get("results", {})
    if set(results) != set(RENDERERS):
        missing = sorted(set(RENDERERS) - set(results))
        extra = sorted(set(results) - set(RENDERERS))
        errors.append(
            f"expected result section mismatch: missing={missing}, extra={extra}"
        )
        return updated, errors

    for method_id, renderer in RENDERERS.items():
        rendered = renderer(results[method_id])
        desired = _marker_block(method_id, rendered)
        pattern = re.compile(
            rf"<!-- TUTORIAL_RESULT:{re.escape(method_id)}:start -->.*?"
            rf"<!-- TUTORIAL_RESULT:{re.escape(method_id)}:end -->",
            re.DOTALL,
        )
        matches = list(pattern.finditer(updated))
        if len(matches) != 1:
            errors.append(
                f"{method_id}: expected exactly one marker block, found {len(matches)}"
            )
            continue
        current = matches[0].group(0)
        if write:
            updated = (
                updated[: matches[0].start()] + desired + updated[matches[0].end() :]
            )
        elif current != desired:
            field_list = ", ".join(rendered.field_paths)
            errors.append(f"{method_id}: Markdown drift for fields {field_list}")
    return updated, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render or verify tutorial result blocks from API-derived expected JSON."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--expected-path", type=Path, default=DEFAULT_EXPECTED_PATH)
    parser.add_argument("--tutorial-path", type=Path, default=DEFAULT_TUTORIAL_PATH)
    args = parser.parse_args()

    expected = json.loads(args.expected_path.read_text(encoding="utf-8"))
    tutorial_text = args.tutorial_path.read_text(encoding="utf-8")
    updated, errors = _replace_or_check(tutorial_text, expected, write=args.write)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.write:
        if updated != tutorial_text:
            args.tutorial_path.write_text(updated, encoding="utf-8", newline="\n")
        print(f"Rendered {len(RENDERERS)} tutorial result blocks.")
    else:
        print(f"Verified {len(RENDERERS)} tutorial result blocks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
