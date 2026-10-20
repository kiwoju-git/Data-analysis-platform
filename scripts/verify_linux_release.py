"""Verify the completed archive bytes via offline install and black-box application tests."""

from __future__ import annotations

import argparse
import errno
import hashlib
import ipaddress
import json
import math
import os
import platform
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from uuid import UUID

from network_isolated_install import run_network_blocked_install
from validate_python_lock import validate_lock_text

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MAX_ARCHIVE_FILES = 100_000
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
CONTOUR_WHEEL_NAME = (
    "contourpy-1.3.2-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_contour_dependency(root: Path) -> dict:
    """Cross-check packaged dependency bytes without importing its native extension."""
    wheels = list((root / "wheels").glob("contourpy-*.whl"))
    if len(wheels) != 1 or wheels[0].name != CONTOUR_WHEEL_NAME:
        raise ValueError(
            "Release must contain the locked Linux CPython 3.12 ContourPy wheel"
        )
    wheel = wheels[0]
    if wheel.is_symlink() or not 0 < wheel.stat().st_size <= 16 * 1024 * 1024:
        raise ValueError("Invalid ContourPy wheel file")
    lock_path = root / "requirements-release.lock"
    manifest_path = root / "FILES.sha256"
    if (
        lock_path.stat().st_size > 1024 * 1024
        or manifest_path.stat().st_size > 16 * 1024 * 1024
    ):
        raise ValueError("Release dependency records exceed validation limits")
    lock = validate_lock_text(
        lock_path.read_text(encoding="ascii"),
        {"contourpy": "1.3.2"},
        target="py312-linux",
        profile="runtime",
    )
    wheel_hash = file_sha256(wheel)
    if lock["contourpy"]["sha256"] != wheel_hash:
        raise ValueError("ContourPy wheel differs from the release lock")
    manifest = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if match is None:
            raise ValueError("Invalid release file manifest record")
        digest, name = match.groups()
        if name in manifest:
            raise ValueError("Duplicate release file manifest record")
        manifest[name] = digest
    notices = root / "THIRD_PARTY_NOTICES" / wheel.stem
    verified_paths = [wheel, lock_path]
    member_hashes = {}
    with zipfile.ZipFile(wheel) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(entries) > 4096 or len(set(names)) != len(names):
            raise ValueError("Invalid ContourPy wheel member inventory")
        for leaf in ("METADATA", "LICENSE"):
            member = f"contourpy-1.3.2.dist-info/{leaf}"
            if member not in names:
                raise ValueError(f"ContourPy wheel lacks {leaf}")
            entry = archive.getinfo(member)
            if not 0 < entry.file_size <= 1024 * 1024:
                raise ValueError("ContourPy metadata exceeds validation limits")
            contents = archive.read(entry)
            notice = notices / f"{names.index(member)}-{leaf}"
            candidates = list(notices.glob(f"*-{leaf}"))
            if (
                candidates != [notice]
                or notice.is_symlink()
                or notice.stat().st_size != len(contents)
                or notice.read_bytes() != contents
            ):
                raise ValueError(
                    f"ContourPy {leaf} notice differs from the wheel bytes"
                )
            if leaf == "METADATA":
                metadata = BytesParser().parsebytes(contents)
                if (
                    metadata.get_all("Name") != ["contourpy"]
                    or metadata.get_all("Version") != ["1.3.2"]
                    or metadata.get_all("Requires-Python") != [">=3.10"]
                ):
                    raise ValueError("Unexpected ContourPy package metadata")
            elif contents.splitlines()[0].strip() != b"BSD 3-Clause License":
                raise ValueError("Unexpected ContourPy license")
            verified_paths.append(notice)
            member_hashes[leaf.lower() + "_sha256"] = hashlib.sha256(
                contents
            ).hexdigest()
    checked = {}
    for path in verified_paths:
        name = path.relative_to(root).as_posix()
        actual = file_sha256(path)
        if manifest.get(name) != actual:
            raise ValueError(
                f"ContourPy dependency file differs from FILES.sha256: {name}"
            )
        checked[name] = actual
    return {
        "status": "verified",
        "name": "contourpy",
        "version": "1.3.2",
        "python_target": "3.12",
        "wheel": wheel.name,
        "wheel_sha256": wheel_hash,
        "license": "BSD-3-Clause",
        **member_hashes,
        "release_lock_sha256": file_sha256(lock_path),
        "release_manifest_sha256": file_sha256(manifest_path),
        "verified_file_sha256": checked,
    }


def interface_ipv4() -> str:
    """Select an actual assigned address without contacting an external service."""
    import fcntl

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        for _, name in socket.if_nameindex():
            try:
                result = fcntl.ioctl(probe, 0x8915, struct.pack("256s", name.encode()))
            except OSError as error:
                # An interface may be IPv6-only; other failures must remain visible.
                if error.errno in {errno.EADDRNOTAVAIL, errno.ENODEV}:
                    continue
                raise
            address = ipaddress.IPv4Address(result[20:24])
            if not (
                address.is_loopback or address.is_unspecified or address.is_multicast
            ):
                return str(address)
    raise RuntimeError(
        "LAN archive verification requires a non-loopback IPv4 interface"
    )


def listener_addresses(port: int) -> set[str]:
    return {
        fields[1].split(":")[0]
        for line in Path("/proc/net/tcp").read_text().splitlines()[1:]
        if (fields := line.split())[3] == "0A"
        and int(fields[1].split(":")[1], 16) == port
    }


def assert_interface_isolated(address: str, port: int) -> None:
    with socket.socket() as probe:
        probe.settimeout(2)
        assert (
            probe.connect_ex((address, port)) != 0
        ), "Local-only server accepts LAN connections"


def unpack(archive: Path, destination: Path) -> Path:
    if destination.exists():
        raise ValueError("Release extraction requires a new destination")
    seen: set[str] = set()
    total_bytes = 0
    with tarfile.open(archive, "r:gz") as source:
        members = []
        for member in source:
            name = member.name.rstrip("/")
            parts = PurePosixPath(name).parts
            if (
                member.issym()
                or member.islnk()
                or not parts
                or parts[0] != "statistical-twin-linux"
                or any(part in {"", ".", ".."} for part in name.split("/"))
                or "\\" in name
                or ":" in name
                or "\x00" in name
                or name in seen
                or len(name) > 4096
                or member.size < 0
            ):
                raise ValueError("Unsafe release archive member")
            if not (member.isfile() or member.isdir()):
                raise ValueError("Unexpected special file in release")
            seen.add(name)
            total_bytes += member.size
            members.append(member)
            if len(members) > MAX_ARCHIVE_FILES or total_bytes > MAX_ARCHIVE_BYTES:
                raise ValueError("Release archive exceeds validation limits")
        destination.mkdir(parents=True)
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = source.extractfile(member)
                if stream is None:
                    raise ValueError("Release archive file cannot be read")
                with stream, target.open("xb") as output:
                    shutil.copyfileobj(stream, output, 1024 * 1024)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
    root = destination / "statistical-twin-linux"
    forbidden = {".git", ".venv", "node_modules", ".env", "workspace", "__pycache__"}
    if any(
        part in forbidden
        for path in root.rglob("*")
        for part in path.relative_to(root).parts
    ):
        raise ValueError("Release contains development or user state")
    if any(
        path.suffix.lower() in {".sqlite", ".sqlite3", ".db"}
        for path in root.rglob("*")
    ):
        raise ValueError("Release contains a database")
    return root


def bootstrap_identity(root: Path, env: dict[str, str], action: str) -> dict:
    if action not in {"verify-payload", "verify-installed"}:
        raise ValueError("Unsupported identity verification action")
    python = (
        env["PYTHON"] if action == "verify-payload" else str(root / ".venv/bin/python")
    )
    result = subprocess.run(
        [
            python,
            "-I",
            "-S",
            "-B",
            str(root / "release_bootstrap.py"),
            action,
            "--release-root",
            str(root),
        ],
        env=env,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    evidence = json.loads(result.stdout)
    status = "payload_verified" if action == "verify-payload" else "verified"
    if not isinstance(evidence, dict) or evidence.get("verification_status") != status:
        raise ValueError("Release identity verification evidence is incomplete")
    return evidence


def require_expected_identity(info: dict, source_commit: str, version: str) -> None:
    if (
        info.get("source_commit") != source_commit
        or info.get("release_version") != version
    ):
        raise ValueError(
            "Archive/installed identity differs from the requested source/version"
        )


def run_browser_stage(repo: Path, output: Path, *arguments: str) -> dict:
    if output.exists():
        raise ValueError("Browser evidence requires a new output directory")
    process = subprocess.Popen(
        [
            sys.executable,
            str(repo / "tests/e2e/linux_release.py"),
            "--output",
            str(output),
            *arguments,
        ],
        cwd=output.parent,
        start_new_session=True,
    )
    try:
        returncode = process.wait(timeout=600)
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, process.args)
    finally:
        stop(process)
    filename = (
        "offline-smoke.json"
        if "--offline-reports" in arguments
        else "resume-smoke.json"
        if "--resume-evidence" in arguments
        else "application-smoke.json"
    )
    evidence = json.loads((output / filename).read_text(encoding="utf-8"))
    require_browser_evidence(evidence, filename)
    return evidence


def require_browser_evidence(evidence: object, filename: str) -> None:
    phases = {
        "application-smoke.json": "initial",
        "resume-smoke.json": "resume",
        "offline-smoke.json": "offline",
    }
    if (
        not isinstance(evidence, dict)
        or type(evidence.get("schema_version")) is not int
        or evidence["schema_version"] != 2
        or evidence.get("status") != "succeeded"
        or filename not in phases
        or evidence.get("phase") != phases[filename]
    ):
        raise ValueError("Browser journey did not produce successful current evidence")
    if filename != "offline-smoke.json":
        methods = {
            "eda.principal_components",
            "regression.partial_least_squares",
            "regression.gaussian_process",
            "quality.two_variances",
        }
        analyses, predictions = evidence.get("analyses"), evidence.get("predictions")
        if (
            not isinstance(analyses, list)
            or len(analyses) != len(methods)
            or any(not isinstance(item, dict) for item in analyses)
            or {item.get("method_id") for item in analyses} != methods
            or not isinstance(predictions, list)
            or len(predictions) != 2
            or any(not isinstance(item, dict) for item in predictions)
            or {item.get("family") for item in predictions}
            != {"pls", "gaussian_process"}
        ):
            raise ValueError("Analysis/model restore coverage is incomplete")
    if filename == "resume-smoke.json":
        if (
            type(evidence.get("analysis_post_count")) is not int
            or evidence["analysis_post_count"] != 0
        ):
            raise ValueError("Restore journey must not resubmit an analysis")
        require_rsm_phase_receipt(evidence.get("doe_rsm_receipt"), "resume")
    elif filename == "offline-smoke.json":
        reports = evidence.get("reports")
        if (
            evidence.get("original_server_unreachable") is not True
            or evidence.get("browser_network_offline") is not True
            or type(evidence.get("http_request_count")) is not int
            or evidence["http_request_count"] != 0
            or not isinstance(reports, list)
            or len(reports) != 4
            or any(not isinstance(item, dict) for item in reports)
            or {(item.get("family"), item.get("locale")) for item in reports}
            != {
                (family, locale)
                for family in ("pls", "gaussian_process")
                for locale in ("ko", "en")
            }
        ):
            raise ValueError("Server-stopped offline report evidence is incomplete")
        require_rsm_phase_receipt(evidence.get("doe_rsm_receipt"), "offline")
    elif filename == "application-smoke.json":
        checks = evidence.get("network_guard_checks")
        if (
            type(evidence.get("ui_analysis_post_count")) is not int
            or evidence["ui_analysis_post_count"] != 3
            or not isinstance(checks, list)
            or len(checks) != 9
            or any(not isinstance(item, str) or not item for item in checks)
            or len(set(checks)) != 9
        ):
            raise ValueError("Initial application journey evidence is incomplete")
        require_doe_rsm_receipt(evidence.get("doe_rsm_receipt"))
        require_fractional_receipt(evidence.get("fractional_receipt"))
        require_doe_zoom_receipt(
            evidence.get("doe_zoom_receipt"), evidence["doe_rsm_receipt"]
        )
    else:
        raise ValueError("Unknown browser evidence phase")


def _receipt_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def _receipt_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _receipt_number(value: object) -> bool:
    return type(value) in {int, float} and math.isfinite(value)


def require_doe_zoom_receipt(receipt: object, rsm: dict) -> None:
    if (
        not isinstance(receipt, dict)
        or type(receipt.get("schema_version")) is not int
        or receipt["schema_version"] != 1
        or receipt.get("status") != "passed"
        or receipt.get("fixture") != "synthetic saved RSM analysis"
        or receipt.get("mechanism") != "chrome.tabs.setZoom/getZoom"
        or receipt.get("deviceScaleFactor_override") is not False
        or receipt.get("fractional_zoom") != "not_exercised_by_this_fixture"
        or receipt.get("design_id") != rsm["design_id"]
        or receipt.get("analysis_id") != rsm["analysis_id"]
        or not _receipt_sha256(receipt.get("analysis_sha256"))
        or receipt.get("analysis_sha256") != rsm["result_payload_sha256"]
        or type(receipt.get("analysis_post_count")) is not int
        or receipt["analysis_post_count"] != 0
        or any(
            receipt.get(field) is not True
            for field in (
                "source_unchanged",
                "draft_preserved",
                "plot_coordinates_unchanged",
                "committed_result_dom_preserved",
            )
        )
    ):
        raise ValueError("Actual saved DOE browser zoom evidence is incomplete")
    steps = receipt.get("steps")
    expected = [
        (locale, factor) for locale in ("ko", "en") for factor in (1.0, 1.25, 1.5, 1.0)
    ]
    if not isinstance(steps, list) or len(steps) != len(expected):
        raise ValueError(
            "DOE zoom must exercise 100/125/150/100 percent in both locales"
        )
    for step, (locale, factor) in zip(steps, expected, strict=True):
        if (
            not isinstance(step, dict)
            or step.get("locale") != locale
            or not _receipt_number(step.get("browserZoom"))
            or abs(step["browserZoom"] - factor) >= 1e-9
            or not isinstance(step.get("viewport"), dict)
            or not _receipt_number(step["viewport"].get("width"))
            or abs(step["viewport"]["width"] - 1440 / factor) > 2
            or not _receipt_number(step.get("scrollWidth"))
            or not 0 < step["scrollWidth"] <= step["viewport"]["width"] + 1
            or not _receipt_number(step.get("devicePixelRatio"))
            or step["devicePixelRatio"] <= 0
            or type(step.get("compactCount")) is not int
            or step["compactCount"] != 10
            or not isinstance(step.get("columns"), list)
            or not step["columns"]
            or any(
                type(count) is not int or count not in {1, 2, 3, 4}
                for count in step["columns"]
            )
            or any(
                not isinstance(step.get(field), list)
                or not step[field]
                or any(not isinstance(item, dict) for item in step[field])
                for field in ("summary", "charts")
            )
        ):
            raise ValueError("DOE browser zoom measured layout evidence is incomplete")


def require_fractional_receipt(receipt: object) -> None:
    if (
        not isinstance(receipt, dict)
        or type(receipt.get("schema_version")) is not int
        or receipt["schema_version"] != 1
        or receipt.get("status") != "succeeded"
        or receipt.get("fixture") != "synthetic"
        or not isinstance(receipt.get("locales"), dict)
        or set(receipt["locales"]) != {"ko", "en"}
    ):
        raise ValueError("Fractional-design UI evidence is missing or incomplete")
    expected_aliases = {
        "factor_3:factor_4": "factor_1:factor_2",
        "factor_2:factor_4": "factor_1:factor_3",
        "factor_2:factor_3": "factor_1:factor_4",
    }
    identifiers = []
    for item in receipt["locales"].values():
        if (
            not isinstance(item, dict)
            or any(
                not _receipt_uuid(item.get(key))
                for key in (
                    "five_factor_design_id",
                    "saturated_analysis_id",
                    "four_factor_design_id",
                )
            )
            or any(
                not _receipt_sha256(item.get(key))
                for key in ("five_factor_design_sha256", "four_factor_design_sha256")
            )
            or type(item.get("preflight_rank")) is not int
            or item["preflight_rank"] != 16
            or type(item.get("saturated_residual_df")) is not int
            or item["saturated_residual_df"] != 0
            or not isinstance(item.get("pooled_term_ids"), list)
            or len(item["pooled_term_ids"]) != 4
            or any(
                not isinstance(term, str)
                or re.fullmatch(r"factor_[1-5](?::factor_[1-5])?", term) is None
                for term in item["pooled_term_ids"]
            )
            or len(set(item["pooled_term_ids"])) != 4
        ):
            raise ValueError(
                "Fractional-design rank or initial pooling evidence is incomplete"
            )
        aliases = item.get("alias_representatives")
        if (
            not isinstance(aliases, dict)
            or set(aliases) != set(expected_aliases)
            or any(
                not isinstance(aliases[term], dict)
                or aliases[term].get("term_id") != term
                or aliases[term].get("representative_term_id") != representative
                or aliases[term].get("reason") != "complete_alias"
                or type(aliases[term].get("sign")) is not int
                or aliases[term]["sign"] != 1
                for term, representative in expected_aliases.items()
            )
        ):
            raise ValueError("Fractional-design signed alias evidence is incomplete")
        identifiers.extend(
            item[key]
            for key in (
                "five_factor_design_id",
                "saturated_analysis_id",
                "four_factor_design_id",
            )
        )
        for key in ("backward", "four_factor"):
            report = item.get(key)
            if (
                not isinstance(report, dict)
                or any(
                    not _receipt_uuid(report.get(field))
                    for field in ("analysis_id", "asset_id")
                )
                or any(
                    not _receipt_sha256(report.get(field))
                    for field in ("analysis_sha256", "report_sha256")
                )
                or type(report.get("report_svg_count")) is not int
                or report["report_svg_count"] <= 0
                or any(
                    report.get(field) is not True
                    for field in (
                        "source_unchanged",
                        "restore_without_analysis",
                        "standalone_network_blocked",
                    )
                )
            ):
                raise ValueError(
                    "Fractional-design report or restore evidence is incomplete"
                )
            identifiers.extend((report["analysis_id"], report["asset_id"]))
    if len(set(identifiers)) != len(identifiers):
        raise ValueError(
            "Fractional-design journeys did not create distinct owners and reports"
        )


def require_doe_rsm_receipt(receipt: object) -> None:
    """Require the initial real UI journey; this does not claim DOE restart coverage."""
    if (
        not isinstance(receipt, dict)
        or type(receipt.get("schema_version")) is not int
        or receipt["schema_version"] != 1
        or receipt.get("status") != "succeeded"
        or receipt.get("fixture") != "synthetic"
    ):
        raise ValueError("DOE/RSM browser receipt is missing or incomplete")

    designs, analyses = receipt.get("designs"), receipt.get("analyses")
    if (
        not isinstance(designs, list)
        or len(designs) != 3
        or any(
            not isinstance(item, dict)
            or not _receipt_uuid(item.get("id"))
            or not _receipt_sha256(item.get("sha256"))
            or not isinstance(item.get("coding"), dict)
            or len(item["coding"]) != 4
            for item in designs
        )
        or {item.get("kind") for item in designs}
        != {"inscribed", "face_centered", "circumscribed"}
        or len({item["id"] for item in designs}) != 3
        or not isinstance(analyses, list)
        or len(analyses) != 4
        or any(
            not isinstance(item, dict) or not _receipt_uuid(item.get("id"))
            for item in analyses
        )
        or {item.get("preset") for item in analyses}
        != {"linear", "linear_squares", "linear_interactions", "full_quadratic"}
        or len({item["id"] for item in analyses}) != 4
        or any(
            not _receipt_uuid(receipt.get(key))
            for key in ("design_id", "analysis_id", "view", "report_id")
        )
        or receipt["design_id"]
        != next(item["id"] for item in designs if item["kind"] == "circumscribed")
        or receipt["analysis_id"] in {item["id"] for item in analyses}
        or not _receipt_sha256(receipt.get("report_sha256"))
        or not _receipt_sha256(receipt.get("result_payload_sha256"))
        or not _receipt_sha256(receipt.get("view_sha256"))
        or not isinstance(receipt.get("report_path"), str)
        or not Path(receipt["report_path"]).is_absolute()
    ):
        raise ValueError(
            "DOE/RSM design, model, saved view, or report coverage is incomplete"
        )
    dimensions = receipt.get("resize_content_widths")
    if (
        not isinstance(dimensions, list)
        or len(dimensions) != 8
        or any(
            not isinstance(item, dict)
            or type(item.get("viewport")) is not int
            or type(item.get("content")) not in {int, float}
            or not math.isfinite(item["content"])
            or not 0 < item["content"] <= item["viewport"] + 1
            or type(item.get("columns")) is not int
            or item["columns"]
            != (
                4
                if item["content"] >= 1040
                else 3
                if item["content"] >= 780
                else 2
                if item["content"] >= 520
                else 1
            )
            for item in dimensions
        )
        or [item["viewport"] for item in dimensions]
        != [1920, 1440, 1280, 1024, 900, 768, 390, 1440]
        or {item["columns"] for item in dimensions} != {1, 2, 3, 4}
        or receipt.get("browser_zoom") != "not exercised by this fixture"
    ):
        raise ValueError(
            "DOE/RSM resize evidence or browser zoom limitation is incomplete"
        )


def require_rsm_phase_receipt(receipt: object, phase: str) -> None:
    if (
        not isinstance(receipt, dict)
        or type(receipt.get("schema_version")) is not int
        or receipt["schema_version"] != 1
        or receipt.get("status") != "succeeded"
        or phase not in {"resume", "offline"}
        or receipt.get("phase") != phase
        or not _receipt_uuid(receipt.get("report_id"))
        or not _receipt_sha256(receipt.get("report_sha256"))
    ):
        raise ValueError("RSM restart/offline evidence is incomplete")
    if phase == "offline":
        if receipt.get("visible_stored_geometry") is not True:
            raise ValueError("Offline RSM report must display its stored geometry")
        return
    if (
        any(
            not _receipt_uuid(receipt.get(key))
            for key in ("design_id", "analysis_id", "view")
        )
        or any(
            not _receipt_sha256(receipt.get(key))
            for key in ("result_payload_sha256", "view_sha256")
        )
        or type(receipt.get("analysis_post_count")) is not int
        or receipt["analysis_post_count"] != 0
        or receipt.get("visible_saved_view_restored") is not True
        or receipt.get("report_bytes_unchanged") is not True
    ):
        raise ValueError(
            "RSM restart must restore the saved view/report without refitting"
        )


def require_rsm_roundtrip(smoke: dict, restarts: list[dict], offline: dict) -> dict:
    require_browser_evidence(smoke, "application-smoke.json")
    require_browser_evidence(offline, "offline-smoke.json")
    initial = smoke.get("doe_rsm_receipt")
    require_doe_rsm_receipt(initial)
    assert isinstance(initial, dict)
    expected = {
        key: initial[key]
        for key in (
            "design_id",
            "analysis_id",
            "view",
            "report_id",
            "result_payload_sha256",
            "view_sha256",
            "report_sha256",
        )
    }
    if len(restarts) != 2:
        raise ValueError(
            "RSM requires both same-install and second-install restart evidence"
        )
    for restart in restarts:
        require_browser_evidence(restart, "resume-smoke.json")
        restored = restart.get("doe_rsm_receipt")
        require_rsm_phase_receipt(restored, "resume")
        if any(restored[key] != value for key, value in expected.items()):
            raise ValueError("RSM restart changed its exact owner or stored bytes")
    stopped = offline.get("doe_rsm_receipt")
    require_rsm_phase_receipt(stopped, "offline")
    if any(stopped[key] != expected[key] for key in ("report_id", "report_sha256")):
        raise ValueError("Offline RSM report differs from the original saved export")
    return {
        **expected,
        "restart_count": 2,
        "restored_saved_view_visible": True,
        "report_bytes_unchanged": True,
        "server_stopped_stored_geometry_visible": True,
    }


def verify_installed_refusal_probes(
    root: Path, env: dict[str, str], output: Path
) -> list[str]:
    """Mutate only disposable extracted files, restoring their exact bytes afterward."""
    marker = root / ".installed"
    original_marker = marker.read_bytes()
    site = root / ".venv/lib/python3.12/site-packages/app"
    initializer = site / "__init__.py"
    original_initializer = initializer.read_bytes()
    build_resource = site / "_release_build.json"
    original_build = build_resource.read_bytes()
    untouched_workspace = output / "must-not-be-created-workspace"
    sentinel = output / "must-not-run-old-application"
    probes = []

    def refused(name: str) -> None:
        process = subprocess.Popen(
            [
                str(root / "run.sh"),
                "--local-only",
                "--workspace-root",
                str(untouched_workspace),
            ],
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            stop(process)
            raise RuntimeError(
                f"Mixed-install refusal did not terminate: {name}"
            ) from None
        finally:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
        (output / f"refusal-{name}.log").write_text(stdout + stderr, encoding="utf-8")
        if process.returncode == 0 or untouched_workspace.exists() or sentinel.exists():
            raise RuntimeError(f"Mixed-install refusal failed: {name}")
        probes.append(name)

    try:
        marker.unlink()
        refused("missing-marker")
        marker.write_bytes(original_marker)
        changed = json.loads(original_marker)
        changed["source_commit"] = "0" * 40
        marker.write_text(json.dumps(changed), encoding="utf-8")
        refused("foreign-marker")
        marker.write_bytes(original_marker)
        changed = json.loads(original_build)
        changed["source_commit"] = "0" * 40
        build_resource.write_text(json.dumps(changed), encoding="utf-8")
        refused("foreign-installed-build")
        build_resource.write_bytes(original_build)
        # Even a matching new build-resource must not legitimize changed old code.
        initializer.write_bytes(
            original_initializer
            + (
                f"\nfrom pathlib import Path\nPath({str(sentinel)!r}).write_text('executed')\n"
            ).encode()
        )
        refused("changed-code-with-matching-build-resource")
        initializer.write_bytes(original_initializer)
        wheels = list((root / "wheels").glob("datalab_studio_backend-*.whl"))
        if len(wheels) != 1:
            raise ValueError(
                "Expected exactly one application wheel for refusal fixture"
            )
        wheel = wheels[0]
        wheel_bytes = wheel.read_bytes()
        try:
            wheel.write_bytes(wheel_bytes + b"corrupted fixture")
            refused("corrupt-wheelhouse")
        finally:
            wheel.write_bytes(wheel_bytes)
    finally:
        marker.write_bytes(original_marker)
        initializer.write_bytes(original_initializer)
        build_resource.write_bytes(original_build)
    return probes


def verify_live_reinstall_refusal(
    root: Path, env: dict[str, str], output: Path
) -> dict:
    marker_sha256 = file_sha256(root / ".installed")
    before = bootstrap_identity(root, env, "verify-installed")
    with (output / "live-reinstall-refusal.log").open("wb") as log:
        process = subprocess.Popen(
            [str(root / "install.sh")],
            cwd=root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            stop(process)
            raise RuntimeError(
                "Live installation lock refusal did not terminate"
            ) from None
    message = (output / "live-reinstall-refusal.log").read_text(encoding="utf-8")
    if returncode == 0 or "Release is in use" not in message:
        raise ValueError("Installer did not reject the running release")
    if file_sha256(root / ".installed") != marker_sha256:
        raise ValueError("Rejected installer changed the installation marker")
    after = bootstrap_identity(root, env, "verify-installed")
    if before != after:
        raise ValueError("Rejected installer changed the installed application")
    return {
        "status": "passed",
        "install_exit_code": returncode,
        "marker_sha256": marker_sha256,
        "installed_identity_unchanged": True,
    }


def immutable_workspace_files(workspace: Path) -> dict[str, str]:
    result = {}
    for namespace in ("workspaces", "artifacts"):
        directory = workspace / namespace
        if directory.is_symlink():
            raise ValueError("Unexpected linked synthetic workspace namespace")
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("Unexpected link in synthetic validation workspace")
            if path.is_file():
                result[path.relative_to(workspace).as_posix()] = file_sha256(path)
    if not result:
        raise ValueError("No persisted synthetic artifacts were created")
    return result


def require_unchanged_artifacts(workspace: Path, expected: dict[str, str]) -> None:
    current = immutable_workspace_files(workspace)
    if any(current.get(path) != digest for path, digest in expected.items()):
        raise ValueError("A previously persisted source/model/report artifact changed")


def require_pilot_receipts(smoke: dict, restarts: list[dict], offline: dict) -> dict:
    """Supplement, never replace, the existing strict archive/identity evidence."""
    receipt = smoke.get("pilot_receipt", {})
    if receipt.get("schema_version") != 1 or receipt.get("status") != "succeeded":
        raise ValueError("Missing completed archive pilot UI receipt")
    for name in ("ingestion", "groups", "prediction", "two_variances", "legacy"):
        if receipt.get(name, {}).get("status") != "succeeded":
            raise ValueError(f"Incomplete pilot UI journey: {name}")
    groups = receipt["groups"]
    variances = receipt["two_variances"]
    prediction = receipt["prediction"]
    legacy = receipt["legacy"]
    seed = legacy["seed"]
    if (
        seed["status"] != "seeded_new_workspace"
        or seed["existing_records_modified"] is not False
        or seed["analysis_calculations_executed"] != 0
    ):
        raise ValueError("Legacy records were not independently provisioned")
    if (
        seed["source_commit"] != "0849aaa279e34a612c5c65d350cfccf220fe581e"
        or legacy["analysis_post_count"] != 0
    ):
        raise ValueError("Legacy source identity or no-recalculation proof differs")
    if {entry["envelope"]["method_id"] for entry in groups["analyses"]} != {
        "eda.equal_variances",
        "hypothesis.kruskal_wallis",
        "hypothesis.two_sample_t",
    }:
        raise ValueError("Pilot group-method coverage is incomplete")
    if {entry["envelope"]["result"]["method"] for entry in variances["analyses"]} != {
        "brown_forsythe",
        "normal_f",
    }:
        raise ValueError("Both visible Two Variances forms must run")
    if not variances["preflight"]["eligible"] or any(
        entry.get("execution_evidence") != "visible built/source UI form with preflight"
        for entry in variances["analyses"]
    ):
        raise ValueError("API-only Two Variances is not pilot form evidence")
    analyses = [
        *groups["analyses"],
        *variances["analyses"],
        {"envelope": prediction["envelope"]},
        *legacy["analyses"],
    ]
    expected_analyses = {
        entry["envelope"]["analysis_id"]: hashlib.sha256(
            json.dumps(
                entry["envelope"]["result"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        for entry in analyses
    }
    legacy_versions = {
        "eda.equal_variances": ("0.2.0", 2),
        "hypothesis.kruskal_wallis": ("0.1.0", 1),
        "hypothesis.two_sample_t": ("0.1.0", 1),
    }
    seed_cases = {case["analysis_id"]: case for case in seed["cases"]}
    if len(seed_cases) != 3 or len(legacy["analyses"]) != 3:
        raise ValueError("Legacy seeded source coverage is incomplete")
    if {item["envelope"]["method_id"] for item in legacy["analyses"]} != set(
        legacy_versions
    ):
        raise ValueError("Legacy seeded method coverage differs")
    for item in legacy["analyses"]:
        envelope = item["envelope"]
        case = seed_cases.get(envelope["analysis_id"], {})
        if (
            case.get("result_payload_sha256")
            != expected_analyses[envelope["analysis_id"]]
            or case.get("method_id") != envelope["method_id"]
            or (envelope["method_version"], envelope["result"]["schema_version"])
            != legacy_versions[envelope["method_id"]]
        ):
            raise ValueError("Legacy saved source bytes or version differs")
    for item in legacy["reports"]:
        descriptor = item["descriptor"]
        case = seed_cases.get(descriptor["analysis_id"], {})
        if descriptor["source_result_sha256"] != case.get("artifact_file_sha256"):
            raise ValueError("Legacy report source checksum differs")
    reports = [
        *groups["reports"],
        *variances["reports"],
        prediction["generic_report"],
        *prediction["saved"]["reports"],
        *legacy["reports"],
    ]
    expected_reports = {
        entry["descriptor"]["export_id"]: entry["descriptor"]["sha256"]
        for entry in reports
    }
    if (
        len(analyses) != 9
        or len(expected_analyses) != 9
        or len(reports) != 17
        or len(expected_reports) != 17
    ):
        raise ValueError("Pilot source/report identities are incomplete or duplicated")
    for stage in [*restarts, offline]:
        proof = stage.get("pilot_receipt", {})
        if proof.get("schema_version") != 1 or proof.get("status") != "succeeded":
            raise ValueError("Pilot restart/offline receipt is missing")
        actual_reports = {
            entry["export_id"]: entry["sha256"] for entry in proof["reports"]
        }
        if (
            len(proof["reports"]) != len(expected_reports)
            or actual_reports != expected_reports
        ):
            raise ValueError("Pilot report bytes changed or were not restored")
        if stage in restarts:
            actual = {
                entry["analysis_id"]: entry["result_payload_sha256"]
                for entry in proof["analyses"]
            }
            if (
                len(proof["analyses"]) != len(expected_analyses)
                or actual != expected_analyses
            ):
                raise ValueError("Pilot analysis payload changed or was not restored")
            if (
                proof["prediction"].get("same_saved_model_prediction") is not True
                or proof["prediction"]["rows"] != prediction["prediction"]["rows"]
            ):
                raise ValueError("Pilot saved GP prediction differs after restart")
    return {
        "schema_version": 1,
        "status": "passed",
        "analysis_count": 9,
        "report_count": 17,
        "restart_count": len(restarts),
        "offline_report_count": 17,
        "legacy_analysis_count": 3,
    }


def seed_pilot_legacy_records(
    repo: Path, root: Path, workspace: Path, output: Path, env: dict
) -> dict:
    """Trusted verification-only provisioning, separate from the black-box browser."""
    receipt = output / "pilot-legacy-seed.json"
    with (output / "pilot-legacy-seed.log").open("wb") as log:
        completed = subprocess.run(
            [
                str(root / ".venv/bin/python"),
                "-I",
                "-B",
                str(repo / "tests/e2e/seed_pilot_legacy.py"),
                "--workspace-root",
                str(workspace),
                "--fixture",
                str(
                    repo
                    / "backend/tests/reference/fixtures/group_identity_legacy_base.json"
                ),
                "--output",
                str(receipt),
            ],
            cwd=root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=180,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError(
            "Legacy verification-only provisioning failed; inspect seed log"
        )
    result = json.loads(receipt.read_text(encoding="utf-8"))
    if (
        result.get("status") != "seeded_new_workspace"
        or result.get("existing_records_modified") is not False
    ):
        raise ValueError("Legacy provisioning receipt is incomplete")
    return result


def wait_ready(base: str, process: subprocess.Popen, expected: dict) -> dict:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "Release server exited during startup; inspect server log"
            )
        try:
            with HTTP.open(base + "/api/v1/runtime-info", timeout=2) as response:
                info = json.load(response)
            assert info["build_commit"] == expected["source_commit"]
            assert info["api_contract_version"] == expected["api_contract_version"]
            assert (
                info["metadata_schema_version"] == expected["metadata_schema_version"]
            )
            assert info["service"] == "datalab-studio-api"
            assert all(
                info.get("capabilities", {}).get(key) is value
                for key, value in expected["required_capabilities"].items()
            )
            return info
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.3)
    raise RuntimeError("Release server startup timed out")


def stop(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        pass
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8600)
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--expected-release-version", required=True)
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error("Run release validation without Python optimization")
    if platform.system() != "Linux" or sys.version_info[:2] != (3, 12):
        parser.error("Validate on Linux CPython 3.12")
    if not re.fullmatch(r"[a-f0-9]{40}", args.expected_source_commit):
        parser.error("Expected source must be a full commit SHA")
    archive = args.archive.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Use a new empty validation output directory")
    output.mkdir(parents=True, exist_ok=True)
    archive_sha256 = file_sha256(archive)
    repo = Path(__file__).resolve().parents[1]
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("0.0.0.0", args.port))
    lan_address = interface_ipv4()
    lan_base = f"http://{lan_address}:{args.port}"
    loopback_base = f"http://127.0.0.1:{args.port}"
    with tempfile.TemporaryDirectory(
        prefix="statistical-twin-archive-check-"
    ) as temporary:
        temp = Path(temporary)
        binaries = temp / "runtime-path"
        binaries.mkdir()
        for name in ("bash", "dirname"):
            executable = shutil.which(name)
            if executable is None:
                raise RuntimeError(f"Missing prerequisite: {name}")
            (binaries / name).symlink_to(executable)
        # Installation and server PATH deliberately contain neither Node nor Git.
        env = dict(
            {
                key: os.environ[key]
                for key in ("HOME", "TMPDIR", "LANG", "LC_ALL", "LD_LIBRARY_PATH")
                if key in os.environ
            },
            PATH=str(binaries),
            PYTHON=sys._base_executable,
            PIP_NO_INDEX="1",
            PIP_DISABLE_PIP_VERSION_CHECK="1",
        )
        workspace = temp / "external workspace 검증"
        smoke = None
        installations = []
        contour_dependencies = []
        isolated_installs = []
        restarts = []
        refusal_probes = []
        live_install_refusal = None
        offline = None
        artifact_hashes: dict[str, str] = {}
        initial_evidence = output / "initial/application-smoke.json"
        legacy_seed = None
        for index in range(2):
            root = unpack(archive, temp / f"installation {index} 검증")
            for dependency in ("react", "react-dom", "lucide-react", "noble_hashes"):
                notices = list(
                    (root / "THIRD_PARTY_NOTICES/frontend").glob(f"{dependency}-*")
                )
                assert notices and any(
                    path.name.lower().startswith("license")
                    for directory in notices
                    for path in directory.iterdir()
                ), f"Missing frontend license notice: {dependency}"
            payload = bootstrap_identity(root, env, "verify-payload")
            require_expected_identity(
                payload, args.expected_source_commit, args.expected_release_version
            )
            contour_dependencies.append(verify_contour_dependency(root))
            expected = json.loads(
                (root / "BUILD_INFO.json").read_text(encoding="utf-8")
            )
            require_expected_identity(
                expected, args.expected_source_commit, args.expected_release_version
            )
            isolated_installs.append(
                run_network_blocked_install(
                    root,
                    env,
                    output / f"install-{index}.log",
                    output / f"install-{index}-network.json",
                )
            )
            installed = bootstrap_identity(root, env, "verify-installed")
            require_expected_identity(
                installed, args.expected_source_commit, args.expected_release_version
            )
            if index == 0:
                refusal_probes = verify_installed_refusal_probes(root, env, output)
                isolated_installs.append(
                    run_network_blocked_install(
                        root,
                        env,
                        output / "reinstall-0.log",
                        output / "reinstall-0-network.json",
                    )
                )
                installed = bootstrap_identity(root, env, "verify-installed")
                require_expected_identity(
                    installed,
                    args.expected_source_commit,
                    args.expected_release_version,
                )
            installations.append(installed)
            assert (
                not workspace.exists() or index == 1
            ), "Installer must not create a workspace"
            if index == 0:
                legacy_seed = seed_pilot_legacy_records(
                    repo, root, workspace, output, env
                )
                # The test provisioner must not mutate installed application bytes.
                if bootstrap_identity(root, env, "verify-installed") != installed:
                    raise ValueError("Legacy setup changed the installed application")
            command = [str(root / "run.sh"), "--workspace-root", str(workspace)]
            # Omit --port at 8600 to exercise the published launcher default itself.
            if args.port != 8600:
                command.extend(["--port", str(args.port)])
            if index == 1:
                command.append("--local-only")
            base = lan_base if index == 0 else loopback_base
            for cycle in range(2 if index == 0 else 1):
                proof = bootstrap_identity(root, env, "verify-installed")
                require_expected_identity(
                    proof, args.expected_source_commit, args.expected_release_version
                )
                with (output / f"server-{index}-{cycle}.log").open("wb") as log:
                    process = subprocess.Popen(
                        command,
                        cwd=root,
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                    try:
                        wait_ready(base, process, expected)
                        assert listener_addresses(args.port) == {
                            "00000000" if index == 0 else "0100007F"
                        }, "Release bound a different interface than requested"
                        if index == 0:
                            wait_ready(loopback_base, process, expected)
                        else:
                            assert_interface_isolated(lan_address, args.port)
                        if index == 0 and cycle == 0:
                            live_install_refusal = verify_live_reinstall_refusal(
                                root, env, output
                            )
                            wait_ready(base, process, expected)
                            smoke = run_browser_stage(
                                repo,
                                output / "initial",
                                "--url",
                                base,
                                "--legacy-seed-receipt",
                                str(output / "pilot-legacy-seed.json"),
                            )
                        else:
                            restarts.append(
                                run_browser_stage(
                                    repo,
                                    output / f"resume-{index}-{cycle}",
                                    "--url",
                                    base,
                                    "--resume-evidence",
                                    str(initial_evidence),
                                )
                            )
                    finally:
                        stop(process)
                assert not listener_addresses(
                    args.port
                ), "Release listener survived shutdown"
                if index == 0 and cycle == 0:
                    artifact_hashes = immutable_workspace_files(workspace)
                    offline = run_browser_stage(
                        repo,
                        output / "server-stopped-offline",
                        "--offline-reports",
                        str(initial_evidence),
                    )
                else:
                    require_unchanged_artifacts(workspace, artifact_hashes)
        if (
            len(installations) != 2
            or len(contour_dependencies) != 2
            or contour_dependencies[0] != contour_dependencies[1]
            or len(isolated_installs) != 3
            or len(restarts) != 2
            or live_install_refusal is None
            or offline is None
            or smoke is None
        ):
            raise RuntimeError("Release verification phases are incomplete")
        if file_sha256(archive) != archive_sha256:
            raise ValueError("Archive bytes changed during validation")
        pilot_checks = require_pilot_receipts(smoke, restarts, offline)
        rsm_checks = require_rsm_roundtrip(smoke, restarts, offline)
        report = {
            "schema_version": 2,
            "status": "passed",
            "archive": archive.name,
            "archive_sha256": archive_sha256,
            "source_commit": expected["source_commit"],
            "release_version": expected["release_version"],
            "actual_platform": platform.platform(),
            "python": platform.python_version(),
            "node_and_git_in_install_runtime_path": False,
            "offline_installations": 2,
            "offline_reinstallations": 1,
            "network_blocked_installations": isolated_installs,
            "installed_identities": installations,
            "contour_dependency_checks": contour_dependencies,
            "mixed_install_refusal_probes": refusal_probes,
            "live_installation_refusal": live_install_refusal,
            "same_install_restart_restore": True,
            "shared_external_workspace_restart_restore": True,
            "restart_journeys": restarts,
            "server_stopped_offline_reports": offline,
            "persisted_artifact_sha256": artifact_hashes,
            "persisted_artifacts_unchanged_after_restarts": True,
            "default_port_exercised": args.port == 8600,
            "listen_port": args.port,
            "lan_interface_ipv4": lan_address,
            "default_lan_bind": "0.0.0.0",
            "local_only_bind": "127.0.0.1",
            "local_only_interface_connection_rejected": True,
            "company_peer_or_firewall_tested": False,
            "application": smoke,
            "pilot_checks": pilot_checks,
            "doe_rsm_checks": rsm_checks,
            "pilot_legacy_provisioning": legacy_seed,
        }
        (output / "validation-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    key: report[key]
                    for key in ("status", "archive_sha256", "source_commit")
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
