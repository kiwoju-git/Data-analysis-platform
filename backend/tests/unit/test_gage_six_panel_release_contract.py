"""Synthetic receipt rejection tests, not archive installation/browser evidence."""

import importlib.util
import math
from copy import deepcopy
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "gage_release_receipt_tests", ROOT / "scripts/verify_linux_release.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
with pytest.MonkeyPatch.context() as imports:
    imports.syspath_prepend(str(ROOT / "scripts"))
    SPEC.loader.exec_module(VERIFY)

SECTIONS = (
    "gage_components_plot",
    "gage_response_by_part",
    "gage_dispersion",
    "gage_response_by_operator",
    "gage_xbar",
    "gage_interaction",
)


def receipts():
    analyses = [
        {
            "analysis_id": str(UUID(int=index + 1)),
            "policy": policy,
            "envelope_sha256": str(index + 1) * 64,
            "source_result_sha256": str(index + 3) * 64,
            "raw_points": 70,
            "raw_measurement_points": 60,
            "box_n": 20,
            "component_bars": 8,
            "operator_paths_per_chart": 3,
            "numeric_svg_checked": True,
            "part_axis_labels_checked": True,
            "part_ids": [str(index) for index in range(1, 11)],
            "part_means": [50 + 2 * index for index in range(10)],
            "dispersion_center": 0.2,
            "dispersion_ucl": 0.6534,
            "xbar_center": 59,
            "xbar_half_width": 0.3 if policy == "retain" else 3 * math.sqrt(0.0125 / 2),
        }
        for index, policy in enumerate(("retain", "auto_pool"))
    ]
    reports = [
        {
            "locale": locale,
            "path": "synthetic-only-not-an-archive.html",
            "descriptor": {
                "export_id": str(UUID(int=index + 3)),
                "analysis_id": analyses[index]["analysis_id"],
                "source_result_sha256": analyses[index]["source_result_sha256"],
                "sha256": str(index + 5) * 64,
            },
        }
        for index, locale in enumerate(("en", "ko"))
    ]
    initial = {
        "schema_version": 1,
        "status": "succeeded",
        "analyses": analyses,
        "reports": reports,
        "zoom_analysis_id": analyses[1]["analysis_id"],
        "view_only_analysis_post_count": 0,
        "legacy_ui": "synthetic_read_only_schema2_transport_projection",
        "interaction_checks": [
            "hover",
            "pin_preserved_while_hovering",
            "escape_keeps_focus",
            "single_roving_item",
            "tab_exit",
            "locale_preserves_pin",
        ],
        "layout": [
            {"locale": locale, "columns": columns, "scrollWidth": 900, "viewport": 900}
            for locale, columns in (("ko", 1), ("en", 2))
        ],
        "filter": {"n_used": 54, "cells": 27, "source_digest": "a" * 64},
        "pagination": {"parts": 11, "operators": 4, "selected_cells": 1, "source_digest": "b" * 64},
    }
    zoom = {
        "schema_version": 1,
        "status": "succeeded",
        "mechanism": "chrome.tabs.setZoom/getZoom",
        "deviceScaleFactor_override": False,
        "source_digest": analyses[1]["envelope_sha256"],
        "steps": [
            {"locale": locale, "browser_zoom": factor, "viewport": 960, "scrollWidth": 960}
            for locale in ("ko", "en")
            for factor in (1.25, 1.5)
        ],
    }
    resumed = {
        "phase": "resume",
        "status": "succeeded",
        "analyses": deepcopy(analyses),
        "analysis_post_count": 0,
        "report_creation_post_count": 0,
        "reports": [
            {
                "export_id": item["descriptor"]["export_id"],
                "sha256": item["descriptor"]["sha256"],
                "bytes_identical": True,
            }
            for item in reports
        ],
    }
    offline = {
        "original_server_unreachable": True,
        "browser_network_offline": True,
        "http_request_count": 0,
        "gage_six_panel_receipt": {
            "phase": "offline",
            "status": "succeeded",
            "server_stopped_by_release_verifier": True,
            "reports": [
                {
                    "export_id": item["descriptor"]["export_id"],
                    "sha256": item["descriptor"]["sha256"],
                    "locale": item["locale"],
                    "raw_point_count": 60,
                    "part_axis_labels_checked": True,
                    "part_ids": [str(index) for index in range(1, 11)],
                    "dispersion_ucl": 0.6534,
                    "sections": [{"section": section, "svg_count": 1} for section in SECTIONS],
                }
                for item in reports
            ],
        },
    }
    return (
        {"gage_six_panel_receipt": initial, "gage_six_panel_zoom_receipt": zoom},
        [{"gage_six_panel_receipt": deepcopy(resumed)} for _ in range(2)],
        offline,
    )


def test_complete_cross_linked_synthetic_receipt_is_accepted_without_processes(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Receipt checks must not launch a process")

    monkeypatch.setattr(VERIFY.subprocess, "Popen", forbidden)
    result = VERIFY.require_gage_six_panel_receipts(*receipts())
    assert result["analysis_count"] == 2
    assert result["restart_count"] == 2
    assert result["server_stopped_six_sections_visible"] is True


@pytest.mark.parametrize(
    "change",
    [
        lambda i, r, o: i["gage_six_panel_receipt"]["analyses"][0].update(part_ids=["1", "10"]),
        lambda i, r, o: i["gage_six_panel_receipt"]["analyses"][0].update(
            part_axis_labels_checked=False
        ),
        lambda i, r, o: r[0]["gage_six_panel_receipt"]["analyses"][0].update(part_means=[50, 68]),
        lambda i, r, o: o["gage_six_panel_receipt"]["reports"][0].pop("part_ids"),
        lambda i, r, o: i.pop("gage_six_panel_receipt"),
        lambda i, r, o: i["gage_six_panel_receipt"].update(status="running"),
        lambda i, r, o: i["gage_six_panel_receipt"].update(view_only_analysis_post_count=1),
        lambda i, r, o: i["gage_six_panel_receipt"].update(view_only_analysis_post_count=False),
        lambda i, r, o: i["gage_six_panel_receipt"]["interaction_checks"].remove("tab_exit"),
        lambda i, r, o: i["gage_six_panel_receipt"]["analyses"][0].update(dispersion_ucl=0.6),
        lambda i, r, o: i["gage_six_panel_receipt"]["analyses"][1].update(xbar_half_width=0.3),
        lambda i, r, o: i["gage_six_panel_receipt"]["analyses"][0].update(
            numeric_svg_checked=False
        ),
        lambda i, r, o: i["gage_six_panel_receipt"]["analyses"][0].update(raw_points=60),
        lambda i, r, o: i["gage_six_panel_receipt"]["reports"][0]["descriptor"].update(
            source_result_sha256="f" * 64
        ),
        lambda i, r, o: i["gage_six_panel_receipt"]["layout"][0].update(scrollWidth=901.1),
        lambda i, r, o: i["gage_six_panel_receipt"]["filter"].update(n_used=60),
        lambda i, r, o: i["gage_six_panel_receipt"]["pagination"].update(selected_cells=30),
        lambda i, r, o: i["gage_six_panel_zoom_receipt"].update(deviceScaleFactor_override=True),
        lambda i, r, o: i["gage_six_panel_zoom_receipt"].update(mechanism="CSS zoom"),
        lambda i, r, o: i["gage_six_panel_zoom_receipt"]["steps"].pop(),
        lambda i, r, o: i["gage_six_panel_zoom_receipt"].update(source_digest="f" * 64),
        lambda i, r, o: r.pop(),
        lambda i, r, o: r[1]["gage_six_panel_receipt"].update(report_creation_post_count=1),
        lambda i, r, o: r[1]["gage_six_panel_receipt"]["analyses"][0].update(
            envelope_sha256="f" * 64
        ),
        lambda i, r, o: r[1]["gage_six_panel_receipt"]["reports"][0].update(sha256="f" * 64),
        lambda i, r, o: r[1]["gage_six_panel_receipt"]["reports"][0].update(bytes_identical=False),
        lambda i, r, o: o.update(original_server_unreachable=False),
        lambda i, r, o: o.update(http_request_count=1),
        lambda i, r, o: o["gage_six_panel_receipt"]["reports"][0]["sections"].pop(),
        lambda i, r, o: o["gage_six_panel_receipt"]["reports"][0]["sections"][0].update(
            svg_count=0
        ),
        lambda i, r, o: o["gage_six_panel_receipt"]["reports"][0].update(sha256="f" * 64),
    ],
)
def test_incomplete_or_changed_gage_receipt_blocks_release(change):
    initial, restarts, offline = receipts()
    change(initial, restarts, offline)
    with pytest.raises(ValueError, match="Gage"):
        VERIFY.require_gage_six_panel_receipts(initial, restarts, offline)
