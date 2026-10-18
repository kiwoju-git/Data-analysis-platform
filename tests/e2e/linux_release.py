"""Black-box archive smoke: no imports from the installed application's source."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(base: str, path: str, body: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if body is not None:
        headers["Origin"] = base
    req = urllib.request.Request(
        base + path,
        data=None if body is None else json.dumps(body).encode(),
        headers=headers,
    )
    with HTTP.open(req, timeout=180) as response:
        return json.load(response)


def verify_network_guards(base: str) -> list[str]:
    endpoint = urllib.parse.urlsplit(base)
    checks = [
        (
            "untrusted Host",
            "GET",
            {"Host": "untrusted.invalid"},
            400,
            "release_host_not_allowed",
        ),
        (
            "wrong Host port",
            "GET",
            {"Host": endpoint.hostname + ":1"},
            400,
            "release_host_not_allowed",
        ),
        (
            "forwarded Host cannot authorize",
            "GET",
            {"Host": "untrusted.invalid", "X-Forwarded-Host": endpoint.netloc},
            400,
            "release_host_not_allowed",
        ),
        ("missing Origin mutation", "POST", {}, 403, "release_origin_not_allowed"),
        (
            "foreign Origin mutation",
            "POST",
            {"Origin": "http://untrusted.invalid"},
            403,
            "release_origin_not_allowed",
        ),
        (
            "null Origin mutation",
            "POST",
            {"Origin": "null"},
            403,
            "release_origin_not_allowed",
        ),
        (
            "wrong Origin port",
            "POST",
            {"Origin": f"http://{endpoint.hostname}:1"},
            403,
            "release_origin_not_allowed",
        ),
        (
            "cross-site fetch",
            "GET",
            {"Origin": base, "Sec-Fetch-Site": "cross-site"},
            403,
            "release_origin_not_allowed",
        ),
        (
            "foreign preflight",
            "OPTIONS",
            {
                "Origin": "http://untrusted.invalid",
                "Access-Control-Request-Method": "POST",
            },
            403,
            "release_origin_not_allowed",
        ),
    ]
    for name, method, headers, status, code in checks:
        path = "/api/v1/datasets/paste" if method == "POST" else "/api/v1/runtime-info"
        req = urllib.request.Request(
            base + path,
            data=b"{}" if method == "POST" else None,
            method=method,
            headers={"Content-Type": "application/json", **headers},
        )
        try:
            with HTTP.open(req, timeout=10):
                raise AssertionError(f"Network guard accepted {name}")
        except urllib.error.HTTPError as error:
            assert error.code == status, name
            payload = json.load(error)
            assert payload["error"]["code"] == code, name
            assert payload["error"]["correlation_id"], name
            assert error.headers.get("Access-Control-Allow-Origin") is None, name
    return [name for name, *_ in checks]


def verify_application(base: str, output: Path, legacy_seed: dict) -> dict:
    from linux_release_journey import payload_digest, run_initial, run_pilot_initial

    result = run_initial(base, output, request)
    version = result["version"]
    columns = {
        column["display_name"]: column["column_id"] for column in version["columns"]
    }
    catalog = request(base, "/api/v1/analysis-methods")
    method = next(
        item
        for item in catalog["methods"]
        if item["method_id"] == "quality.two_variances"
    )
    source = request(
        base,
        "/api/v1/analysis-runs",
        {
            "method_id": method["method_id"],
            "method_version": method["method_version"],
            "dataset_version_id": version["version_id"],
            "roles": {},
            "options": {
                "response_column_id": columns["yield_pct"],
                "group_column_id": columns["group"],
                "numerator_group_key": "A",
                "denominator_group_key": "B",
            },
        },
    )
    assert source["result"]["summary_type"] == "two_variances_test"
    result["analyses"].append(
        {
            "method_id": method["method_id"],
            "analysis_id": source["analysis_id"],
            "envelope": source,
            "execution_evidence": "API smoke, not visible Two Variances form",
            "result_payload_sha256": payload_digest(source["result"]),
        }
    )
    for analysis in result["analyses"]:
        analysis_id = analysis["analysis_id"]
        restored = request(base, f"/api/v1/analysis-runs/{analysis_id}/result")
        assert payload_digest(restored["result"]) == analysis["result_payload_sha256"]
        export = request(
            base, f"/api/v1/analysis-runs/{analysis_id}/exports/html", {"locale": "en"}
        )
        with HTTP.open(
            base
            + f"/api/v1/analysis-runs/{analysis_id}/exports/{export['export_id']}/download",
            timeout=30,
        ) as response:
            html = response.read()
        digest = hashlib.sha256(html).hexdigest()
        assert digest == export["sha256"]
        assert b"<svg" in html and b"<table" in html and b"<script" not in html
        path = output / "html" / f"{analysis['method_id']}.html"
        path.write_bytes(html)
        analysis["generic_report"] = {
            "path": str(path.resolve()),
            "sha256": digest,
            "descriptor": export,
        }
        analysis["source_result_artifact_sha256"] = export["source_result_sha256"]
        assert (
            payload_digest(
                request(base, f"/api/v1/analysis-runs/{analysis_id}/result")["result"]
            )
            == analysis["result_payload_sha256"]
        )
    result["network_guard_checks"] = verify_network_guards(base)
    result["pilot_receipt"] = run_pilot_initial(base, output / "pilot", legacy_seed)
    result["checks"] = [
        "visible paste and parsing confirmation",
        "visible PCA/PLS/GPR execution",
        "saved PLS and GPR direct predictions",
        "KO/EN managed HTML creation/download",
        "exact managed source inspection",
        "API Two Variances",
        "generic HTML API export",
        "built-UI readiness",
        "interface-IP same-origin mutation",
        "Host/Origin rejection",
        "pilot CSV and long-group visible forms",
        "pilot small-scale GP prediction and managed reports",
        "pilot visible BF/F Two Variances forms with preflight",
    ]
    result["offline_html_verified"] = False
    return result


def require_server_stopped(base: str) -> None:
    try:
        with HTTP.open(base + "/api/v1/runtime-info", timeout=3):
            pass
    except urllib.error.HTTPError as error:
        raise AssertionError(
            "The original application server is still responding"
        ) from error
    except urllib.error.URLError:
        return
    raise AssertionError(
        "The original application server must be stopped for offline verification"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--legacy-seed-receipt", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--resume-evidence", type=Path)
    modes.add_argument("--offline-reports", type=Path)
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error("Run validation without Python optimization")
    if not args.offline_reports and not args.url:
        parser.error("--url is required for initial and resume journeys")
    if (
        not args.offline_reports
        and not args.resume_evidence
        and args.legacy_seed_receipt is None
    ):
        parser.error(
            "--legacy-seed-receipt is required for the initial archive journey"
        )
    args.output.mkdir(parents=True, exist_ok=True)
    if args.offline_reports:
        from linux_release_journey import run_offline

        evidence = json.loads(args.offline_reports.read_text(encoding="utf-8"))
        assert evidence["schema_version"] == 2 and evidence["status"] == "succeeded"
        # The orchestrator must stop the actual server, not just disable browser networking.
        require_server_stopped(evidence["access_origin"])
        result = run_offline(args.output, evidence)
        result["original_server_unreachable"] = True
        name = "offline-smoke.json"
    elif args.resume_evidence:
        from linux_release_journey import run_resume

        evidence = json.loads(args.resume_evidence.read_text(encoding="utf-8"))
        assert evidence["schema_version"] == 2 and evidence["status"] == "succeeded"
        result = run_resume(args.url, args.output, evidence, request)
        name = "resume-smoke.json"
    else:
        try:
            legacy_seed = json.loads(
                args.legacy_seed_receipt.read_text(encoding="utf-8")
            )
            result = verify_application(args.url, args.output, legacy_seed)
        except Exception:
            journal = args.output / "journey-evidence.json"
            if journal.exists():
                partial = json.loads(journal.read_text(encoding="utf-8"))
                partial["status"] = "failed"
                journal.write_text(
                    json.dumps(partial, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
            raise
        name = "application-smoke.json"
    (args.output / name).write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
