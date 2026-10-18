"""Generate checked-in capability facts from repository declarations, offline."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.analyses.capabilities import backend_capability_facts  # noqa: E402

OUTPUT_JSON = Path("frontend/src/generated/analysisCapabilities.json")
OUTPUT_MARKDOWN = Path("docs/generated/analysis_capability_matrix.md")


def assemble_matrix(facts: dict[str, Any], frontend: dict[str, Any]) -> dict[str, Any]:
    """Join canonical placement to backend facts; never infer live eligibility."""
    methods = {item["method_id"]: item for item in facts["methods"]}
    if len(methods) != len(facts["methods"]):
        raise ValueError("capability_duplicate_catalog_method")
    placements: dict[str, dict[str, Any]] = {}
    domains = frontend["domains"]
    seen_domains: set[str] = set()
    workflow_ids: set[str] = set()
    workflows: list[dict[str, Any]] = []

    def add_methods(
        ids: list[str], domain: str, family: str | None, contextual: bool
    ) -> None:
        for method_id in ids:
            if method_id not in methods:
                raise ValueError(f"capability_unknown_placement:{method_id}")
            if method_id in placements:
                raise ValueError(f"capability_duplicate_placement:{method_id}")
            placements[method_id] = {
                "domain_id": domain,
                "family_id": family,
                "contextual": contextual,
                "order": len(placements),
            }

    def add_workflows(
        items: list[dict[str, Any]], domain: str, family: str | None, kind: str
    ) -> None:
        for item in items:
            identifier = item["id"]
            if identifier in methods or identifier in workflow_ids:
                raise ValueError(f"capability_duplicate_workflow:{identifier}")
            workflow_ids.add(identifier)
            visibility = item.get("visibility", "navigation")
            if visibility not in {"navigation", "roadmap_only"}:
                raise ValueError("capability_workflow_visibility_invalid")
            workflows.append(
                {
                    **item,
                    "entry_kind": kind,
                    "domain_id": domain,
                    "family_id": family,
                    "visibility": visibility,
                }
            )

    orders = [domain["order"] for domain in domains]
    if orders != sorted(set(orders)):
        raise ValueError("capability_domain_order_invalid")
    for domain in domains:
        identifier = domain["id"]
        if identifier in seen_domains:
            raise ValueError("capability_duplicate_domain")
        seen_domains.add(identifier)
        add_methods(domain.get("directMethodIds", []), identifier, None, False)
        add_methods(domain.get("directContextualMethodIds", []), identifier, None, True)
        add_workflows(
            domain.get("directPlannedWorkflows", []),
            identifier,
            None,
            "planned_workflow",
        )
        add_workflows(
            domain.get("directContextualWorkflows", []),
            identifier,
            None,
            "contextual_information",
        )
        families: set[str] = set()
        for family in domain["families"]:
            family_id = family["id"]
            if family_id in families:
                raise ValueError("capability_duplicate_family")
            families.add(family_id)
            add_methods(family["methodIds"], identifier, family_id, False)
            add_methods(
                family.get("contextualMethodIds", []), identifier, family_id, True
            )
            add_workflows(
                family.get("plannedWorkflows", []),
                identifier,
                family_id,
                "planned_workflow",
            )
            add_workflows(
                family.get("contextualWorkflows", []),
                identifier,
                family_id,
                "contextual_information",
            )
    if placements.keys() != methods.keys():
        raise ValueError(
            "capability_missing_placement:"
            + ",".join(sorted(methods.keys() - placements.keys()))
        )
    guidance = frontend["guidance_method_ids"]
    if len(guidance) != len(set(guidance)):
        raise ValueError("capability_duplicate_guidance")
    known_guidance = methods.keys() | {
        item["method_id"] for item in facts["subworkflows"]
    }
    if set(guidance) - known_guidance:
        raise ValueError(
            "capability_unknown_guidance:"
            + ",".join(sorted(set(guidance) - known_guidance))
        )
    if methods.keys() - set(guidance):
        raise ValueError(
            "capability_missing_guidance:"
            + ",".join(sorted(methods.keys() - set(guidance)))
        )
    return {
        **facts,
        "methods": [
            {**methods[key], "placement": placement}
            for key, placement in placements.items()
        ],
        "domains": domains,
        "informational_workflows": workflows,
        "guidance_method_ids": sorted(guidance),
        "evidence": "source_declarations_not_runtime_test_results",
    }


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# Analysis Capability Matrix (Generated)",
        "",
        "Generated offline by `scripts/generate_capability_matrix.py`. Do not edit this file.",
        "",
        f"API contract **{matrix['api_contract_version']}**; metadata schema **{matrix['metadata_schema_version']}**.",
        "",
        "This is a source-declaration inventory, not a claim that every option, historical artifact,",
        "browser journey, or platform has been executed. Live catalog availability, preflight and",
        "source prerequisites remain authoritative. Report level is assessed from the exact stored",
        "payload: `full`, `summary`, or `unsupported`; declared schemas alone do not guarantee full output.",
        "Historical readable and stale are independent: no result or model is rewritten by this inventory.",
        "",
        "## Canonical Menu Placement",
        "",
        f"{len(matrix['methods'])} catalog methods; {len(matrix['domains'])} user-facing domains.",
        "Contextual menu entries still require their source and are not independent generic runners.",
        "",
    ]
    for domain in matrix["domains"]:
        lines.extend(
            [
                f"### {domain['id']}",
                "",
                "| Method / Version | Label | Family / Entry | Availability / Prerequisite | Execution / Cancellation / Progress |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in matrix["methods"]:
            place = item["placement"]
            if place["domain_id"] != domain["id"]:
                continue
            prerequisite = (
                "dataset"
                if item["requires_dataset"]
                else (item["source_prerequisite"] or "workflow inputs")
            )
            execution = item["execution_capability"]
            values = [
                f"`{item['method_id']}` / {item['method_version']}",
                item["label_en"],
                f"{place['family_id'] or 'direct'} / {'contextual' if place['contextual'] else 'direct'}",
                f"{item['availability']} / {prerequisite}",
                f"{execution['lifecycle']} / {execution['cancellation_support']} / {execution['progress_support']}",
            ]
            lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
        lines.append("")
    lines.extend(
        [
            "## Actual Execution Entry Points",
            "",
            "| Method | Route | Handler | Source |",
            "| --- | --- | --- | --- |",
        ]
    )
    entries = matrix["methods"] + matrix["subworkflows"]
    for item in entries:
        entry = item["entry_point"]
        lines.append(
            f"| `{item['method_id']}` | `{entry['route']}` | `{entry['handler']}` | `{entry['source']}` |"
        )
    lines.extend(
        [
            "",
            "## Declared Execution Limits",
            "",
            "These are the live catalog's declared caps, not an exhaustive memory/time guarantee.",
            "An omitted cap does not mean unlimited execution. Variant caps apply only to that option.",
            "",
            "| Method | Limit | Value / Unit | Variant |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in matrix["methods"]:
        for limit in item["resource_limits"] or []:
            values = [
                f"`{item['method_id']}`",
                limit["name"],
                f"{limit['value']} {limit['unit']}",
                limit["variant"] or "all",
            ]
            lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    lines.extend(
        [
            "",
            "## Stored Report Contracts",
            "",
            "Each row reuses an actual renderer declaration. Core sections are prefixed with `*`.",
            "Missing optional sections yield summary output; missing core/invalid payload yields unsupported.",
            "Not-applicable intervals or diagnostics are not fabricated. Source staleness does not erase historical output.",
            "",
            "| Owner Method | Source Kind / Summary | Reader Schemas | Renderer / Version | Variant: Sections |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in entries:
        for report in item["reports"]:
            variants = "; ".join(
                variant["variant_id"]
                + ": "
                + ", ".join(
                    ("*" if section["core"] else "") + section["section_id"]
                    for section in variant["sections"]
                )
                for variant in report["variants"]
            )
            values = [
                f"`{item['method_id']}`",
                f"{report['source_kind']} / {report['summary_type']}",
                ", ".join(str(schema) for schema in report["accepted_schemas"]),
                f"{report['renderer_id']} / {report['renderer_version']}",
                variants,
            ]
            lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    lines.extend(
        [
            "",
            "## Non-Menu Entries",
            "",
            "| ID | Kind | Meaning |",
            "| --- | --- | --- |",
        ]
    )
    for item in matrix["subworkflows"]:
        lines.append(
            f"| `{item['method_id']}` | current subworkflow | version {item['method_version']}; {item['source_prerequisite']} required |"
        )
    for alias, target in matrix["legacy_aliases"].items():
        lines.append(
            f"| `{alias}` | legacy alias | resolves to `{target}`; not another menu method |"
        )
    for item in matrix["informational_workflows"]:
        lines.append(
            f"| `{item['id']}` | {item['entry_kind']} | {item['visibility']}; {item['domain_id']}; not an executable catalog entry |"
        )
    lines.extend(
        [
            "",
            "## Bounded Policies",
            "",
            "These are explicit product limits and conditional support, not dynamic eligibility or performance guarantees.",
            "",
            "| Declaration | Value |",
            "| --- | --- |",
        ]
    )
    for key, value in {**matrix["limits"], **matrix["option_policies"]}.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Sources and Verification",
            "",
            "- Registry/version/source requirements: `backend/app/analyses/registry.py`.",
            "- Generic specs and actual runners: `analysis_method_handlers.py`, `analysis_runs.py`.",
            "- Dedicated endpoints: actual route decorators named above, not copied route strings.",
            "- Report schemas/variants: `report_coverage.py`, `dedicated_report_renderers.py`,",
            "  `stored_prediction_report.py`, `completed_prediction_report.py`.",
            "- Ordered menu placement/roadmap: `frontend/src/analysisDomains.ts`; guidance keys:",
            "  `frontend/src/analysisMethodGuidance.ts` (parsed, not executed).",
            "- Limits: `backend/app/core/doe_capabilities.py`; ANOVA policy: typed request default.",
            "- Conditional-policy evidence and generator checks: [capability contract](../analysis_capability_contract.md).",
            "- Executed journey evidence is separate: [remediation journey matrix](../remediation_journey_matrix.md).",
            "- Exact saved-result support: [report coverage](../html_report_coverage_matrix.md).",
            "",
        ]
    )
    return "\n".join(lines)


def generated_outputs(matrix: dict[str, Any]) -> dict[Path, bytes]:
    return {
        OUTPUT_JSON: (
            json.dumps(matrix, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        ).encode("utf-8"),
        OUTPUT_MARKDOWN: render_markdown(matrix).encode("utf-8"),
    }


def check_or_write(
    root: Path, outputs: dict[Path, bytes], *, write: bool
) -> list[Path]:
    changed = [
        path
        for path, content in outputs.items()
        if not (root / path).is_file() or (root / path).read_bytes() != content
    ]
    if write:
        for path in changed:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(
                prefix=".capability-", dir=target.parent
            )
            try:
                with os.fdopen(descriptor, "wb") as output:
                    output.write(outputs[path])
                os.replace(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = subprocess.run(
            [
                "node",
                str(ROOT / "scripts/read_frontend_capability_metadata.mjs"),
                str(ROOT),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        matrix = assemble_matrix(
            backend_capability_facts(ROOT), json.loads(result.stdout)
        )
        changed = check_or_write(ROOT, generated_outputs(matrix), write=args.write)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(
            f"Capability generation failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    for path in changed:
        print(f"{'Updated' if args.write else 'Out of date'}: {path.as_posix()}")
    if not changed:
        print("Capability matrix is current.")
    return 0 if args.write or not changed else 1


if __name__ == "__main__":
    raise SystemExit(main())
