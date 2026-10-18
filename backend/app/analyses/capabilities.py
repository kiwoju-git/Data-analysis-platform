"""Offline joins of execution and report declarations, never runtime eligibility."""

from __future__ import annotations

import ast
from dataclasses import asdict
from pathlib import Path
from typing import Any, get_args

from app.analyses.registry import LEGACY_METHOD_ID_ALIASES, METHOD_VERSIONS, analysis_method_catalog
from app.api.v1.schemas.analyses import OneWayAnovaOptions
from app.api.v1.schemas.reports import ReportSourceKind
from app.core import doe_capabilities
from app.core.runtime_contract import API_CONTRACT_VERSION
from app.services.analysis_method_handlers import METHOD_EXECUTION_HANDLER_SPECS
from app.services.completed_prediction_report import COMPLETED_PREDICTION_REPORT_DEFINITION
from app.services.dedicated_report_renderers import DEFINITIONS
from app.services.report_contract import ReportDefinition
from app.services.report_coverage import report_definitions
from app.services.stored_prediction_report import PREDICTION_REPORT_DEFINITION
from app.storage.metadata import SCHEMA_VERSION

# Dedicated APIs have no generic runner. Bind their actual function/decorator,
# not another manually maintained URL or availability list.
DEDICATED_ENTRY_POINTS = {
    "regression.predict": ("regression_models", "create_regression_predictions_route"),
    "doe.factorial_design": ("doe_designs", "create_factorial_design_route"),
    "doe.general_factorial_design": ("doe_designs", "create_general_factorial_design_route"),
    "doe.latin_hypercube": ("doe_designs", "create_latin_hypercube_design_route"),
    "doe.response_surface": ("doe_designs", "create_response_surface_design_route"),
    "doe.response_optimizer": ("doe_designs", "create_response_optimizer_route"),
    "doe.bayesian_optimization": ("bayesian_studies", "create_bayesian_study_route"),
}
SUBWORKFLOW_ENTRY_POINTS = {
    "regression.predict_pasted": ("regression_models", "create_regression_pasted_prediction_route"),
    "regression.linear_model_optimizer": (
        "regression_models",
        "create_regression_response_optimization_route",
    ),
}


def _source_tree(root: Path, relative: str) -> ast.Module:
    return ast.parse((root / relative).read_text(encoding="utf-8"), filename=relative)


def _entry_point(root: Path, module: str, function: str) -> dict[str, str]:
    relative = f"backend/app/api/v1/{module}.py"
    tree = _source_tree(root, relative)
    prefix: str | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "router" for target in node.targets
            )
            and isinstance(node.value, ast.Call)
        ):
            prefix = next(
                (ast.literal_eval(kw.value) for kw in node.value.keywords if kw.arg == "prefix"), ""
            )
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) or node.name != function:
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "router"
                and decorator.func.attr == "post"
                and decorator.args
                and prefix is not None
            ):
                path = ast.literal_eval(decorator.args[0])
                if isinstance(path, str):
                    return {
                        "route": "/api/v1" + prefix + path,
                        "handler": function,
                        "source": relative,
                    }
    raise ValueError(f"capability_route_missing:{module}:{function}")


def _generic_runners(root: Path) -> dict[str, str]:
    tree = _source_tree(root, "backend/app/services/analysis_runs.py")
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "_METHOD_EXECUTION_HANDLERS"
            and isinstance(node.value, ast.Call)
            and node.value.args
            and isinstance(node.value.args[0], ast.Dict)
        ):
            mapping = node.value.args[0]
            result = {}
            for key, value in zip(mapping.keys, mapping.values, strict=True):
                if (
                    not isinstance(key, ast.Constant)
                    or not isinstance(key.value, str)
                    or not isinstance(value, ast.Name)
                ):
                    raise ValueError("capability_runner_shape_invalid")
                if key.value in result:
                    raise ValueError("capability_runner_duplicate")
                result[key.value] = value.id
            return result
    raise ValueError("capability_runner_map_missing")


def _report(definition: ReportDefinition, source_kind: str) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        **asdict(definition),
        "level": "assessed_from_exact_stored_payload",
        "historical_reading": "declared_schemas_only_no_rewrite",
    }


def backend_capability_facts(root: Path) -> dict[str, Any]:
    """Read bounded repository source files only; no database or application startup."""
    catalog = analysis_method_catalog()
    runners = _generic_runners(root)
    specs = {item.method_id: item for item in METHOD_EXECUTION_HANDLER_SPECS}
    generic = {item.method_id for item in catalog.methods if item.execution_mode != "dedicated"}
    dedicated = {item.method_id for item in catalog.methods if item.execution_mode == "dedicated"}
    if set(runners) != set(specs) or generic != set(specs):
        raise ValueError("capability_generic_handler_mismatch")
    if dedicated != set(DEDICATED_ENTRY_POINTS):
        raise ValueError("capability_dedicated_handler_mismatch")
    if any(
        alias in generic | dedicated | set(SUBWORKFLOW_ENTRY_POINTS)
        or target not in generic | dedicated
        for alias, target in LEGACY_METHOD_ID_ALIASES.items()
    ):
        raise ValueError("capability_legacy_alias_mismatch")
    definitions = report_definitions()
    if set(definitions) != generic:
        raise ValueError("capability_generic_report_mismatch")
    report_by_method = {key: [_report(value, "analysis_run")] for key, value in definitions.items()}
    for family, definition in DEFINITIONS.items():
        source = (
            "lhs_design_revision"
            if family == "lhs"
            else "bayesian_history_revision"
            if family == "bayesian"
            else "regression_prediction"
            if family == "doe_prediction"
            else "doe_optimizer_result"
            if "optimizer" in family
            else "doe_analysis"
        )
        owners = (
            ("doe.factorial_design", "doe.general_factorial_design")
            if family == "doe_prediction"
            else (definition.method_id,)
        )
        for owner in owners:
            report_by_method.setdefault(owner, []).append(_report(definition, source))
    for owner in ("regression.predict", "regression.predict_pasted"):
        report_by_method[owner] = [_report(PREDICTION_REPORT_DEFINITION, "regression_prediction")]
    for owner in ("regression.gaussian_process", "regression.partial_least_squares"):
        report_by_method[owner].append(
            _report(COMPLETED_PREDICTION_REPORT_DEFINITION, "regression_prediction")
        )
    methods = []
    for method in catalog.methods:
        item = method.model_dump(mode="json", exclude={"report_contract"})
        item["entry_kind"] = "catalog_method"
        item["reports"] = report_by_method.pop(method.method_id)
        if method.method_id in specs:
            spec = specs[method.method_id]
            if (
                spec.method_version != method.method_version
                or spec.result_summary_type != definitions[method.method_id].summary_type
            ):
                raise ValueError(f"capability_handler_contract_mismatch:{method.method_id}")
            item["entry_point"] = {
                "route": "/api/v1/analysis-runs",
                "handler": runners[method.method_id],
                "source": "backend/app/services/analysis_runs.py",
            }
        else:
            item["entry_point"] = _entry_point(root, *DEDICATED_ENTRY_POINTS[method.method_id])
        methods.append(item)
    subworkflows = []
    for method_id, entry in SUBWORKFLOW_ENTRY_POINTS.items():
        subworkflows.append(
            {
                "method_id": method_id,
                "method_version": METHOD_VERSIONS[method_id],
                "entry_kind": "subworkflow",
                "source_prerequisite": "regression_model",
                "entry_point": _entry_point(root, *entry),
                "reports": report_by_method.pop(method_id),
            }
        )
    if report_by_method or set(METHOD_VERSIONS) != set(specs) | dedicated | set(
        SUBWORKFLOW_ENTRY_POINTS
    ) | set(LEGACY_METHOD_ID_ALIASES):
        raise ValueError("capability_unclassified_method")
    return {
        "schema_version": 1,
        "api_contract_version": API_CONTRACT_VERSION,
        "metadata_schema_version": SCHEMA_VERSION,
        "methods": methods,
        "subworkflows": subworkflows,
        "legacy_aliases": dict(sorted(LEGACY_METHOD_ID_ALIASES.items())),
        "report_source_kinds": list(get_args(ReportSourceKind)),
        "limits": {
            key: getattr(doe_capabilities, key)
            for key in (
                "LATIN_HYPERCUBE_FACTOR_LIMIT",
                "BAYESIAN_STUDY_FACTOR_LIMIT",
                "FACTORIAL_AUTHORING_FACTOR_LIMIT",
                "GENERAL_FACTORIAL_AUTHORING_FACTOR_LIMIT",
                "RESPONSE_SURFACE_CCD_FACTOR_LIMIT",
                "FACTORIAL_RUN_LIMIT",
                "GENERAL_FACTORIAL_RUN_LIMIT",
            )
        },
        "option_policies": {
            "anova_posthoc_default": OneWayAnovaOptions.model_fields["posthoc_policy"].default,
            "normality_grouping": "not_supported",
            "graphical_summary_input": "numeric_ungrouped",
            "factorial_selection": "full_design_only",
            "attribute_phase_2": "eligible_frozen_limit_set_required",
            "two_variances_brown_forsythe_ratio_ci": "not_provided",
        },
    }
