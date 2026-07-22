from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np

REFERENCE_CASES = (
    {
        "case_id": "symmetric_small",
        "values": [-1.0, 0.0, 1.0],
    },
    {
        "case_id": "normal_like",
        "values": [-1.9, -1.1, -0.7, -0.2, 0.0, 0.3, 0.8, 1.2, 1.7, 2.0],
    },
    {
        "case_id": "right_skewed",
        "values": [0.05, 0.08, 0.12, 0.2, 0.33, 0.55, 0.9, 1.5, 2.8, 6.0],
    },
    {
        "case_id": "bimodal",
        "values": [-3.2, -2.9, -2.7, -2.4, -2.1, 2.0, 2.3, 2.6, 2.9, 3.3],
    },
)

OUTPUT_PATH = Path(
    "backend/tests/reference/fixtures/normality_statsmodels_reference.json"
)


def main() -> None:
    try:
        import statsmodels
        from statsmodels.stats.diagnostic import normal_ad
    except ImportError as exc:
        raise SystemExit(
            "statsmodels 0.14.6 is required only to regenerate this committed reference fixture.",
        ) from exc

    if statsmodels.__version__ != "0.14.6":
        raise SystemExit(
            f"statsmodels 0.14.6 required, found {statsmodels.__version__}"
        )

    cases = []
    for case in REFERENCE_CASES:
        values = np.asarray(case["values"], dtype=float)
        statistic, p_value = normal_ad(values)
        adjusted = float(statistic) * (
            1 + 0.75 / len(values) + 2.25 / (len(values) * len(values))
        )
        cases.append(
            {
                "case_id": case["case_id"],
                "values": list(case["values"]),
                "n": len(values),
                "anderson_statistic": float(statistic),
                "adjusted_statistic": adjusted,
                "approximate_p_value": float(p_value),
            },
        )

    payload = {
        "fixture_schema_version": 1,
        "reference": "statsmodels.stats.diagnostic.normal_ad",
        "statsmodels_version": statsmodels.__version__,
        "python_version": platform.python_version(),
        "p_value_method": "stephens_normal_unknown_mean_variance",
        "cases": cases,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
