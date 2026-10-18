"""Windows runner partitioning preserves the full ordered browser coverage."""

from __future__ import annotations

import ast
import importlib
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
ONLY_FLAGS = (
    "factorial-workflow",
    "gpr-report",
    "refined-ui",
    "api-translation",
    "dataset-context",
    "gp-prediction-context",
    "schema-concurrency",
    "upload-recovery",
    "chart-formatting",
    "report-center-context",
    "analysis-completion",
)
STAGE_CALLS = {
    "analysis_completion": "verify_analysis_completion",
    "report_center_context": "verify_report_center_context",
    "api_translation": "verify_api_translation_boundary",
    "dataset_context": "verify_dataset_context",
    "gp_prediction_context": "verify_gp_prediction_context",
    "schema_concurrency": "verify_schema_concurrency",
    "chart_interactions": "verify_chart_interactions",
    "result_chart_models": "verify_result_chart_models",
    "chart_formatting": "verify_chart_formatting",
    "desktop_resize": "verify_desktop_resize",
    "localization_shell": "verify_localization_shell",
}


@pytest.fixture
def driver(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tests/e2e"))
    return importlib.import_module("critical_path")


def test_default_full_order_and_exact_disjoint_suite_union(driver):
    assert driver.argument_parser().parse_args([]).suite is None
    assert driver.suite_stage_ids("full") == (
        "analysis_completion",
        "report_center_context",
        "api_translation",
        "dataset_context",
        "gp_prediction_context",
        "schema_concurrency",
        "chart_interactions",
        "result_chart_models",
        "chart_formatting",
        "desktop_resize",
        "localization_shell",
        "legacy_workflow",
    )
    partitions = [driver.suite_stage_ids(name) for name in driver.SUITE_STAGES]
    union = Counter(stage for partition in partitions for stage in partition)
    assert union == Counter(driver.suite_stage_ids("full"))
    assert set(union.values()) == {1}
    for partition in partitions:
        assert partition == tuple(stage for stage in driver.FULL_STAGE_ORDER if stage in partition)
    assert driver.suite_stage_ids("prediction") == ("gp_prediction_context",)


@pytest.mark.parametrize("suite", ["full", "workflows", "context", "data", "prediction"])
@pytest.mark.parametrize("flag", ONLY_FLAGS)
def test_explicit_suite_rejects_every_focused_only_flag(driver, suite, flag):
    with pytest.raises(SystemExit) as failure:
        driver.argument_parser().parse_args(["--suite", suite, f"--{flag}-only"])
    assert failure.value.code == 2
    assert getattr(
        driver.argument_parser().parse_args([f"--{flag}-only"]), flag.replace("-", "_") + "_only"
    )


class LegacyBoundary(BaseException):
    pass


@pytest.mark.parametrize("suite", [None, "full", "workflows", "context", "data", "prediction"])
def test_actual_dispatch_invokes_exact_partition_and_closes_browser(
    driver, monkeypatch, tmp_path, suite
):
    calls = []
    closed = []
    browser = SimpleNamespace(close=lambda: closed.append(True))

    @contextmanager
    def playwright():
        yield SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_kwargs: browser))

    monkeypatch.setattr(driver, "sync_playwright", playwright)
    for stage, name in STAGE_CALLS.items():

        def invoke(*_args, _stage=stage, **_kwargs):
            calls.append(_stage)
            if _stage == "localization_shell":
                raise LegacyBoundary()

        monkeypatch.setattr(driver, name, invoke)
    diagnostics = SimpleNamespace(root=tmp_path, step=lambda _label: None)
    kwargs = {} if suite is None else {"suite": suite}
    if suite in (None, "full", "workflows"):
        with pytest.raises(LegacyBoundary):
            driver.run_browser_flow("http://frontend", diagnostics, "http://backend", **kwargs)
    else:
        driver.run_browser_flow("http://frontend", diagnostics, "http://backend", **kwargs)
    expected = [
        stage for stage in driver.suite_stage_ids(suite or "full") if stage != "legacy_workflow"
    ]
    assert calls == expected
    assert closed == [True]


def test_legacy_workflow_checks_remain_in_the_unchanged_block():
    tree = ast.parse((ROOT / "tests/e2e/critical_path.py").read_text(encoding="utf-8"))
    flow = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_browser_flow"
    )
    block = next(node for node in ast.walk(flow) if isinstance(node, ast.Try))
    start = next(
        index
        for index, node in enumerate(block.body)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "verify_desktop_resize"
    )
    calls = [
        node.func.id
        for statement in block.body[start:]
        for node in ast.walk(statement)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and (
            node.func.id.startswith("verify_")
            or node.func.id
            in {
                "create_exports",
                "restore_and_compare_saved_results",
                "delete_one_saved_analysis_run",
            }
        )
    ]
    assert calls == [
        "verify_desktop_resize",
        "verify_localization_shell",
        "verify_browser_branding",
        "verify_factorial_model_workflow",
        "verify_curvature_selection",
        "verify_pls_regression_and_prediction",
        "verify_gaussian_process_regression_and_prediction",
        "verify_dashboard_navigation",
        "verify_dataset_cell_correction",
        "verify_project_dashboard",
        "verify_dashboard_navigation",
        "verify_sidebar_group_toggle",
        "verify_active_dataset_analysis_alignment",
        "verify_graph_builder_box_plot",
        "create_exports",
        "verify_help_report_and_manage_routes",
        "restore_and_compare_saved_results",
        "delete_one_saved_analysis_run",
        "verify_schema_stale_behavior",
        "verify_linear_model_fit_and_prediction",
        "verify_regularized_regression",
        "verify_pls_regression_and_prediction",
        "verify_gaussian_process_regression_and_prediction",
        "verify_principal_components_analysis",
        "verify_attribute_control_chart",
        "verify_reporting_summary_variance_and_scatter",
        "verify_doe_factorial_analysis",
        "verify_factorial_model_workflow",
        "verify_curvature_selection",
        "verify_doe_response_surface_analysis",
        "verify_latin_hypercube_design",
        "verify_bayesian_optimization",
        "verify_xlsx_file_upload",
        "verify_csv_file_upload_and_error_recovery",
        "verify_parser_option_editing",
        "verify_delimiter_option_editing",
        "verify_xlsx_sheet_selection",
        "verify_text_encoding_selection",
        "verify_descriptive_quick_charts_and_run_chart",
        "verify_graph_layout_refinements",
        "verify_grouped_graphs_and_hypothesis_extensions",
        "verify_lazy_panel_direct_routes",
        "verify_lazy_panel_error_boundary",
        "verify_refined_ui",
        "verify_startup_readiness",
        "verify_two_variances",
    ]


def test_windows_ci_isolated_matrix_aggregate_and_linux_full_contract():
    jobs = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    windows = jobs["windows-e2e"]
    assert windows["needs"] == "windows"
    assert windows["runs-on"] == "windows-latest"
    assert windows["strategy"] == {
        "fail-fast": False,
        "matrix": {"suite": ["workflows", "context", "data", "prediction"]},
    }
    assert windows["timeout-minutes"] == 20
    browser = next(step for step in windows["steps"] if step.get("name") == "Browser E2E Smoke")
    assert '-Suite "${{ matrix.suite }}"' in browser["run"]
    upload = next(
        step for step in windows["steps"] if step.get("uses") == "actions/upload-artifact@v4"
    )
    assert upload["with"]["name"] == "e2e-logs-${{ matrix.suite }}"
    aggregate = jobs["e2e"]
    assert aggregate["if"] == "always()"
    assert aggregate["needs"] == "windows-e2e"
    assert "--kind windows-e2e" in aggregate["steps"][-1]["run"]
    assert "e2e" in jobs["release-ready"]["needs"]
    linux = next(step for step in jobs["linux"]["steps"] if step.get("name") == "Linux browser E2E")
    assert linux["run"] == "bash scripts/e2e.sh --diagnostics-root .tmp/linux-e2e"
    powershell = (ROOT / "scripts/e2e.ps1").read_text(encoding="utf-8")
    assert '$PSBoundParameters.ContainsKey("Suite")' in powershell
    assert '$Args += @("--suite", "$Suite")' in powershell
    assert '[ValidateSet("full", "workflows", "context", "data", "prediction")]' in powershell
