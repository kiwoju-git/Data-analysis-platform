"""Stored Gage plot/report parity; no fitting or source-row reads during export."""

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from app.services.analysis_run_exports import prepare_analysis_report
from app.services.quality_report import quality_report_body
from app.statistics.gage_rr import calculate_gage_rr_anova
from app.statistics.gage_rr_preflight import GageRrColumn

PLOT_IDS = (
    "gage_components_plot",
    "gage_response_by_part",
    "gage_dispersion",
    "gage_response_by_operator",
    "gage_xbar",
    "gage_interaction",
)


def result_fixture(parts=10, operators=3, repeats=2, part_ids=None):
    rows = [
        [
            str(20 + part * 2 + operator * 0.3 + (repeat - (repeats - 1) / 2) * 0.4),
            part_ids[part] if part_ids else f"PRIVATE-PART-{part}",
            f"PRIVATE-OPERATOR-{operator}",
        ]
        for part in range(parts)
        for operator in range(operators)
        for repeat in range(repeats)
    ]
    columns = [
        GageRrColumn("y", 0, "Response <&> 한국어", "numeric", "continuous", "response", "mg"),
        GageRrColumn("p", 1, "Part", "text", "nominal", "part_id", None),
        GageRrColumn("o", 2, "Operator", "text", "nominal", "operator_id", None),
    ]
    return calculate_gage_rr_anova(
        rows,
        measurement_column=columns[0],
        part_column=columns[1],
        operator_column=columns[2],
        replicate_column=None,
        replicate_mode="infer_from_rows",
        interaction_policy="auto_pool",
    )


def checksum(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def prepared(payload, locale="en"):
    return prepare_analysis_report(
        SimpleNamespace(method_id="quality.gage_rr", result=payload), locale
    )


def markup_tree(markup):
    return ET.fromstring(f"<main>{markup}</main>")


@pytest.mark.parametrize("locale", ["en", "ko"])
def test_six_stored_charts_are_full_escaped_and_do_not_recalculate(locale, monkeypatch):
    result = result_fixture()
    assert result["schema_version"] == 4
    before = checksum(result)

    def forbidden(*args, **kwargs):
        pytest.fail("Gage export must not calculate, pool, or read source rows")

    monkeypatch.setattr("app.statistics.gage_rr.calculate_gage_rr_anova", forbidden)
    monkeypatch.setattr("app.statistics.gage_rr._anova", forbidden)
    monkeypatch.setattr("app.statistics.gage_rr._variance_components", forbidden)
    monkeypatch.setattr("app.services.dataset_rows.get_dataset_rows_context", forbidden)
    report = prepared(result, locale)
    assert report.level == "full"
    root = markup_tree(report.render())
    plots = [node for node in root.iter("div") if node.get("data-report-section") in PLOT_IDS]
    assert [node.get("data-report-section") for node in plots] == list(PLOT_IDS)
    assert all(node.find(".//svg") is not None for node in plots)
    assert root.find('.//div[@class="report-grid"]') is not None
    text = "".join(root.itertext())
    assert "Response <&> 한국어" in text and "mg" in text
    assert "PRIVATE-PART-0" in text and "PRIVATE-OPERATOR" not in text
    assert ("Xbar" in text and "R Chart" in text) if locale == "en" else "R 관리도" in text
    assert "<script" not in report.render() and "https://" not in report.render()
    assert checksum(result) == before


@pytest.mark.parametrize("schema", [1, 2])
def test_legacy_only_uses_stored_components_and_marks_five_missing(schema):
    result = result_fixture()
    result["schema_version"] = schema
    result.pop("plot_bundle", None)
    before = checksum(result)
    report = prepared(result)
    assert report.level == "summary"
    plots = {
        section.section_id: section
        for section in report.body.sections
        if section.section_id in PLOT_IDS
    }
    assert plots["gage_components_plot"].status == "rendered"
    assert "Reanalysis" in plots["gage_components_plot"].markup
    for key in PLOT_IDS[1:]:
        assert plots[key].status == "missing"
        assert plots[key].reason == "gage_plot_bundle_not_stored_reanalysis_required"
    assert checksum(result) == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.pop("plot_bundle"),
        lambda r: r["plot_bundle"].update(schema_version=99),
        lambda r: r["plot_bundle"]["dispersion"].update(points=[]),
        lambda r: r["plot_bundle"]["xbar"].update(lower_limit=float("nan")),
        lambda r: r["plot_bundle"]["response_by_operator"]["boxes"][0].update(q1=None),
        lambda r: r["plot_bundle"]["components"]["items"][0].update(percent_contribution=None),
        lambda r: r["plot_bundle"]["parts"][0].pop("part_id"),
        lambda r: r["plot_bundle"]["parts"][0].update(
            part_id=r["plot_bundle"]["parts"][1]["part_id"]
        ),
    ],
)
def test_malformed_current_bundle_cannot_be_full_or_a_blank_plot(mutation):
    result = copy.deepcopy(result_fixture())
    mutation(result)
    assert prepared(result).level == "unsupported"


def test_actual_cell_means_and_selected_anova_zero_limits_are_preserved():
    result = result_fixture()
    bundle = result["plot_bundle"]
    assert bundle["interaction"]["interaction_pooled"] is True
    root = markup_tree(quality_report_body(result).render())
    interaction = root.find('.//div[@data-report-section="gage_interaction"]')
    actual = {
        (int(node.get("data-part-index")), int(node.get("data-operator-index"))): float(
            node.get("data-y")
        )
        for node in interaction.iter("circle")
        if node.get("data-role") == "cell_mean"
    }
    assert actual == {
        (p["part_index"], p["operator_index"]): p["mean"] for p in bundle["interaction"]["points"]
    }
    dispersion = root.find('.//div[@data-report-section="gage_dispersion"]')
    assert any(
        float(line.get("data-value")) == 0
        for line in dispersion.iter("line")
        if line.get("data-reference") == "lower_limit"
    )
    xbar = root.find('.//div[@data-report-section="gage_xbar"]')
    for key in ("center", "lower_limit", "upper_limit"):
        assert any(
            float(line.get("data-value")) == bundle["xbar"][key]
            for line in xbar.iter("line")
            if line.get("data-reference") == key
        )


def test_r_s_titles_and_stored_type7_box_geometry():
    for repeats, expected in ((2, "R Chart"), (9, "S Chart")):
        result = result_fixture(repeats=repeats)
        root = markup_tree(prepared(result).render())
        assert expected in "".join(root.itertext())
        boxes = root.findall(".//rect[@data-box-operator]")
        assert len(boxes) == 3
        for box in boxes:
            stored = result["plot_bundle"]["response_by_operator"]["boxes"][
                int(box.get("data-box-operator"))
            ]
            assert float(box.get("data-q1")) == stored["q1"]
            assert float(box.get("data-q3")) == stored["q3"]
            assert float(box.get("height")) >= 0


def test_all_summary_cells_survive_raw_display_cap_and_pagination():
    result = result_fixture(parts=31, operators=9, repeats=20)
    bundle = result["plot_bundle"]
    assert bundle["counts"]["n_used"] == 5580
    assert bundle["counts"]["truncated"] is True
    report = prepared(result)
    assert report.level == "full"
    root = markup_tree(report.render())
    interaction = root.find('.//div[@data-report-section="gage_interaction"]')
    points = [node for node in interaction.iter("circle") if node.get("data-role") == "cell_mean"]
    assert len(points) == 31 * 9
    assert "5580" in "".join(root.itertext()) and "5000" in "".join(root.itertext())
    assert len(interaction.findall(".//svg")) > 1


def test_svg_geometry_uses_saved_coordinates_and_shared_global_bounds():
    result = result_fixture(parts=11, operators=4)
    root = markup_tree(prepared(result).render())
    for section_id in ("gage_response_by_part", "gage_xbar", "gage_dispersion", "gage_interaction"):
        section = root.find(f'.//div[@data-report-section="{section_id}"]')
        ranges = set()
        for svg in section.iter("svg"):
            xmin, xmax = float(svg.get("data-x-min")), float(svg.get("data-x-max"))
            ymin, ymax = float(svg.get("data-y-min")), float(svg.get("data-y-max"))
            ranges.add((ymin, ymax))
            for point in svg.iter("circle"):
                x, y = float(point.get("data-x")), float(point.get("data-y"))
                assert float(point.get("cx")) == pytest.approx(
                    80 + (x - xmin) / (xmax - xmin) * 455, abs=5e-7
                )
                assert float(point.get("cy")) == pytest.approx(
                    240 - (y - ymin) / (ymax - ymin) * 208, abs=5e-7
                )
                assert 32 <= float(point.get("cy")) <= 240
            for line in svg.iter("line"):
                if line.get("data-reference") is not None:
                    y = float(line.get("data-value"))
                    assert float(line.get("y1")) == pytest.approx(
                        240 - (y - ymin) / (ymax - ymin) * 208, abs=5e-7
                    )
        assert len(ranges) == 1
    clips = [node.get("id") for node in root.iter("clipPath")]
    assert len(clips) == len(set(clips))


def test_component_bars_and_box_whiskers_are_actual_svg_geometry():
    result = result_fixture()
    root = markup_tree(prepared(result).render())
    component = root.find('.//div[@data-report-section="gage_components_plot"]//svg')
    low, high = float(component.get("data-y-min")), float(component.get("data-y-max"))
    for bar in component.iter("rect"):
        if bar.get("data-component") is None:
            continue
        saved = result["variance_components"][bar.get("data-component")][bar.get("data-metric")]
        assert float(bar.get("data-value")) == saved
        assert float(bar.get("height")) == pytest.approx(saved / (high - low) * 208, abs=5e-7)
    box_svg = root.find('.//div[@data-report-section="gage_response_by_operator"]//svg')
    low, high = float(box_svg.get("data-y-min")), float(box_svg.get("data-y-max"))
    for box in box_svg.findall(".//rect[@data-box-operator]"):
        saved = result["plot_bundle"]["response_by_operator"]["boxes"][
            int(box.get("data-box-operator"))
        ]
        assert float(box.get("height")) == pytest.approx(
            (saved["q3"] - saved["q1"]) / (high - low) * 208, abs=5e-7
        )
    for line in box_svg.findall(".//line[@data-box-whisker]"):
        saved = result["plot_bundle"]["response_by_operator"]["boxes"][
            int(line.get("data-box-whisker"))
        ]
        assert float(line.get("y1")) == pytest.approx(
            240 - (saved["lower_whisker"] - low) / (high - low) * 208, abs=5e-7
        )
        assert float(line.get("y2")) == pytest.approx(
            240 - (saved["upper_whisker"] - low) / (high - low) * 208, abs=5e-7
        )


def test_current_unavailable_stored_plot_is_honest_summary_not_blank_full():
    result = result_fixture()
    result["plot_bundle"]["dispersion"].update(
        status="unavailable",
        unavailable_reason="non_finite_plot_summary",
        center=None,
        lower_limit=None,
        upper_limit=None,
    )
    for point in result["plot_bundle"]["dispersion"]["points"]:
        point["outside_limits"] = None
    report = prepared(result)
    assert report.level == "summary"
    section = next(s for s in report.body.sections if s.section_id == "gage_dispersion")
    assert section.status == "missing" and section.markup is None


def test_hostile_measurement_name_and_unit_remain_text_not_markup():
    result = result_fixture()
    for target in (result["columns"]["measurement"], result["plot_bundle"]["measurement"]):
        target["display_name"] = '<script>alert("private")</script>'
        target["unit"] = '<img src=x onerror="private">'
    rendered = prepared(result).render()
    root = markup_tree(rendered)
    assert not root.findall(".//script") and not root.findall(".//img")
    assert '<script>alert("private")</script>' in "".join(root.itertext())
    assert "&lt;script&gt;" in rendered


def test_consistently_linked_negative_component_is_not_a_valid_chart():
    result = result_fixture()
    result["variance_components"]["total_gage_rr"]["percent_contribution"] = -1.0
    result["plot_bundle"]["components"]["items"][0]["percent_contribution"] = -1.0
    assert prepared(result).level == "unsupported"


@pytest.mark.parametrize("locale", ["en", "ko"])
def test_actual_numeric_part_ids_match_saved_values_and_natural_display_order(locale):
    result = result_fixture(part_ids=[str(i) for i in range(1, 11)])
    before = checksum(result)
    report = prepared(result, locale)
    assert report.level == "full"
    assert report.definition.renderer_version == "2.3.1"
    root = markup_tree(report.render())
    for section_id in ("gage_response_by_part", "gage_interaction"):
        section = root.find(f'.//div[@data-report-section="{section_id}"]')
        svg = section.find(".//svg")
        assert [
            node.get("data-gage-part-id") for node in svg.findall("text[@data-gage-part-id]")
        ] == [str(i) for i in range(1, 11)]
        for point in svg.findall(".//*[@data-part-index]"):
            index = int(point.get("data-part-index"))
            assert point.get("data-gage-part-id") == str(index + 1)
            assert str(index + 1) in point.find("title").text
    table = root.find('.//div[@data-gage-part-summary="true"]//table')
    assert [row.find("td").text for row in table.findall(".//tbody/tr")] == [
        str(i) for i in range(1, 11)
    ]
    tenth = root.find(
        './/div[@data-report-section="gage_interaction"]//circle[@data-gage-part-id="10"]'
    )
    assert float(tenth.get("data-y")) == pytest.approx(38.0)
    assert checksum(result) == before


def test_distinct_leading_zero_and_hostile_long_ids_have_full_escaped_detail_paths():
    part_ids = ["1", "01", "부품" * 80, '<script>alert("part")</script>', "a&b<>/'\\"]
    result = result_fixture(parts=len(part_ids), part_ids=part_ids)
    before = checksum(result)
    root = markup_tree(prepared(result).render())
    section = root.find('.//div[@data-report-section="gage_response_by_part"]')
    labels = section.findall(".//svg/text[@data-gage-part-id]")
    assert {label.get("data-gage-part-id") for label in labels} == set(part_ids)
    assert all(len("".join(label.findall("tspan")[0].itertext())) <= 6 for label in labels)
    rows = section.findall(".//table/tbody/tr")
    assert {row.find("td").text for row in rows} == set(part_ids)
    assert {
        row.findall("td")[0].text: float("".join(row.findall("td")[2].itertext())) for row in rows
    } == {part_id: pytest.approx(20 + index * 2 + 0.3) for index, part_id in enumerate(part_ids)}
    assert not root.findall(".//script") and not root.findall(".//img")
    for point in section.findall(".//svg//*[@data-gage-part-id]"):
        assert point.get("data-gage-part-id") in "".join(point.find("title").itertext())
    assert "PRIVATE-OPERATOR" not in "".join(root.itertext())
    assert checksum(result) == before


@pytest.mark.parametrize("locale", ["en", "ko"])
def test_legacy_schema3_preserves_indices_and_labels_original_id_unavailable(locale):
    path = Path(__file__).parents[3] / "tests/fixtures/gage_rr_six_panel.json"
    result = json.loads(path.read_text(encoding="utf-8"))["auto_pool"]
    assert result["schema_version"] == 3
    before = checksum(result)
    report = prepared(result, locale)
    assert report.level == "full"
    root = markup_tree(report.render())
    text = "".join(root.itertext())
    assert ("Part display number" if locale == "en" else "부품 표시 번호") in text
    assert (
        "Original part IDs were not stored" if locale == "en" else "원래 부품 ID가 저장되지"
    ) in text
    assert ("Reanalysis" if locale == "en" else "재분석") in text
    assert ("Display 1" if locale == "en" else "표시 번호 1") in text
    assert "P1" not in text
    section = root.find('.//div[@data-report-section="gage_interaction"]')
    point = section.find('.//circle[@data-part-index="1"]')
    stored = next(p for p in result["plot_bundle"]["interaction"]["points"] if p["part_index"] == 1)
    assert float(point.get("data-y")) == stored["mean"]
    assert point.get("data-gage-part-id") is None
    assert checksum(result) == before
