"""Actual built UI source/create/review/confirm/restore/offline report checks."""

import argparse
import json
from pathlib import Path

from bo_desirability_review import verify_desirability_review
from bo_vector_history import verify_bo_vector_entry
from playwright.sync_api import sync_playwright


def verify_target_curve_recommendation(browser, base, output):
    output.mkdir(parents=True, exist_ok=True)
    paths = [output / name for name in ("entry", "q1", "q2-fit")]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    receipt = {
        "synthetic": True,
        "browser": browser.version,
        "ui_creation": verify_bo_vector_entry(
            browser, base, paths[0], curve_policy=True
        ),
        "q1": verify_desirability_review(browser, base, paths[1], 1, curve_policy=True),
        "q2_fit": verify_desirability_review(
            browser, base, paths[2], 2, fit_quality=True, curve_policy=True
        ),
    }
    (output / "receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            print(
                json.dumps(
                    verify_target_curve_recommendation(
                        browser, args.base_url, args.output
                    )
                )
            )
        finally:
            browser.close()
