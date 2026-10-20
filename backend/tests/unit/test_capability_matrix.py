"""Python-only declaration tests: Node AST checks are a separate explicit gate."""

from __future__ import annotations

import importlib.util
import json
import socket
import sqlite3
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.analyses import capabilities
from app.api.v1.schemas.analyses import (
    AttributeControlChartOptions,
    GraphicalSummaryOptions,
    OneWayAnovaOptions,
)
from app.api.v1.schemas.doe import DoeFactorialAnalysisCreateRequest
from app.core.config import Settings
from app.core.doe_capabilities import BAYESIAN_STUDY_FACTOR_LIMIT, LATIN_HYPERCUBE_FACTOR_LIMIT
from app.core.errors import ApiError
from app.services import doe_factorial_analysis
from app.services.analysis_runners_eda import (
    _reject_normality_grouping,
    _validate_graphical_summary_column,
)
from app.statistics.two_variances import TwoVariancesOptions, calculate_two_variances

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "capability_generator", ROOT / "scripts/generate_capability_matrix.py"
)
assert SPEC is not None and SPEC.loader is not None
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


@pytest.fixture(scope="module")
def facts() -> dict[str, Any]:
    return capabilities.backend_capability_facts(ROOT)


@pytest.fixture
def frontend() -> dict[str, Any]:
    saved = json.loads((ROOT / generator.OUTPUT_JSON).read_text(encoding="utf-8"))
    return {"domains": saved["domains"], "guidance_method_ids": saved["guidance_method_ids"]}


def test_backend_inventory_joins_actual_execution_reports_and_subworkflows(
    facts: dict[str, Any],
) -> None:
    methods = {item["method_id"]: item for item in facts["methods"]}
    assert len(methods) == 38
    assert sum(item["execution_mode"] == "dedicated" for item in methods.values()) == 7
    assert {item["method_id"] for item in facts["subworkflows"]} == {
        "regression.predict_pasted",
        "regression.linear_model_optimizer",
    }
    assert "regression.predict_manual" not in methods
    assert len(facts["report_source_kinds"]) == 6
    for item in methods.values():
        assert item["entry_point"]["route"].startswith("/api/v1/")
        assert item["reports"]
        assert item["execution_capability"]["cancellation_support"] in {
            "none",
            "cooperative",
            "process",
        }
        for report in item["reports"]:
            assert report["level"] == "assessed_from_exact_stored_payload"
            assert report["historical_reading"] == "declared_schemas_only_no_rewrite"
            assert all(
                any(section["core"] for section in variant["sections"])
                for variant in report["variants"]
            )
    gp = methods["regression.gaussian_process"]["reports"]
    assert {item["source_kind"] for item in gp} == {"analysis_run", "regression_prediction"}
    assert tuple(gp[0]["accepted_schemas"]) == (1, 2, 3)
    assert len(methods["doe.general_factorial_design"]["reports"]) == 2


def test_generation_core_never_starts_app_connects_network_or_opens_workspace(
    monkeypatch: pytest.MonkeyPatch,
    frontend: dict[str, Any],
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("generation must remain offline and workspace-free")

    monkeypatch.setattr(sqlite3, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(Settings, "__init__", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    matrix = generator.assemble_matrix(capabilities.backend_capability_facts(ROOT), frontend)
    assert len(matrix["methods"]) == 38
    assert matrix["evidence"] == "source_declarations_not_runtime_test_results"


def test_fresh_import_is_offline_without_app_lifespan() -> None:
    program = (
        "import sqlite3,socket,sys; from pathlib import Path; "
        f"sys.path.insert(0, {str(ROOT / 'backend')!r}); "
        "exec('def forbidden(*args, **kwargs):\\n raise AssertionError(\\\"unexpected I/O\\\")'); "
        "sqlite3.connect=forbidden; socket.create_connection=forbidden; "
        "socket.socket.connect=forbidden; "
        "from app.analyses.capabilities import backend_capability_facts; "
        f"assert len(backend_capability_facts(Path({str(ROOT)!r}))['methods'])==38; "
        "assert 'app.main' not in sys.modules; print('offline declarations verified')"
    )
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "offline declarations verified"


def test_generated_bytes_match_current_backend_and_are_deterministic(
    facts: dict[str, Any],
    frontend: dict[str, Any],
) -> None:
    matrix = generator.assemble_matrix(facts, frontend)
    first = generator.generated_outputs(matrix)
    assert first == generator.generated_outputs(generator.assemble_matrix(facts, frontend))
    for path, content in first.items():
        assert (ROOT / path).read_bytes() == content
        assert b"\r\n" not in content
    assert generator.check_or_write(ROOT, first, write=False) == []


def test_generated_outputs_explicitly_keep_lf_on_windows_checkout() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    for path in (generator.OUTPUT_JSON, generator.OUTPUT_MARKDOWN):
        assert f"{path.as_posix()} text eol=lf" in attributes


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("missing", "missing_placement"),
        ("duplicate", "duplicate_placement"),
        ("unknown", "unknown_placement"),
        ("guidance_missing", "missing_guidance"),
        ("guidance_unknown", "unknown_guidance"),
        ("guidance_duplicate", "duplicate_guidance"),
        ("domain_duplicate", "domain_order_invalid"),
        ("workflow_duplicate", "duplicate_workflow"),
    ],
)
def test_join_fails_closed_on_drift(
    facts: dict[str, Any],
    frontend: dict[str, Any],
    mutation: str,
    expected: str,
) -> None:
    source = deepcopy(frontend)
    first = source["domains"][0]["directMethodIds"]
    if mutation == "missing":
        first.pop()
    elif mutation == "duplicate":
        first.append(first[0])
    elif mutation == "unknown":
        first.append("regression.predict_manual")
    elif mutation == "guidance_missing":
        source["guidance_method_ids"].remove("eda.principal_components")
    elif mutation == "guidance_unknown":
        source["guidance_method_ids"].append("fake.method")
    elif mutation == "guidance_duplicate":
        source["guidance_method_ids"].append(source["guidance_method_ids"][0])
    elif mutation == "domain_duplicate":
        source["domains"].append(source["domains"][0])
    else:
        source["domains"][0]["directPlannedWorkflows"] = [{"id": first[0]}]
    with pytest.raises(ValueError, match=expected):
        generator.assemble_matrix(facts, source)


def test_roadmap_and_contextual_are_not_counted_as_available_methods(
    facts: dict[str, Any],
    frontend: dict[str, Any],
) -> None:
    matrix = generator.assemble_matrix(facts, frontend)
    workflows = {item["id"]: item for item in matrix["informational_workflows"]}
    assert workflows["hypothesis.comparability_assessment"]["visibility"] == "roadmap_only"
    assert workflows["quality.multivariate_monitoring"]["visibility"] == "roadmap_only"
    assert workflows["gaussian-process-surrogate"]["entry_kind"] == "contextual_information"
    assert "quality.two_variances" not in workflows
    methods = {item["method_id"]: item for item in matrix["methods"]}
    assert methods["regression.predict"]["placement"]["contextual"]
    assert methods["regression.predict"]["source_prerequisite"] == "regression_model"
    assert methods["regression.predict"]["availability"] == "available"
    assert len(matrix["methods"]) == 38


def test_check_never_writes_and_write_is_scoped_with_korean_space_path(tmp_path: Path) -> None:
    root = tmp_path / "한글 capability directory"
    root.mkdir()
    user_file = root / "user.txt"
    user_file.write_bytes(b"unchanged")
    output = {Path("generated/facts.json"): b'{"a":1}\n'}
    assert generator.check_or_write(root, output, write=False) == list(output)
    assert not (root / "generated").exists()
    assert generator.check_or_write(root, output, write=True) == list(output)
    assert generator.check_or_write(root, output, write=False) == []
    updated = {Path("generated/facts.json"): b'{"a":2}\n'}
    assert generator.check_or_write(root, updated, write=False) == list(updated)
    assert (root / "generated/facts.json").read_bytes() == output[Path("generated/facts.json")]
    assert user_file.read_bytes() == b"unchanged"


def test_actual_dedicated_route_missing_is_not_silently_omitted(tmp_path: Path) -> None:
    source = tmp_path / "backend/app/api/v1/example.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        'router = APIRouter(prefix="/example")\n@router.post("/{id}")\ndef create(): pass\n',
        encoding="utf-8",
    )
    assert (
        capabilities._entry_point(tmp_path, "example", "create")["route"] == "/api/v1/example/{id}"
    )
    with pytest.raises(ValueError, match="capability_route_missing"):
        capabilities._entry_point(tmp_path, "example", "not_registered")


def test_generic_runner_map_mismatch_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capabilities, "_generic_runners", lambda _root: {})
    with pytest.raises(ValueError, match="generic_handler_mismatch"):
        capabilities.backend_capability_facts(ROOT)


def test_legacy_alias_cannot_advertise_an_unknown_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capabilities, "LEGACY_METHOD_ID_ALIASES", {"legacy.unknown": "fake.method"})
    with pytest.raises(ValueError, match="legacy_alias_mismatch"):
        capabilities.backend_capability_facts(ROOT)


def test_conditional_claims_match_real_schema_and_validator_contracts(
    facts: dict[str, Any],
) -> None:
    policies = facts["option_policies"]
    assert (
        policies["anova_posthoc_default"]
        == OneWayAnovaOptions(response_column_id="response", group_column_id="group").posthoc_policy
        == "when_requested"
    )
    assert facts["limits"]["LATIN_HYPERCUBE_FACTOR_LIMIT"] == LATIN_HYPERCUBE_FACTOR_LIMIT == 10
    assert facts["limits"]["BAYESIAN_STUDY_FACTOR_LIMIT"] == BAYESIAN_STUDY_FACTOR_LIMIT == 10
    assert "group_column_id" not in GraphicalSummaryOptions.model_fields
    with pytest.raises(ValidationError):
        AttributeControlChartOptions(
            phase="phase_2", chart_type="c", count_definition="defects", count_column_id="count"
        )
    phase_2 = AttributeControlChartOptions(
        phase="phase_2",
        limit_set_id=uuid4(),
        chart_type="c",
        count_definition="defects",
        count_column_id="count",
    )
    assert phase_2.phase == "phase_2"
    with pytest.raises(ApiError) as raised:
        _reject_normality_grouping(SimpleNamespace(roles={}), {"group_column_id": "group"})
    assert raised.value.code == "normality_grouping_not_supported"
    with pytest.raises(ApiError) as raised:
        _validate_graphical_summary_column(
            SimpleNamespace(role="response", measurement_level="nominal", data_type="string")
        )
    assert raised.value.code == "graphical_summary_column_not_numeric"
    bf = calculate_two_variances([1, 2, 3, 4, 5], [1, 3, 5, 7, 9], TwoVariancesOptions())
    assert bf["ratio_interval"]["available"] is False
    assert bf["ratio_interval"]["reason"] == "not_provided_by_selected_method"


@pytest.mark.parametrize("manual", [True, False])
def test_screening_selection_remains_rejected_by_actual_service_guard(
    monkeypatch: pytest.MonkeyPatch,
    manual: bool,
) -> None:
    design = SimpleNamespace(fractional=None, screening={"stored": True})
    monkeypatch.setattr(doe_factorial_analysis, "get_factorial_design", lambda *_args: design)
    policy = (
        {"term_policies": [{"term_id": "factor_1", "disposition": "excluded"}]}
        if manual
        else {"method": "backward_elimination"}
    )
    request = DoeFactorialAnalysisCreateRequest.model_validate(
        {"response_name": "Y", "model_selection": policy}
    )
    with pytest.raises(ApiError) as raised:
        doe_factorial_analysis.create_factorial_analysis(None, uuid4(), request)
    expected = "term_selection" if manual else "model_selection"
    assert raised.value.code == f"doe_factorial_{expected}_unsupported_for_aliased_design"


@pytest.mark.parametrize("manual", [True, False])
def test_fractional_selection_reaches_response_dependency_loading(
    monkeypatch: pytest.MonkeyPatch,
    manual: bool,
) -> None:
    design_version_id = uuid4()
    design = SimpleNamespace(
        fractional={"stored": True},
        screening=None,
        design_version_id=design_version_id,
    )
    monkeypatch.setattr(doe_factorial_analysis, "get_factorial_design", lambda *_args: design)

    class DependencyLoadingReached(Exception):
        pass

    def stop_at_dependency(settings: object, **kwargs: object) -> None:
        assert settings is None
        assert kwargs == {
            "design_version_id": design_version_id,
            "response_name": "Y",
            "response_revision_id": None,
        }
        raise DependencyLoadingReached

    monkeypatch.setattr(
        doe_factorial_analysis, "load_response_revision_dependency", stop_at_dependency
    )
    policy = (
        {"term_policies": [{"term_id": "factor_1", "disposition": "excluded"}]}
        if manual
        else {"method": "backward_elimination"}
    )
    request = DoeFactorialAnalysisCreateRequest.model_validate(
        {"response_name": "Y", "model_selection": policy}
    )
    with pytest.raises(DependencyLoadingReached):
        doe_factorial_analysis.create_factorial_analysis(None, uuid4(), request)


def test_declared_report_sections_do_not_claim_all_payloads_are_full(facts: dict[str, Any]) -> None:
    from app.services.report_contract import ReportBody, ReportSection, assess_report_body
    from app.services.report_coverage import report_definitions

    definition = report_definitions()["eda.normality"]
    variant = definition.variants[0]
    assert any(not section.core for section in variant.sections)
    sections = tuple(
        ReportSection(
            section.section_id,
            section.section_id,
            "rendered" if section.core else "missing",
            "<table><tr><td>saved</td></tr></table>" if section.core else None,
            None if section.core else "legacy_section_unavailable",
        )
        for section in variant.sections
    )
    assert assess_report_body(definition, ReportBody(variant.variant_id, sections)) == "summary"
    assert (
        assess_report_body(definition, ReportBody(variant.variant_id, (), "schema_unsupported"))
        == "unsupported"
    )
    assert facts["methods"][0]["reports"][0]["level"] != "full"
