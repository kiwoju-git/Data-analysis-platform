# Factorial Prediction, Plots and Reports Contract

Status: implementation contract, 2026-09-12. See the companion selection
contract and official-source audit before changing these policies.

## Immutable Source

Prediction/report source is one saved analysis, not the latest mutable response
or a refitted model. Validate design SHA, result SHA, config binding and response
revision relation/SHA. Historical revisions remain valid after correction.
The new result stores ordered final feature definitions, coefficients,
inverse(X'X), residual MSE/DF and coding. No executable formula, pickle or paths.
Legacy results remain readable; new capabilities require a recorded basis and
must not silently rerun legacy calculations.

## Prediction

Dedicated analysis-owned preflight/create/get APIs; no sidebar method.
1..256 rows, exact factor names, finite numeric values, known categorical labels.
Atomic policy: one invalid row blocks the entire request. Preflight never saves.
Out-of-range numeric settings are rejected. Discrete numeric settings retain
their executable grid contract. Block-specific prediction requires a known
block; default is the reference block, visibly recorded.

Two-level coding: numeric (value-midpoint)/half_range; text low/high -1/+1.
With curvature in the final selected model, allow only complete corners or actual stored center/pseudo-center
settings. Reject arbitrary mixed/interior settings. General Full treats every
level as categorical: only declared levels, no numeric interpolation.

Mean=x0'b; SE_mean=sqrt(MSE*x0'inverse(X'X)x0).
Mean CI uses t(DF,1-alpha/2)*SE_mean; PI adds one inside the covariance factor.
If residual variance/DF are unavailable, return point prediction and null
intervals with a reason. Post-selection intervals are exploratory and conditional
on the selected model. No causal or out-of-domain guarantees.

Prediction JSON is immutable, source-bound and SHA-checked. Creation validates
source identity again in the storage transaction. Deletion preflight includes
dependent predictions/reports; a stale plan must fail without partial deletion.

## Fitted Means and Cube

Main/interactions average final fitted values over the Cartesian product of
declared corner/level settings, equally weighting other factors and observed
block levels. Curvature indicator is zero for corners. Persist the bounded
cell table (at most 256 treatment combinations); derive plots from saved cells,
never refit. Data means remain separate and explicitly labelled.

Pair view supports chosen X/trace factors or a bounded all-pairs view (15 plots
per view). Every pair remains selectable individually. A final-model-only
filter is explicit; the default selected pair remains useful even after its
interaction has been removed.
Missing interactions in a selected model can yield parallel fitted lines.
General Full supports main/interaction plots but no two-level cube.

Two-level full cube displays 2 or 3 selected factors; others have explicit
low/high fixed settings. A square/cube is a bounded combination diagram, not
a fitted 3-D response surface. Fitted and observed means cannot be silently
substituted. Fractions/PB retain alias warnings and existing effect views.

## Residuals

Raw and standardized Q-Q, histogram, fits and actual run-order plots use final
residuals. Histograms aggregate all observations before display limits; Q-Q
coordinates and references are persisted. Null standardized values remain
unavailable. Keep leverage/Cook/Shapiro/Durbin-Watson and visible warnings.
Reuse keyboard-accessible SVG chart primitives and stable point identities.

## Paste and Revisions

Both Factorial panels share a strict preview-before-apply response importer.
One numeric column maps to sorted run_order; two columns explicitly map
run_order,response. CSV/TSV and optional header are supported. Reject duplicates,
missing/extra runs, blanks, nonnumeric and nonfinite cells; never pad/truncate.
Maximum 256 rows. Applying affects draft only. Saving uses one existing atomic
revision operation. An analyzed response must enter explicit correction mode
first. Never log clipboard values or include them in error text.

## HTML and Ownership

Keep the legacy on-demand design/response/latest-analysis endpoint unchanged.
New reports are analysis-ID-specific artifacts, with locale en/ko, SHA, byte
size and creation time. Render saved data only: design/revision/options,
selection trace, equation, summary, coefficient/ANOVA tables, effects, residuals,
main/interactions/cube, warnings and collapsed technical provenance.
Inline SVG, escaped user text, no scripts or external resource/CDN. Print-safe.

Metadata 20 uses a dedicated analysis-owned table for bounded HTML/JSON BLOBs
(16 MiB per artifact, 100 artifacts per source analysis), since generic analysis-run artifacts have the wrong
foreign-key owner. SHA-checked BLOB writes and cascade deletion are transactional;
no filesystem path is exposed or required. Export and prediction schemas start
at 1. List metadata only, download verified bytes, explicit delete preflight.
Catalog/detail and design cascade counts include the new owned assets.

## Compatibility and Test Gates

No design/revision schema bump or rewriting. New analysis result/config versions
are separate from unchanged design-generation meaning. Independent matrix
prediction, t intervals, center-domain cases, full-N histogram, fitted means,
escape/CSP, tamper, transaction rollback, legacy report, restore, KOR/ENG and
mobile/keyboard E2E are release gates, not optional follow-up work.
