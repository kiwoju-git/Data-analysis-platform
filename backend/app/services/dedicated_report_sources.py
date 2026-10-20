"""Exact immutable dedicated-workflow sources for the shared report center."""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any, Literal
from urllib.parse import urlencode

from pydantic import ValidationError

from app.api.v1.schemas.analyses import RegressionResponseOptimizationResponse
from app.api.v1.schemas.doe_model_workflow import DoePredictionResponse
from app.api.v1.schemas.reports import (
    BayesianHistoryReportSource,
    DoeAnalysisReportSource,
    DoeOptimizerReportSource,
    LhsDesignReportSource,
    RegressionPredictionReportSource,
    ReportSourceDescriptor,
    ReportSourceList,
    ReportSourceRef,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.i18n.report_text import ReportLocale
from app.services.analysis_report_source import _safe_owned_path, load_analysis_report_source
from app.services.dedicated_report_readers import (
    exact_design_version,
    invalid,
    parsed,
    read_bayesian,
    read_lhs,
)
from app.services.dedicated_report_renderers import (
    DEFINITIONS,
    render_bayesian_body,
    render_doe_analysis_body,
    render_doe_prediction_body,
    render_lhs_body,
    render_optimizer_body,
    render_regression_optimizer_body,
)
from app.services.doe_factorial_analysis import get_factorial_analysis
from app.services.doe_response_surface_analysis import get_response_surface_analysis
from app.services.general_factorial_designs import get_general_factorial_analysis
from app.services.regression_response_optimizer import _validate_restore_relationship
from app.services.report_source_contract import VerifiedReportSource, report_source_sha256
from app.services.response_optimizer import get_response_optimizer
from app.services.rsm_plot_views import read_rsm_plot_view
from app.storage.factorial_analysis_assets import get_asset
from app.storage.metadata import (
    get_experiment_design_analysis_record,
    get_regression_model_record,
    metadata_db_path,
)

_FAMILIES = {
    "doe.factorial_design": "factorial",
    "doe.general_factorial_design": "general_factorial",
    "doe.response_surface": "response_surface",
}


def prepare_dedicated_report_source(
    settings: Settings, source: ReportSourceRef, locale: ReportLocale
) -> VerifiedReportSource:
    try:
        return _prepare(settings, source, locale)
    except (ValidationError, KeyError, TypeError, ValueError, ArithmeticError, OSError) as exc:
        raise invalid() from exc


def _prepare(
    settings: Settings, source: ReportSourceRef, locale: ReportLocale
) -> VerifiedReportSource:
    payload: dict[str, Any]
    stale = False
    storage: Literal["analysis", "doe", "managed"] = "doe"
    if source.kind == "doe_analysis":
        payload, title, created = _doe_analysis(settings, source)
        body, definition = (
            render_doe_analysis_body(payload, source.family, locale),
            DEFINITIONS[source.family],
        )
        owner, target = (
            str(source.analysis_id),
            "/analysis/doe/" + payload["provenance"]["method_id"],
        )
    elif source.kind == "doe_optimizer_result":
        ref = source.optimizer
        if ref.workflow == "response_surface":
            record = get_experiment_design_analysis_record(
                settings.workspace_root, str(ref.optimization_id)
            )
            if record is None or record.result_sha256 != ref.expected_source_sha256:
                raise invalid("report_source_changed")
            response = get_response_optimizer(settings, ref.design_id, ref.optimization_id)
            envelope = response.model_dump(mode="json")
            if (
                response.design_version_id != ref.design_version_id
                or response.design_sha256 != ref.design_sha256
                or response.source_bundle_sha256 != ref.source_bundle_sha256
            ):
                raise invalid("report_source_changed")
            config = parsed(record.config_json)
            supplied = [
                {
                    "analysis_id": str(item.analysis_id),
                    "analysis_sha256": item.analysis_sha256,
                    "response_revision_id": str(item.response_revision.response_revision_id),
                    "response_revision_sha256": item.response_revision.response_revision_sha256,
                }
                for item in ref.source_dependencies
            ]
            actual = []
            for objective in config["request"]["objectives"]:
                dependency = get_experiment_design_analysis_record(
                    settings.workspace_root, objective["source_analysis_id"]
                )
                if dependency is None:
                    raise invalid("report_source_changed")
                actual.append(
                    {
                        "analysis_id": dependency.analysis_id,
                        "analysis_sha256": dependency.result_sha256,
                        "response_revision_id": dependency.response_revision_id,
                        "response_revision_sha256": dependency.response_revision_sha256,
                    }
                )
            if actual != supplied:
                raise invalid("report_source_changed")
            payload = {
                "result": envelope["result"],
                "provenance": {
                    **{key: value for key, value in envelope.items() if key != "result"},
                    "config": config,
                    "source": source.model_dump(mode="json"),
                },
            }
            title, created, owner, target = (
                "Response optimizer",
                response.created_at,
                str(ref.optimization_id),
                "/analysis/doe/doe.response_optimizer",
            )
            body, definition = (
                render_optimizer_body(payload, locale),
                DEFINITIONS["response_optimizer"],
            )
        else:
            stored = load_analysis_report_source(settings, ref.analysis_id)
            if (
                stored.record.method_id != "regression.linear_model_optimizer"
                or stored.record.result_sha256 != ref.expected_source_sha256
            ):
                raise invalid("report_source_changed")
            response_reg = RegressionResponseOptimizationResponse.model_validate(
                stored.envelope.result
            )
            _validate_restore_relationship(
                response_reg.model_id,
                ref.analysis_id,
                parsed(stored.record.config_json),
                response_reg,
            )
            model = get_regression_model_record(settings.workspace_root, str(response_reg.model_id))
            if (
                model is None
                or model.manifest_sha256 != response_reg.model_manifest_sha256
                or model.dataset_version_id != str(response_reg.source_dataset_version_id)
            ):
                raise invalid("report_source_changed")
            manifest_path = _safe_owned_path(
                settings.workspace_root, model.manifest_path, require_file=True
            )
            if (
                manifest_path.stat().st_size > 16 * 1024 * 1024
                or hashlib.sha256(manifest_path.read_bytes()).hexdigest() != model.manifest_sha256
            ):
                raise invalid("report_source_changed")
            payload = {
                "result": response_reg.result,
                "provenance": {
                    **response_reg.model_dump(mode="json", exclude={"result"}),
                    "config": parsed(stored.record.config_json),
                    "source": source.model_dump(mode="json"),
                },
            }
            title, created, owner, target, storage, stale = (
                "Regression response optimizer",
                stored.record.created_at,
                str(ref.analysis_id),
                "/analysis/regression/regression.linear_model_optimizer",
                "analysis",
                stored.record.stale,
            )
            body, definition = (
                render_regression_optimizer_body(payload, locale),
                DEFINITIONS["regression_optimizer"],
            )
    elif source.kind == "lhs_design_revision":
        payload, title, created = read_lhs(settings, source)
        payload["provenance"] = {
            "source": source.model_dump(mode="json"),
            "created_at": created,
            **payload["owner"],
        }
        owner, target, storage = (
            str(source.design_version_id),
            "/analysis/doe/doe.latin_hypercube",
            "managed",
        )
        body, definition = render_lhs_body(payload, locale), DEFINITIONS["lhs"]
    elif source.kind == "bayesian_history_revision":
        payload, title, created = read_bayesian(settings, source)
        payload["provenance"] = {
            "source": source.model_dump(mode="json"),
            "created_at": created,
            **payload["owner"],
        }
        owner, target, storage = (
            str(source.study_version_id),
            "/analysis/doe/doe.bayesian_optimization",
            "managed",
        )
        body, definition = render_bayesian_body(payload, locale), DEFINITIONS["bayesian"]
    elif source.kind == "regression_prediction" and source.prediction.storage == "doe_prediction":
        ref_prediction = source.prediction
        analysis_payload, title, _ = _doe_analysis(settings, ref_prediction.source)
        asset = get_asset(
            settings.workspace_root,
            str(ref_prediction.source.analysis_id),
            str(ref_prediction.prediction_id),
        )
        if (
            asset is None
            or asset[0].kind != "prediction"
            or asset[0].sha256 != ref_prediction.expected_source_sha256
            or asset[0].source_analysis_sha256 != ref_prediction.source.expected_source_sha256
        ):
            raise invalid("report_source_changed")
        prediction = DoePredictionResponse.model_validate_json(asset[1])
        if (
            prediction.prediction_id != ref_prediction.prediction_id
            or prediction.analysis_id != ref_prediction.source.analysis_id
            or prediction.design_id != ref_prediction.source.design_id
            or prediction.source_analysis_sha256 != ref_prediction.source.expected_source_sha256
            or prediction.response_revision_id
            != ref_prediction.source.response_revision.response_revision_id
            or prediction.response_revision_sha256
            != ref_prediction.source.response_revision.response_revision_sha256
        ):
            raise invalid("report_source_changed")
        payload = {
            "prediction": prediction.model_dump(mode="json"),
            "provenance": {
                "source": source.model_dump(mode="json"),
                "analysis": analysis_payload["provenance"],
            },
        }
        created, owner, target = (
            prediction.created_at,
            str(prediction.analysis_id),
            "/analysis/doe/" + analysis_payload["provenance"]["method_id"],
        )
        body, definition = (
            render_doe_prediction_body(payload, locale),
            DEFINITIONS["doe_prediction"],
        )
    else:
        raise invalid("report_source_unsupported")
    assert storage in {"doe", "analysis", "managed"}
    return VerifiedReportSource(
        source=source,
        payload=payload,
        title=title,
        created_at=created,
        stale=stale or report_source_is_stale(settings, source),
        open_target=_supported_open_target(source, target),
        storage_kind=storage,
        owner_id=owner,
        definition=definition,
        body=body,
    )


def _doe_analysis(
    settings: Settings, source: DoeAnalysisReportSource
) -> tuple[dict[str, Any], str, str]:
    record = get_experiment_design_analysis_record(settings.workspace_root, str(source.analysis_id))
    version = exact_design_version(settings, str(source.design_version_id))
    if record is None or version is None:
        raise invalid("report_source_not_found")
    if (
        record.result_sha256 != source.expected_source_sha256
        or record.design_version_id != str(source.design_version_id)
        or version.design_id != str(source.design_id)
        or version.design_sha256 != source.design_sha256
        or record.response_revision_id != str(source.response_revision.response_revision_id)
        or record.response_revision_sha256 != source.response_revision.response_revision_sha256
    ):
        raise invalid("report_source_changed")
    readers = {
        "factorial": get_factorial_analysis,
        "general_factorial": get_general_factorial_analysis,
        "response_surface": get_response_surface_analysis,
    }
    response = readers[source.family](settings, source.design_id, source.analysis_id)
    envelope = response.model_dump(mode="json")
    payload = {
        "result": envelope["result"],
        "provenance": {
            **{key: value for key, value in envelope.items() if key != "result"},
            "config": parsed(record.config_json),
            "design_factors": parsed(version.factors_json),
            "source": source.model_dump(mode="json"),
        },
    }
    if source.plot_view is not None:
        try:
            view = read_rsm_plot_view(
                settings,
                source.design_id,
                source.analysis_id,
                source.plot_view.plot_view_id,
                source.plot_view.expected_sha256,
            )
        except ApiError as exc:
            if exc.code == "doe_rsm_plot_view_not_found":
                raise invalid("report_source_changed") from exc
            raise
        payload["plot_view"] = view.model_dump(mode="json")
    return payload, str(envelope["response_name"]), record.created_at


def _descriptor(
    source: ReportSourceRef, title: str, created: str, target: str, stale: bool = False
) -> ReportSourceDescriptor:
    return ReportSourceDescriptor(
        source=source,
        source_ref_sha256=report_source_sha256(source),
        title=title,
        created_at=created,
        stale=stale,
        open_target=_supported_open_target(source, target),
    )


def _doe_ref(connection: sqlite3.Connection, analysis_id: str) -> DoeAnalysisReportSource:
    row = connection.execute(
        "SELECT a.analysis_id,a.method_id,a.design_version_id,a.result_sha256,"
        "v.design_id,v.design_sha256,dep.response_revision_id,"
        "dep.response_revision_sha256 FROM experiment_design_analyses a "
        "JOIN experiment_design_versions v ON v.design_version_id=a.design_version_id "
        "LEFT JOIN experiment_design_analysis_response_revisions dep "
        "ON dep.analysis_id=a.analysis_id WHERE a.analysis_id=?",
        (analysis_id,),
    ).fetchone()
    if row is None or row["method_id"] not in _FAMILIES:
        raise invalid("report_source_not_found")
    return DoeAnalysisReportSource.model_validate(
        dict(
            kind="doe_analysis",
            family=_FAMILIES[row["method_id"]],
            design_id=row["design_id"],
            design_version_id=row["design_version_id"],
            design_sha256=row["design_sha256"],
            analysis_id=row["analysis_id"],
            expected_source_sha256=row["result_sha256"],
            response_revision={
                "response_revision_id": row["response_revision_id"],
                "response_revision_sha256": row["response_revision_sha256"],
            },
        )
    )


def doe_prediction_source_descriptor(settings: Settings, asset_id: str) -> ReportSourceDescriptor:
    with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT asset_id,analysis_id,sha256,created_at "
            "FROM experiment_design_analysis_assets WHERE asset_id=? AND kind='prediction'",
            (asset_id,),
        ).fetchone()
        if row is None:
            raise invalid("report_source_not_found")
        analysis = _doe_ref(connection, row["analysis_id"])
    source = RegressionPredictionReportSource.model_validate(
        dict(
            kind="regression_prediction",
            prediction={
                "storage": "doe_prediction",
                "source": analysis,
                "prediction_id": row["asset_id"],
                "expected_source_sha256": row["sha256"],
            },
        )
    )
    return _descriptor(
        source,
        "Stored DOE prediction",
        row["created_at"],
        "/analysis/doe/" + {value: key for key, value in _FAMILIES.items()}[analysis.family],
        report_source_is_stale(settings, source),
    )


def list_dedicated_report_sources(
    settings: Settings, kind: str, limit: int = 50, offset: int = 0
) -> ReportSourceList:
    if not 1 <= limit <= 100 or offset < 0:
        raise invalid("report_source_pagination_invalid")
    with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
        connection.row_factory = sqlite3.Row
        candidates = _catalog_page(connection, kind, limit + 1, offset)
        items = [_catalog_descriptor(connection, row) for row in candidates[:limit]]
        items = [
            item.model_copy(update={"stale": _source_is_stale(connection, item.source)})
            for item in items
        ]
    return ReportSourceList(
        items=items, limit=limit, offset=offset, has_more=len(candidates) > limit
    )


def _catalog_page(
    connection: sqlite3.Connection, kind: str, count: int, offset: int
) -> list[sqlite3.Row]:
    queries = {
        "doe_analysis": (
            "SELECT 'doe_analysis' AS kind,analysis_id AS id,created_at,NULL AS extra "
            "FROM experiment_design_analyses WHERE method_id IN "
            "('doe.factorial_design','doe.general_factorial_design','doe.response_surface')"
            " UNION ALL SELECT 'rsm_plot_view',a.analysis_id,v.created_at,v.asset_id "
            "FROM experiment_design_analysis_assets v JOIN experiment_design_analyses a "
            "ON a.analysis_id=v.analysis_id WHERE v.kind='plot_view' "
            "AND a.method_id='doe.response_surface'"
        ),
        "doe_optimizer_result": (
            "SELECT 'rsm_optimizer' AS kind,analysis_id AS id,created_at,NULL AS extra "
            "FROM experiment_design_analyses "
            "WHERE method_id IN ('doe.response_optimizer','regression.response_optimizer') "
            "UNION ALL SELECT 'reg_optimizer',analysis_id,created_at,NULL FROM analysis_runs "
            "WHERE method_id='regression.linear_model_optimizer' AND status='succeeded'"
        ),
        "lhs_design_revision": (
            "SELECT 'lhs' AS kind,v.design_version_id AS id,v.created_at,NULL AS extra "
            "FROM experiment_design_versions v JOIN experiment_designs d "
            "ON d.design_id=v.design_id WHERE d.method_id='doe.latin_hypercube' "
            "UNION ALL SELECT 'lhs',v.design_version_id,r.created_at,r.response_revision_id "
            "FROM experiment_response_revisions r JOIN experiment_design_versions v "
            "ON v.design_version_id=r.design_version_id JOIN experiment_designs d "
            "ON d.design_id=v.design_id WHERE d.method_id='doe.latin_hypercube'"
        ),
        "bayesian_history_revision": (
            "SELECT 'bo' AS kind,history_revision_id AS id,created_at,NULL AS extra "
            "FROM bayesian_observation_history_revisions UNION ALL SELECT 'bo_recommendation',"
            "source_history_revision_id,created_at,recommendation_id FROM bayesian_recommendations "
            "UNION ALL SELECT 'bo_batch',source_history_revision_id,created_at,batch_id "
            "FROM bayesian_recommendation_batches"
        ),
    }
    if kind not in queries:
        raise invalid("report_source_unsupported")
    return connection.execute(
        "SELECT * FROM ("
        + queries[kind]
        + ") ORDER BY created_at DESC,id DESC,COALESCE(extra,'') DESC LIMIT ? OFFSET ?",
        (count, offset),
    ).fetchall()


def _catalog_descriptor(connection: sqlite3.Connection, row: sqlite3.Row) -> ReportSourceDescriptor:
    kind, identifier, created, extra = row["kind"], row["id"], row["created_at"], row["extra"]
    source: ReportSourceRef
    if kind in {"doe_analysis", "rsm_plot_view"}:
        source = _doe_ref(connection, identifier)
        if kind == "rsm_plot_view":
            asset = connection.execute(
                "SELECT sha256 FROM experiment_design_analysis_assets "
                "WHERE analysis_id=? AND asset_id=? AND kind='plot_view'",
                (identifier, extra),
            ).fetchone()
            if asset is None:
                raise invalid("report_source_changed")
            source = DoeAnalysisReportSource.model_validate(
                {
                    **source.model_dump(),
                    "plot_view": {"plot_view_id": extra, "expected_sha256": asset[0]},
                }
            )
        return _descriptor(
            source,
            source.family + (" / saved plot view" if kind == "rsm_plot_view" else ""),
            created,
            "/analysis/doe/" + {value: key for key, value in _FAMILIES.items()}[source.family],
        )
    if kind == "reg_optimizer":
        result = connection.execute(
            "SELECT result_sha256,stale FROM analysis_runs WHERE analysis_id=?", (identifier,)
        ).fetchone()
        source = DoeOptimizerReportSource.model_validate(
            dict(
                kind="doe_optimizer_result",
                optimizer={
                    "workflow": "regression",
                    "analysis_id": identifier,
                    "expected_source_sha256": result[0],
                },
            )
        )
        return _descriptor(
            source,
            "Regression response optimizer",
            created,
            "/analysis/regression/regression.linear_model_optimizer",
            bool(result[1]),
        )
    if kind == "rsm_optimizer":
        result = connection.execute(
            "SELECT a.config_json,a.result_sha256,a.response_sha256,a.design_version_id,"
            "v.design_id,v.design_sha256 FROM experiment_design_analyses a "
            "JOIN experiment_design_versions v ON v.design_version_id=a.design_version_id "
            "WHERE analysis_id=?",
            (identifier,),
        ).fetchone()
        config = parsed(result["config_json"])
        dependencies = []
        for objective in config["request"]["objectives"]:
            dependency = connection.execute(
                "SELECT a.analysis_id,a.result_sha256,dep.response_revision_id,"
                "dep.response_revision_sha256 FROM experiment_design_analyses a "
                "LEFT JOIN experiment_design_analysis_response_revisions dep "
                "ON dep.analysis_id=a.analysis_id WHERE a.analysis_id=?",
                (objective["source_analysis_id"],),
            ).fetchone()
            if dependency is None:
                raise invalid("report_source_changed")
            dependencies.append(
                {
                    "analysis_id": dependency["analysis_id"],
                    "analysis_sha256": dependency["result_sha256"],
                    "response_revision": {
                        "response_revision_id": dependency["response_revision_id"],
                        "response_revision_sha256": dependency["response_revision_sha256"],
                    },
                }
            )
        source = DoeOptimizerReportSource.model_validate(
            dict(
                kind="doe_optimizer_result",
                optimizer={
                    "workflow": "response_surface",
                    "design_id": result["design_id"],
                    "design_version_id": result["design_version_id"],
                    "design_sha256": result["design_sha256"],
                    "optimization_id": identifier,
                    "expected_source_sha256": result["result_sha256"],
                    "source_bundle_sha256": result["response_sha256"],
                    "source_dependencies": dependencies,
                },
            )
        )
        return _descriptor(
            source, "Response optimizer", created, "/analysis/doe/doe.response_optimizer"
        )
    if kind == "lhs":
        result = connection.execute(
            "SELECT v.design_id,v.design_sha256,d.name FROM experiment_design_versions v "
            "JOIN experiment_designs d ON d.design_id=v.design_id WHERE v.design_version_id=?",
            (identifier,),
        ).fetchone()
        revisions = []
        if extra:
            revision = connection.execute(
                "SELECT response_sha256 FROM experiment_response_revisions "
                "WHERE response_revision_id=?",
                (extra,),
            ).fetchone()
            revisions.append(
                {"response_revision_id": extra, "response_revision_sha256": revision[0]}
            )
        source = LhsDesignReportSource.model_validate(
            dict(
                kind="lhs_design_revision",
                design_id=result["design_id"],
                design_version_id=identifier,
                expected_source_sha256=result["design_sha256"],
                response_revisions=revisions,
            )
        )
        return _descriptor(source, result["name"], created, "/analysis/doe/doe.latin_hypercube")
    result = connection.execute(
        "SELECT h.study_version_id,h.observation_history_sha256,v.study_id,"
        "v.definition_sha256,s.name FROM bayesian_observation_history_revisions h "
        "JOIN bayesian_study_versions v ON v.study_version_id=h.study_version_id "
        "JOIN bayesian_studies s ON s.study_id=v.study_id WHERE h.history_revision_id=?",
        (identifier,),
    ).fetchone()
    attachment: dict[str, Any] = {"kind": "none"}
    if kind in {"bo_recommendation", "bo_batch"}:
        table, id_column = (
            ("bayesian_recommendations", "recommendation_id")
            if kind == "bo_recommendation"
            else ("bayesian_recommendation_batches", "batch_id")
        )
        record = connection.execute(
            "SELECT result_sha256,json_extract(result_json,'$.result_payload_sha256') AS inner_rec,"
            f"json_extract(result_json,'$.result_sha256') AS inner_batch FROM {table} "
            f"WHERE {id_column}=?",
            (extra,),
        ).fetchone()
        attachment = {
            "kind": "recommendation" if kind == "bo_recommendation" else "batch",
            id_column: extra,
            "result_json_sha256": record["result_sha256"],
            "result_payload_sha256": record[
                "inner_rec" if kind == "bo_recommendation" else "inner_batch"
            ],
        }
    source = BayesianHistoryReportSource.model_validate(
        dict(
            kind="bayesian_history_revision",
            study_id=result["study_id"],
            study_version_id=result["study_version_id"],
            definition_sha256=result["definition_sha256"],
            history_revision_id=identifier,
            expected_source_sha256=result["observation_history_sha256"],
            attachment=attachment,
        )
    )
    return _descriptor(source, result["name"], created, "/analysis/doe/doe.bayesian_optimization")


def report_source_is_stale(settings: Settings, source: ReportSourceRef) -> bool:
    """Compare metadata heads only; an old snapshot remains valid and readable."""
    with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
        connection.row_factory = sqlite3.Row
        return _source_is_stale(connection, source)


def _source_is_stale(connection: sqlite3.Connection, source: ReportSourceRef) -> bool:
    if source.kind == "regression_prediction":
        if source.prediction.storage == "doe_prediction":
            doe_prediction = source.prediction
            child = connection.execute(
                "SELECT kind,analysis_id,sha256,source_analysis_sha256 "
                "FROM experiment_design_analysis_assets WHERE asset_id=?",
                (str(doe_prediction.prediction_id),),
            ).fetchone()
            if (
                child is None
                or child[0] != "prediction"
                or child[1] != str(doe_prediction.source.analysis_id)
                or child[2] != doe_prediction.expected_source_sha256
                or child[3] != doe_prediction.source.expected_source_sha256
            ):
                return True
            return _source_is_stale(connection, doe_prediction.source)
        if source.prediction.storage == "completed_prediction":
            completed = source.prediction
            child = connection.execute(
                "SELECT kind,analysis_id,sha256 FROM analysis_artifacts WHERE artifact_id=?",
                (str(completed.prediction_artifact_id),),
            ).fetchone()
            kind = (
                "gp_completed_prediction"
                if completed.family == "gaussian_process"
                else "pls_completed_prediction"
            )
            if (
                child is None
                or child[0] != kind
                or child[1] != str(completed.source_analysis_id)
                or child[2] != completed.expected_source_sha256
            ):
                return True
            identifier = completed.source_analysis_id
            expected_hash = completed.source_result_sha256
        else:
            assert source.prediction.storage == "analysis_run"
            identifier = source.prediction.analysis_id
            expected_hash = source.prediction.expected_source_sha256
        row = connection.execute(
            "SELECT stale,result_sha256 FROM analysis_runs WHERE analysis_id=?", (str(identifier),)
        ).fetchone()
        return row is None or bool(row[0]) or row[1] != expected_hash
    if source.kind == "analysis_run":
        row = connection.execute(
            "SELECT stale FROM analysis_runs WHERE analysis_id=?", (str(source.analysis_id),)
        ).fetchone()
        return row is None or bool(row[0])
    if source.kind == "doe_optimizer_result" and source.optimizer.workflow == "regression":
        row = connection.execute(
            "SELECT stale FROM analysis_runs WHERE analysis_id=?",
            (str(source.optimizer.analysis_id),),
        ).fetchone()
        return row is None or bool(row[0])
    if source.kind == "bayesian_history_revision":
        attachment = source.attachment
        if attachment.kind != "none":
            table, id_column, child_id = (
                ("bayesian_recommendations", "recommendation_id", attachment.recommendation_id)
                if attachment.kind == "recommendation"
                else ("bayesian_recommendation_batches", "batch_id", attachment.batch_id)
            )
            child = connection.execute(
                "SELECT study_version_id,source_history_revision_id,"
                f"source_observation_history_sha256,result_sha256 FROM {table} "
                f"WHERE {id_column}=?",
                (str(child_id),),
            ).fetchone()
            if (
                child is None
                or child[0] != str(source.study_version_id)
                or child[1] != str(source.history_revision_id)
                or child[2] != source.expected_source_sha256
                or child[3] != attachment.result_json_sha256
            ):
                return True
        row = connection.execute(
            "SELECT h.history_revision_id,v.version_number,s.current_version "
            "FROM bayesian_study_versions v JOIN bayesian_studies s ON s.study_id=v.study_id "
            "LEFT JOIN bayesian_observation_history_heads h "
            "ON h.study_version_id=v.study_version_id "
            "WHERE v.study_version_id=?",
            (str(source.study_version_id),),
        ).fetchone()
        return row is None or row[0] != str(source.history_revision_id) or row[1] != row[2]
    if source.kind == "doe_optimizer_result":
        assert source.optimizer.workflow == "response_surface"
        version_id = source.optimizer.design_version_id
        revisions = [item.response_revision for item in source.optimizer.source_dependencies]
    elif source.kind == "doe_analysis":
        version_id, revisions = source.design_version_id, [source.response_revision]
        if source.plot_view is not None:
            view = connection.execute(
                "SELECT sha256,source_analysis_sha256 FROM experiment_design_analysis_assets "
                "WHERE analysis_id=? AND asset_id=? AND kind='plot_view'",
                (str(source.analysis_id), str(source.plot_view.plot_view_id)),
            ).fetchone()
            if (
                view is None
                or view[0] != source.plot_view.expected_sha256
                or view[1] != source.expected_source_sha256
            ):
                return True
    else:
        version_id, revisions = source.design_version_id, source.response_revisions
    version = connection.execute(
        "SELECT v.version_number,d.current_version FROM experiment_design_versions v "
        "JOIN experiment_designs d ON d.design_id=v.design_id WHERE v.design_version_id=?",
        (str(version_id),),
    ).fetchone()
    if version is None or version[0] != version[1]:
        return True
    for ref in revisions:
        row = connection.execute(
            "SELECT r.state,h.response_revision_id FROM experiment_response_revisions r "
            "LEFT JOIN experiment_response_heads h ON h.design_version_id=r.design_version_id "
            "AND h.response_name=r.response_name WHERE r.response_revision_id=?",
            (str(ref.response_revision_id),),
        ).fetchone()
        if row is None or row[0] != "completed" or row[1] != str(ref.response_revision_id):
            return True
    return False


def _supported_open_target(source: ReportSourceRef, fallback: str) -> str:
    if source.kind == "regression_prediction" and source.prediction.storage == "doe_prediction":
        return _supported_open_target(source.prediction.source, fallback)
    if source.kind == "doe_analysis" and source.family in {"factorial", "general_factorial"}:
        query = {"design_id": str(source.design_id), "analysis_id": str(source.analysis_id)}
        if source.family == "general_factorial":
            query["design_kind"] = "general"
        return "/analysis/doe/doe.factorial_design?" + urlencode(query)
    if (
        source.kind == "doe_analysis"
        and source.family == "response_surface"
        and source.plot_view is None
    ):
        return "/analysis/doe/doe.response_surface?" + urlencode(
            {"design_id": str(source.design_id), "analysis_id": str(source.analysis_id)}
        )
    if source.kind == "bayesian_history_revision":
        query = {"study_id": str(source.study_id)}
        if source.attachment.kind == "recommendation":
            query["recommendation_id"] = str(source.attachment.recommendation_id)
        elif source.attachment.kind == "batch":
            query["batch_id"] = str(source.attachment.batch_id)
        return "/analysis/doe/doe.bayesian_optimization?" + urlencode(query)
    return fallback
