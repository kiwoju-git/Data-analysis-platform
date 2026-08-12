# Statistical Twin End-to-End Tutorial

## 1. Start the Application

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Open `http://127.0.0.1:8600`. Confirm that the top-right status says **API ready**. English is used when no language preference has been saved. Use `KOR / ENG` to switch languages without reloading the page.

## 2. Register Tutorial Data

1. Open **Datasets > Data Import**.
2. Select `examples/tutorial/studio_process_training.csv`.
3. Review the detected encoding, delimiter, header, and data start row.
4. Confirm parsing and create an immutable dataset version.

All tutorial files contain synthetic data. They are listed in `examples/tutorial/tutorial_data_manifest.json` with their checksums.

## 3. Review the Schema

Open **Datasets > Preview** and check the inferred data types, measurement levels, and analysis roles. Keep column names and data values unchanged. In particular:

- `temperature_c`, `pressure_bar`, `cycle_time_s`, `catalyst_pct`, and `feed_rate_kg_h` are numeric predictors.
- `material_grade`, `production_line`, and `supplier` are categorical predictors or grouping variables according to the analysis.
- `yield_pct` and `tensile_strength_mpa` are continuous responses.

Review missing values, unique values, identifiers, and warnings before analysis.

## 4. Run Exploratory Analysis

1. Open **Analysis > Exploratory Analysis**.
2. Choose **Descriptive Statistics** or **Graphical Summary**.
3. Select a continuous column such as `yield_pct`.
4. Review the active dataset, filters, missing-data policy, and preflight checks.
5. Run the analysis and inspect the estimates, confidence intervals, warnings, and charts.

Saved results can be reopened under **Reports** and managed under **Manage**.

## 5. Run a Hypothesis Test

Open **Analysis > Hypothesis Tests**. Select the statistical family and method that match the study design. The selected-method guidance summarizes required roles, assumptions, options, and result interpretation. Do not select a test solely from the stored data type.

For group comparisons, verify independence, group definitions, missing-data handling, alpha, and multiplicity policy before execution. Interpret effect estimates and confidence intervals together with p-values.

## 6. Fit and Use a Regression Model

1. Open **Analysis > Correlation and Regression > Fit Regression Model**.
2. Select a numeric response and valid predictors.
3. Run the preflight check and fit the model.
4. Review the regression equation, model summary, coefficients, ANOVA, residual diagnostics, and unusual observations.
5. Use the prediction section inside the fitted-model workflow to enter new predictor rows and run prediction.

Prediction values are not stored as observed data, and user-provided column names or category levels are never translated.

## 7. Create Graphs and Reports

Use **Graphs > Graph Builder** to create interactive charts from the active dataset. Use **Reports** to restore saved results and create HTML, CSV, or JSON exports. HTML reports use the interface language selected when the export is created; JSON fields and canonical CSV headers remain language-independent.

## 8. Manage Saved Assets

Open **Manage** to find datasets, analysis results, models, designs, and studies. Select a row to open its inline detail. Review deletion impact before any destructive action. Names, notes, IDs, filenames, and checksums are not translated.

## 9. Troubleshooting

- **API unavailable**: confirm that `scripts/dev.ps1` is still running and ports `8000` and `8600` are available.
- **Method unavailable**: confirm that a compatible dataset version is active and required roles are assigned.
- **Stale result or model**: reopen the source dataset or analysis and review the recorded dependency state.
- **Artifact mismatch**: do not modify workspace files manually; use the application retention and recovery workflows.

The application is local-first and binds to `127.0.0.1`. It does not require uploading the dataset to an external service.
