# DataLab Studio tutorial data pack

This directory contains only deterministic synthetic records. It does not contain real people,
companies, products, equipment identifiers, filenames, or production measurements.

## Files

| File | Shape | Purpose |
| --- | ---: | --- |
| `studio_process_training.csv` | 240 x 15 | Upload, EDA, inference, regression, and quality |
| `studio_process_paste_60.tsv` | 60 x 15 | Exact-text spreadsheet paste staging |
| `studio_process_prediction.csv` | 48 x 8 | Compatible Predict target and Phase II P chart target |
| `studio_process_prediction_invalid.csv` | 3 x 7 | Predict preflight failure examples only |
| `studio_gage_rr.csv` | 60 x 4 | Balanced crossed 10-part, 3-operator, 2-replicate Gage R&R |
| `studio_factorial_responses.csv` | 16 x 6 | Replicated 3-factor full-factorial responses |
| `studio_rsm_responses.csv` | 13 x 4 | Two-factor face-centered CCD responses |
| `studio_bayesian_observations.csv` | 5 x 4 | Manual Bayesian initial observations |
| `tutorial_data_manifest.json` | n/a | SHA-256, shape, encoding, formula, and intended-use manifest |
| `tutorial_expected_results.json` | 18 sections | Normalized results captured from real Studio APIs |

`studio_process_prediction_invalid.csv` intentionally omits `feed_rate_kg_h`, contains unseen
`material_grade=D`, a nonnumeric pressure, and a missing catalyst. It is not a success-path file.

## Reproduce

From the repository root:

```powershell
.\.venv\Scripts\python.exe .\examples\tutorial\generate_studio_tutorial_data.py
powershell -ExecutionPolicy Bypass -File .\scripts\tutorial_smoke.ps1
```

The generator uses seed `20260718`, UTF-8, LF line endings, explicit float rounding, and atomic
replacement. Running it twice produces identical data-file SHA-256 values. It does not compute
statistics.

`scripts/tutorial_smoke.py` creates a temporary local workspace, calls the actual FastAPI routes,
and compares 18 normalized result sections with `tutorial_expected_results.json`. Dynamic IDs,
timestamps, and workspace paths are excluded. Updating expected values is an explicit operation:

```powershell
.\.venv\Scripts\python.exe .\scripts\tutorial_smoke.py --write-expected
```

Run that command only after an intentional method/data contract change and review the numeric diff.
The Korean user walkthrough is [studio_end_to_end_tutorial_ko.md](../../docs/studio_end_to_end_tutorial_ko.md).
