"""Windows runner partitioning preserves the full ordered browser coverage."""

from __future__ import annotations

import ast
import copy
import importlib
import json
import subprocess
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
    "bo_noise_context": "verify_bo_noise_context",
    "bo_progress": "verify_bo_progress",
    "bo_vector_history": "verify_bo_vector_history",
    "bo_dataset_import": "verify_bo_dataset_import",
    "bo_profile_constraints": "verify_profile_constraints",
    "bo_xy_gpr_navigation": "verify_bo_xy_gpr_navigation",
    "bo_noise_extension": "verify_bo_noise_extension",
    "doe_rsm_completion": "verify_doe_rsm_completion",
    "doe_browser_zoom": "verify_doe_browser_zoom",
    "gage_followup": "verify_gage_followup",
    "gage_six_panel": "verify_gage_six_panel",
    "english_system_text": "verify_english_system_text",
    "result_metric_layout": "verify_result_metric_layout",
    "fractional_completion": "verify_fractional_completion",
    "api_translation": "verify_api_translation_boundary",
    "dataset_context": "verify_dataset_context",
    "gp_prediction_context": "verify_gp_prediction_context",
    "gp_validation_extension": "verify_gp_validation_extension",
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
        "bo_noise_context",
        "bo_progress",
        "bo_vector_history",
        "bo_dataset_import",
        "bo_profile_constraints",
        "bo_xy_gpr_navigation",
        "api_translation",
        "dataset_context",
        "gp_prediction_context",
        "gp_validation_extension",
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
        "gage_followup",
        "gage_six_panel",
        "english_system_text",
        "result_metric_layout",
        "bo_noise_extension",
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
    assert driver.suite_stage_ids("prediction") == (
        "gp_prediction_context",
        "gp_validation_extension",
        "pilot_prediction",
    )
    assert "pilot_feedback" in driver.suite_stage_ids("context")
    assert "rsm_context" in driver.suite_stage_ids("context")
    assert "bo_vector_history" in driver.suite_stage_ids("context")
    assert "bo_xy_gpr_navigation" in driver.suite_stage_ids("context")
    assert "bo_dataset_import" in driver.suite_stage_ids("workflows")
    assert "bo_profile_constraints" in driver.suite_stage_ids("workflows")
    assert "bo_profile_constraints" not in driver.suite_stage_ids("context")
    assert "rsm_context" not in driver.suite_stage_ids("workflows")
    assert "pilot_ingestion" in driver.suite_stage_ids("data")
    assert "pilot_groups" in driver.suite_stage_ids("workflows")
    assert "gage_followup" in driver.suite_stage_ids("workflows")
    assert "gage_six_panel" in driver.suite_stage_ids("workflows")
    assert {"english_system_text", "result_metric_layout"} <= set(driver.suite_stage_ids("context"))


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
    zoom_calls = []
    gage_receipt = {"fixture": "synthetic_dispatch_receipt_not_browser_evidence"}
    browser = SimpleNamespace(close=lambda: closed.append(True))

    @contextmanager
    def playwright():
        yield SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_kwargs: browser))

    monkeypatch.setattr(driver, "sync_playwright", playwright)
    for stage, name in STAGE_CALLS.items():

        def invoke(*_args, _stage=stage, **_kwargs):
            calls.append(_stage)
            if _stage in {"bo_dataset_import", "bo_xy_gpr_navigation"}:
                assert _kwargs == {"isolated_workspace": True}
            if _stage == "localization_shell":
                raise LegacyBoundary()
            if _stage == "doe_rsm_completion":
                return {"design_id": "synthetic-design", "analysis_id": "synthetic-analysis"}
            if _stage == "gage_six_panel":
                return gage_receipt

        monkeypatch.setattr(driver, name, invoke)

    def verify_gage_zoom(*args, **kwargs):
        assert args[-1] is gage_receipt
        assert calls[-1] == "gage_six_panel"
        zoom_calls.append("gage_six_panel")

    monkeypatch.setattr(driver, "verify_gage_six_panel_zoom", verify_gage_zoom)
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
    assert zoom_calls == (["gage_six_panel"] if "gage_six_panel" in expected else [])
    assert closed == [True]


@pytest.fixture
def runner_boundaries(driver, monkeypatch):
    events = []

    def run(command, **kwargs):
        events.append(("build", command, kwargs))
        assert kwargs["check"] is True
        output = Path(command[command.index("--outDir") + 1])
        assert not output.exists(), "A workflow must never reuse stale built assets"
        output.mkdir()
        (output / "index.html").write_text("<html>synthetic built UI</html>", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    def start(command, **kwargs):
        events.append(("start", command, kwargs))
        return SimpleNamespace()

    monkeypatch.delenv("DATALAB_FRONTEND_DIST", raising=False)
    monkeypatch.setattr(driver, "npm_command", lambda: "synthetic-npm")
    monkeypatch.setattr(driver.subprocess, "run", run)
    monkeypatch.setattr(driver.subprocess, "Popen", start)
    monkeypatch.setattr(driver, "terminate_process", lambda _process: None)
    monkeypatch.setattr(driver, "wait_for_url", lambda *_args: None)
    monkeypatch.setattr(
        driver, "run_browser_flow", lambda *args, **kwargs: events.append(("flow", args, kwargs))
    )
    return events


@pytest.mark.parametrize("suite", ["full", "workflows", "context", "data", "prediction"])
def test_runner_builds_only_workflows_in_fresh_owned_directory(
    driver, monkeypatch, tmp_path, runner_boundaries, suite
):
    diagnostics = tmp_path / "evidence"
    workspace = tmp_path / "synthetic space \ud55c\uae00"
    monkeypatch.setattr(
        driver.sys,
        "argv",
        [
            "critical_path.py",
            "--suite",
            suite,
            "--workspace-root",
            str(workspace),
            "--diagnostics-root",
            str(diagnostics),
            "--backend-port",
            "18011",
            "--frontend-port",
            "15199",
            "--keep-workspace",
        ],
    )
    assert driver.main() == 0
    builds = [event for event in runner_boundaries if event[0] == "build"]
    assert len(builds) == (1 if suite == "workflows" else 0)
    backend = next(event for event in runner_boundaries if event[0] == "start")
    flow = next(event for event in runner_boundaries if event[0] == "flow")
    assert flow[1][0] == "http://127.0.0.1:15199"
    if suite == "workflows":
        assert runner_boundaries[0][0] == "build"
        command = builds[0][1]
        assert command[:7] == [
            "synthetic-npm",
            "--prefix",
            "frontend",
            "run",
            "build",
            "--",
            "--outDir",
        ]
        output = Path(command[7])
        assert output.parent.parent == workspace
        assert output.name == "frontend-dist"
        assert builds[0][2]["env"]["VITE_API_BASE_URL"] == "/"
        assert backend[2]["env"]["DATALAB_FRONTEND_DIST"] == str(output)
        assert flow[2]["built_workflow_base_url"] == "http://127.0.0.1:18011"
        manifest = json.loads((diagnostics / "suite-manifest.json").read_text(encoding="utf-8"))
        assert manifest.get("frontend_modes") == {
            "bo_dataset_import": "built",
            "bo_profile_constraints": "built",
            "chart_interactions": "dev",
            "result_chart_models": "dev",
            "pilot_groups": "built",
            "fractional_completion": "built",
            "doe_rsm_completion": "built",
            "doe_browser_zoom": "built",
            "gage_followup": "built",
            "gage_six_panel": "built",
            "bo_noise_extension": "built",
            "desktop_resize": "dev",
            "localization_shell": "built",
            "legacy_workflow": "dev",
        }
    else:
        assert "DATALAB_FRONTEND_DIST" not in backend[2]["env"]
        assert flow[2].get("built_workflow_base_url") is None


@pytest.mark.parametrize("flag", ONLY_FLAGS)
def test_focused_checks_keep_source_frontend(
    driver, monkeypatch, tmp_path, runner_boundaries, flag
):
    monkeypatch.setattr(
        driver.sys,
        "argv",
        ["critical_path.py", f"--{flag}-only", "--workspace-root", str(tmp_path)],
    )
    assert driver.main() == 0
    assert not any(event[0] == "build" for event in runner_boundaries)
    flow = next(event for event in runner_boundaries if event[0] == "flow")
    assert flow[2].get("built_workflow_base_url") is None


def test_workflow_build_resolves_relative_output_for_npm_script_directory(
    driver, monkeypatch, tmp_path, runner_boundaries
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        driver.sys,
        "argv",
        ["critical_path.py", "--suite", "workflows", "--workspace-root", "relative workspace"],
    )
    assert driver.main() == 0
    build = next(event for event in runner_boundaries if event[0] == "build")
    output = Path(build[1][-1])
    assert output.is_absolute(), "npm scripts resolve relative --outDir against frontend/"
    assert output.parent.parent == tmp_path / "relative workspace"


@pytest.mark.parametrize("failure", ["command_failed", "missing_output"])
def test_workflow_build_failure_stops_before_servers_and_browser(
    driver, monkeypatch, tmp_path, runner_boundaries, failure
):
    def fail(command, **_kwargs):
        if failure == "command_failed":
            raise subprocess.CalledProcessError(1, command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(driver.subprocess, "run", fail)
    monkeypatch.setattr(
        driver.sys,
        "argv",
        ["critical_path.py", "--suite", "workflows", "--workspace-root", str(tmp_path)],
    )
    assert driver.main() == 1
    assert not runner_boundaries


def test_workflow_dispatch_routes_dev_fixtures_without_moving_built_journeys(
    driver, monkeypatch, tmp_path
):
    calls = []
    navigations = []
    closed = []

    def navigate(url, **_kwargs):
        navigations.append(url)
        raise LegacyBoundary()

    context = SimpleNamespace(
        add_init_script=lambda _script: None,
        new_page=lambda: SimpleNamespace(goto=navigate),
    )
    browser = SimpleNamespace(
        close=lambda: closed.append(True), new_context=lambda **_kwargs: context
    )

    @contextmanager
    def playwright():
        yield SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_kwargs: browser))

    monkeypatch.setattr(driver, "sync_playwright", playwright)
    for stage, name in STAGE_CALLS.items():

        def invoke(*args, _stage=stage, **_kwargs):
            calls.append((_stage, args[1]))
            if _stage == "doe_rsm_completion":
                return {"design_id": "synthetic-design", "analysis_id": "synthetic-analysis"}
            if _stage == "gage_six_panel":
                return {"fixture": "synthetic"}

        monkeypatch.setattr(driver, name, invoke)
    monkeypatch.setattr(driver, "verify_gage_six_panel_zoom", lambda *_args: None)
    diagnostics = SimpleNamespace(root=tmp_path, step=lambda _label: None)
    with pytest.raises(LegacyBoundary):
        driver.run_browser_flow(
            "http://source",
            diagnostics,
            "http://built",
            suite="workflows",
            built_workflow_base_url="http://built",
        )
    assert calls == [
        ("bo_dataset_import", "http://built"),
        ("bo_profile_constraints", "http://built"),
        ("chart_interactions", "http://source"),
        ("result_chart_models", "http://source"),
        ("pilot_groups", "http://built"),
        ("fractional_completion", "http://built"),
        ("doe_rsm_completion", "http://built"),
        ("doe_browser_zoom", "http://built"),
        ("gage_followup", "http://built"),
        ("gage_six_panel", "http://built"),
        ("bo_noise_extension", "http://built"),
        ("desktop_resize", "http://source"),
        ("localization_shell", "http://built"),
    ]
    assert navigations == ["http://source"]
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


def test_vector_context_includes_actual_target_curve_entry_and_recommendations():
    source = (ROOT / "tests/e2e/bo_vector_history.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    entry = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "verify_bo_vector_history"
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "verify_target_curve_recommendation"
        for node in ast.walk(entry)
    )
    target = (ROOT / "tests/e2e/bo_target_curve_recommendation.py").read_text(encoding="utf-8")
    assert "curve_policy=True" in target
    assert "verify_bo_vector_entry" in target
    assert "verify_desirability_review" in target
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "verify_persistent_planning"
        for node in ast.walk(entry)
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "verify_augmentation"
        for node in ast.walk(entry)
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "verify_mixed_workflow"
        for node in ast.walk(entry)
    )


def test_context_keeps_regular_and_auto_evidence_without_duplicate_profile_fit():
    tree = ast.parse((ROOT / "tests/e2e/bo_vector_history.py").read_text(encoding="utf-8"))
    entry = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "verify_bo_vector_history"
    )
    for name in ("verify_persistent_planning", "verify_mixed_workflow"):
        calls = [
            node
            for node in ast.walk(entry)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == name
        ]
        evidence = [
            node
            for node in calls
            if any(
                keyword.arg == "auto_evidence_only"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            )
        ]
        ordinary = [
            node
            for node in calls
            if all(
                keyword.arg not in {"auto_evidence_only", "profile_constraints_only"}
                for keyword in node.keywords
            )
        ]
        constrained = [
            node
            for node in calls
            if any(
                keyword.arg == "profile_constraints_only"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            )
        ]
        assert len(evidence) == 1, name
        assert len(ordinary) == 1, name
        assert not constrained, name
        assert len(calls) == 2, name


def test_profile_stage_selects_existing_constrained_only_journey(driver, monkeypatch, tmp_path):
    planning = importlib.import_module("bo_persistent_planning")
    calls = []
    browser = object()

    def verify(*args, **kwargs):
        calls.append((args, kwargs))
        return {"synthetic": True, "fit_posts": 1}

    monkeypatch.setattr(planning, "verify_persistent_planning", verify)
    assert planning.verify_profile_constraints(browser, "http://built", tmp_path) == {
        "synthetic": True,
        "fit_posts": 1,
    }
    assert calls == [((browser, "http://built", tmp_path), {"profile_constraints_only": True})]


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
    assert aggregate["if"] == (
        "always() && inputs.generate_linux_locks != true && inputs.browser_diagnostics_only != true"
    )
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
    assert diagnostic["strategy"]["matrix"]["suite"] == ["context", "workflows", "prediction"]
    assert diagnostic["strategy"]["fail-fast"] is False
    assert "inputs.browser_diagnostics == true" in diagnostic["if"]
    assert "needs" not in diagnostic
    triggers = workflow.get("on", workflow.get(True))
    diagnostic_only = triggers["workflow_dispatch"]["inputs"]["browser_diagnostics_only"]
    assert diagnostic_only["type"] == "boolean"
    assert diagnostic_only["default"] is False
    for name in ("windows", "windows-e2e", "linux", "python311", "linux-release", "release-ready"):
        assert "inputs.browser_diagnostics == true" not in jobs[name]["if"]
        assert "inputs.browser_diagnostics_only != true" in jobs[name]["if"]
    assert set(jobs["release-ready"]["needs"]) == {
        "windows",
        "e2e",
        "linux",
        "python311",
        "linux-release",
        "dependency-security",
        "gp-resources",
    }
    command = next(
        step["run"] for step in diagnostic["steps"] if step.get("name") == "Existing browser suite"
    )
    assert "--suite ${{ matrix.suite }}" in command
    assert "--diagnostics-root" in command


def test_early_windows_diagnostics_preserve_required_native_gate():
    jobs = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    diagnostic = jobs["windows-browser-diagnostics"]
    assert diagnostic["runs-on"] == "windows-latest"
    assert "inputs.browser_diagnostics == true" in diagnostic["if"]
    assert "needs" not in diagnostic
    assert diagnostic["permissions"] == {"contents": "read"}
    commands = [step.get("run", "") for step in diagnostic["steps"]]
    assert any("e2e.ps1 -Suite workflows" in command for command in commands)
    assert any("-DiagnosticsRoot" in command for command in commands)
    assert jobs["windows-e2e"]["needs"] == "windows"
    assert {"windows", "e2e"} <= set(jobs["release-ready"]["needs"])
    assert "windows-browser-diagnostics" not in jobs["release-ready"]["needs"]


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
        assert jobs[name]["if"] == (
            "always() && inputs.generate_linux_locks != true"
            " && inputs.browser_diagnostics_only != true"
        )
    for name in (
        "security-python",
        "security-npm",
        "windows",
        "windows-e2e",
        "linux",
        "python311",
        "linux-release",
    ):
        assert jobs[name]["if"] == (
            "inputs.generate_linux_locks != true && inputs.browser_diagnostics_only != true"
        )
    assert jobs["release-ready"]["needs"] == [
        "windows",
        "e2e",
        "linux",
        "python311",
        "linux-release",
        "dependency-security",
        "gp-resources",
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
