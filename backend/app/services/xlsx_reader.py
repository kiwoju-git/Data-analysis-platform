import posixpath
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from app.core.errors import ApiError

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


@dataclass(frozen=True)
class XlsxSheetRow:
    row_number: int
    cells: list[str]


@dataclass(frozen=True)
class _XlsxSheet:
    name: str
    path: str


def iter_xlsx_sheet_rows(path: Path, sheet_name: str | None) -> Iterator[XlsxSheetRow]:
    try:
        with zipfile.ZipFile(path) as archive:
            sheet = _selected_sheet(archive, sheet_name)
            shared_strings = _read_shared_strings(archive)
            yield from _iter_sheet_rows(archive, sheet.path, shared_strings)
    except zipfile.BadZipFile as exc:
        raise ApiError(
            code="invalid_xlsx_container",
            message="XLSX 컨테이너를 읽을 수 없습니다.",
        ) from exc
    except ElementTree.ParseError as exc:
        raise ApiError(
            code="xlsx_xml_parse_failed",
            message="XLSX XML을 읽을 수 없습니다.",
        ) from exc


def _selected_sheet(archive: zipfile.ZipFile, sheet_name: str | None) -> _XlsxSheet:
    sheets = _workbook_sheets(archive)
    if not sheets:
        raise ApiError(
            code="xlsx_sheet_not_found",
            message="XLSX 워크북에서 시트를 찾을 수 없습니다.",
        )

    requested_name = sheet_name.strip() if sheet_name is not None else ""
    if requested_name == "":
        return sheets[0]

    for sheet in sheets:
        if sheet.name == requested_name:
            return sheet

    raise ApiError(
        code="xlsx_sheet_not_found",
        message="요청한 XLSX 시트를 찾을 수 없습니다.",
    )


def _workbook_sheets(archive: zipfile.ZipFile) -> list[_XlsxSheet]:
    try:
        workbook_root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        rels_root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    except KeyError as exc:
        raise ApiError(
            code="invalid_xlsx_container",
            message="XLSX workbook 관계 정보를 찾을 수 없습니다.",
        ) from exc

    targets_by_id: dict[str, str] = {}
    for relationship in rels_root:
        if _local_name(relationship.tag) != "Relationship":
            continue
        relationship_id = relationship.attrib.get("Id")
        target = relationship.attrib.get("Target")
        if relationship_id is None or target is None:
            continue
        targets_by_id[relationship_id] = _relationship_target_path(target)

    sheets: list[_XlsxSheet] = []
    for sheet_element in workbook_root.iter(f"{{{MAIN_NS}}}sheet"):
        name = sheet_element.attrib.get("name")
        relationship_id = sheet_element.attrib.get(f"{{{REL_NS}}}id")
        if name is None or relationship_id is None:
            continue
        path = targets_by_id.get(relationship_id)
        if path is None or path not in archive.namelist():
            continue
        sheets.append(_XlsxSheet(name=name, path=path))
    return sheets


def _relationship_target_path(target: str) -> str:
    if target.startswith("/"):
        normalized = posixpath.normpath(target.lstrip("/"))
    else:
        normalized = posixpath.normpath(posixpath.join("xl", target))
    if normalized.startswith("../") or normalized == "..":
        raise ApiError(
            code="invalid_xlsx_container",
            message="XLSX workbook 관계 경로가 올바르지 않습니다.",
        )
    return normalized


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root:
        if _local_name(item.tag) != "si":
            continue
        strings.append(
            "".join(text.text or "" for text in item.iter() if _local_name(text.tag) == "t"),
        )
    return strings


def _iter_sheet_rows(
    archive: zipfile.ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> Iterator[XlsxSheetRow]:
    fallback_row_number = 0
    with archive.open(sheet_path) as sheet_handle:
        for _, element in ElementTree.iterparse(sheet_handle, events=("end",)):
            if _local_name(element.tag) != "row":
                continue

            fallback_row_number += 1
            row_number = _row_number(element.attrib.get("r"), fallback_row_number)
            cells = _row_cells(element, shared_strings)
            yield XlsxSheetRow(row_number=row_number, cells=cells)
            element.clear()


def _row_cells(row_element: ElementTree.Element, shared_strings: list[str]) -> list[str]:
    values_by_index: dict[int, str] = {}
    next_index = 0
    for cell in row_element:
        if _local_name(cell.tag) != "c":
            continue
        cell_ref = cell.attrib.get("r")
        column_index = _column_index(cell_ref) if cell_ref is not None else next_index
        values_by_index[column_index] = _cell_value(cell, shared_strings)
        next_index = column_index + 1

    if not values_by_index:
        return []
    max_index = max(values_by_index)
    return [values_by_index.get(index, "") for index in range(max_index + 1)]


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find(f"{{{MAIN_NS}}}is")
        if inline is None:
            return ""
        return "".join(text.text or "" for text in inline.iter() if _local_name(text.tag) == "t")

    value_element = cell.find(f"{{{MAIN_NS}}}v")
    raw_value = "" if value_element is None or value_element.text is None else value_element.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (ValueError, IndexError) as exc:
            raise ApiError(
                code="xlsx_shared_string_invalid",
                message="XLSX 공유 문자열 참조가 올바르지 않습니다.",
            ) from exc
    if cell_type == "b":
        return "TRUE" if raw_value == "1" else "FALSE"
    return raw_value


def _row_number(raw_value: str | None, fallback: int) -> int:
    if raw_value is None:
        return fallback
    try:
        return int(raw_value)
    except ValueError:
        return fallback


def _column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Za-z]+)", cell_ref)
    if match is None:
        return 0
    index = 0
    for character in match.group(1).upper():
        index = index * 26 + (ord(character) - ord("A") + 1)
    return index - 1


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag
