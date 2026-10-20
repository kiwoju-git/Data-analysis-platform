"""Windows runner partitioning preserves the full ordered browser coverage."""

from __future__ import annotations

import ast
import copy
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
    "rsm_context": "verify_rsm_context",
    "doe_rsm_completion": "verify_doe_rsm_completion",
    "doe_browser_zoom": "verify_doe_browser_zoom",
    "fractional_completion": "verify_fractional_completion",
    "api_translation": "verify_api_translation_boundary",
    "dataset_context": "verify_dataset_context",
    "gp_prediction_context": "verify_gp_prediction_context",
    "schema_concurrency": "verify_schema_concurrency",
    "chart_interactions": "verify_chart_interactions",
    "result_chart_models": "verify_result_chart_models",
    "chart_formatting": "verify_chart_formatting",
    "pilot_feedback": "verify_pilot_feedback",
    "pilot_ingestion": "verify_pilot_ingestion",
    "pilot_prediction": "verify_pilot_prediction",
    "pilot_groups": "verify_pilot_groups",
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
        "rsm_context",
        "api_translation",
        "dataset_context",
        "gp_prediction_context",
        "schema_concurrency",
        "chart_interactions",
        "result_chart_models",
        "chart_formatting",
        "pilot_feedback",
        "pilot_ingestion",
        "pilot_prediction",
        "pilot_groups",
        "fractional_completion",
        "doe_rsm_completion",
        "doe_browser_zoom",
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
    assert driver.suite_stage_ids("prediction") == ("gp_prediction_context", "pilot_prediction")
    assert "pilot_feedback" in driver.suite_stage_ids("context")
    assert "rsm_context" in driver.suite_stage_ids("context")
    assert "rsm_context" not in driver.suite_stage_ids("workflows")
    assert "pilot_ingestion" in driver.suite_stage_ids("data")
    assert "pilot_groups" in driver.suite_stage_ids("workflows")


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
            if _stage == "doe_rsm_completion":
                return {"design_id": "synthetic-design", "analysis_id": "synthetic-analysis"}

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
    assert aggregate["if"] == "always() && inputs.generate_linux_locks != true"
    assert aggregate["needs"] == "windows-e2e"
    assert "--kind windows-e2e" in aggregate["steps"][-1]["run"]
    assert "e2e" in jobs["release-ready"]["needs"]
    linux = next(step for step in jobs["linux"]["steps"] if step.get("name") == "Linux browser E2E")
    assert linux["run"] == "bash scripts/e2e.sh --diagnostics-root .tmp/linux-e2e"
    powershell = (ROOT / "scripts/e2e.ps1").read_text(encoding="utf-8")
    assert '$PSBoundParameters.ContainsKey("Suite")' in powershell
    assert '$Args += @("--suite", "$Suite")' in powershell
    assert '[ValidateSet("full", "workflows", "context", "data", "prediction")]' in powershell


def test_early_browser_diagnostics_do_not_replace_product_gates():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    diagnostic = jobs["browser-diagnostics"]
    assert diagnostic["strategy"]["matrix"]["suite"] == ["context", "workflows"]
    assert diagnostic["strategy"]["fail-fast"] is False
    assert "inputs.browser_diagnostics == true" in diagnostic["if"]
    assert "needs" not in diagnostic
    for name in ("windows", "windows-e2e", "linux", "python311", "linux-release", "release-ready"):
        assert "browser_diagnostics" not in jobs[name]["if"]
    assert set(jobs["release-ready"]["needs"]) == {
        "windows",
        "e2e",
        "linux",
        "python311",
        "linux-release",
        "dependency-security",
    }
    command = next(
        step["run"] for step in diagnostic["steps"] if step.get("name") == "Existing browser suite"
    )
    assert "--suite ${{ matrix.suite }}" in command
    assert "--diagnostics-root" in command


def test_native_linux_lock_generation_is_not_a_product_or_release_gate():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    option = triggers["workflow_dispatch"]["inputs"]["generate_linux_locks"]
    assert option["type"] == "boolean"
    assert option["default"] is False
    assert option["required"] is False
    jobs = workflow["jobs"]
    native = jobs["generate-linux-locks"]
    assert native["if"] == (
        "github.event_name == 'workflow_dispatch' && inputs.generate_linux_locks == true"
    )
    assert native["runs-on"] == "ubuntu-24.04"
    assert native["permissions"] == {"contents": "read"}
    assert native["strategy"] == {
        "fail-fast": False,
        "matrix": {
            "include": [
                {"python": "3.11", "target": "py311-linux", "profile": "runtime"},
                {"python": "3.11", "target": "py311-linux", "profile": "dev"},
                {"python": "3.12", "target": "py312-linux", "profile": "runtime"},
                {"python": "3.12", "target": "py312-linux", "profile": "dev"},
            ]
        },
    }
    for name in ("dependency-security", "e2e", "release-ready"):
        assert jobs[name]["if"] == "always() && inputs.generate_linux_locks != true"
    for name in (
        "security-python",
        "security-npm",
        "windows",
        "windows-e2e",
        "linux",
        "python311",
        "linux-release",
    ):
        assert jobs[name]["if"] == "inputs.generate_linux_locks != true"
    assert jobs["release-ready"]["needs"] == [
        "windows",
        "e2e",
        "linux",
        "python311",
        "linux-release",
        "dependency-security",
    ]
    assert "needs" not in native
    commands = "\n".join(step.get("run", "") for step in native["steps"])
    assert "pip download --only-binary=:all: --require-hashes" in commands
    assert "pip download --only-binary=:all: --no-deps" in commands
    assert "'contourpy==1.3.2'" in commands
    assert "scripts/generate_python_lock.py" in commands
    assert "scripts/validate_python_lock.py" in commands
    assert "pip install --no-index --find-links" in commands
    assert "--only-binary=:all: --require-hashes" in commands
    assert "pip check" in commands
    assert 'name="serial"' in commands
    assert '"product_validation_complete": False' in commands
    assert '"network_isolation_enforced": False' in commands
    assert "release_readiness.py" not in commands
    assert "--platform" not in commands
    upload = next(
        step for step in native["steps"] if step.get("uses") == "actions/upload-artifact@v4"
    )
    assert upload["if"] == "success()"
    assert upload["with"]["name"] == (
        "native-contourpy-locks-${{ matrix.target }}-${{ matrix.profile }}-${{ github.sha }}"
    )
    assert upload["with"]["if-no-files-found"] == "error"


def _native_lock_python_blocks() -> list[str]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    return [
        step["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        for step in workflow["jobs"]["generate-linux-locks"]["steps"]
        if "<<'PY'\n" in step.get("run", "")
    ]


def test_native_lock_python_blocks_compile():
    blocks = _native_lock_python_blocks()
    assert len(blocks) == 2
    for code in blocks:
        compile(code, "ci-native-lock-verification", "exec")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("version", "Existing version or wheel SHA-256 changed: numpy"),
        ("hash", "Existing version or wheel SHA-256 changed: numpy"),
        ("missing", "Only ContourPy may be added"),
        ("extra", "Only ContourPy may be added"),
        ("contour_version", "Unexpected ContourPy version"),
    ],
)
def test_native_lock_actual_drift_checks_reject_changes(change, message):
    before = {"numpy": {"version": "2.2.6", "sha256": "a" * 64}}
    after = {
        **copy.deepcopy(before),
        "contourpy": {"version": "1.3.2", "sha256": "b" * 64},
    }
    tree = ast.parse(_native_lock_python_blocks()[0])
    first = next(
        index
        for index, node in enumerate(tree.body)
        if isinstance(node, ast.If) and ast.unparse(node.test).startswith("set(after)")
    )
    checks = compile(
        ast.Module(body=tree.body[first : first + 3], type_ignores=[]), "drift", "exec"
    )
    exec(checks, {"before": before, "after": after})
    if change == "version":
        after["numpy"]["version"] = "2.3.0"
    elif change == "hash":
        after["numpy"]["sha256"] = "c" * 64
    elif change == "missing":
        del after["numpy"]
    elif change == "extra":
        after["unexpected"] = {"version": "1.0", "sha256": "c" * 64}
    else:
        after["contourpy"]["version"] = "1.4.0"
    with pytest.raises(SystemExit, match=message):
        exec(checks, {"before": before, "after": after})
