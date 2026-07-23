# Interactive Chart Contract

Last updated: 2026-07-21

## Scope And Invariants

DataLab Studio keeps chart interaction in a dependency-free React/SVG layer.
Interaction changes presentation only: it must not recalculate statistics,
invent points, change result schemas, or load uncapped raw rows. A chart may
render only values already present in a validated result payload. Tooltips and
selection details are never logged or persisted in browser storage.

The shared foundation is:

- `charts/InteractiveScatterChart.tsx` for axes, reference lines, points,
  annotations, accessible descriptions, tooltip, and persistent text detail;
- `charts/useChartPointInteraction.ts` for pointer/focus/keyboard selection;
- `charts/useChartItemInteraction.ts` for roving tabindex and aggregate chart
  item interaction;
- shared `InteractiveQqChart`, `InteractiveHistogramChart`, and
  `InteractiveBoxplotChart` components for EDA results;
- `charts/chartScale.ts` for finite padded domains and coordinate scaling;
- `charts/ChartTooltip.tsx` for bounded text-only tooltip content.

Each chart has one `tabIndex=0` item. Arrow keys move to adjacent items,
Home/End move to the first/last item, Enter/Space pins selection, and Escape
clears it while preserving normal Tab exit. Every interactive item exposes an `aria-label`,
an SVG `title` fallback, a non-color selected outline, and the same values in a
text detail region below the chart. Pointer hover and keyboard focus expose the
same fields. `Escape` clears selection. Touch pointer events are supported.
Required assumptions and warnings remain in the result panel, not only in a
tooltip.

## Phase 1: Regression Diagnostics

Implemented charts:

| Chart | Tooltip/detail fields | Reference and warning policy |
| --- | --- | --- |
| Observed vs Fitted | row index, observed, fitted, residual, standardized residual | identical X/Y domain, `y=x` identity line; observed is the exact persisted `fitted + residual` relationship |
| Residuals vs Fitted | row index, fitted, residual, standardized residual | residual-zero line; large standardized residuals have a visible warning ring |
| Leverage vs Cook's D | row index, leverage, Cook's D, threshold status | persisted leverage and Cook thresholds; threshold candidates have a warning ring |

Observed vs Fitted reports Multiple R derived as the non-negative square root
of persisted R-squared, adjusted R-squared, residual standard error, and
displayed/total N. If diagnostic points are capped, the UI states that fit
statistics use the full complete-case sample. There is no calibration refit and
no regression formula change.

Current diagnostic point cap remains 500. Non-finite coordinates are excluded
from rendering rather than converted to a fake coordinate. Empty point sets
show an explicit empty state.

## Phase 2: Normality And Graphical Summary

Implemented:

| Chart | Tooltip/detail fields | Bounds and redaction |
| --- | --- | --- |
| Normality and graphical Q-Q | point number, theoretical quantile, observed quantile, reference deviation, column, N basis | only bounded persisted Q-Q points; no invented row index |
| Histogram | bin number, lower/upper bound and inclusion, count, count/N | persisted aggregate bins only |
| Boxplot | lower/upper whisker, Q1, median, Q3, lower/upper fence, outlier count, IQR | aggregate elements only; the five primary values are always labeled on the axis, coincident values are grouped, and individual outlier values are unavailable and never fabricated |
| ECDF | point number, X, cumulative probability, approximate rank, N basis | only bounded persisted ECDF points |

Pointer, touch, focus, roving keys, selection outline, SVG title, and the text
detail region use the same values. Existing result point/bin caps and truncated
copy remain visible.

The descriptive-statistics table can request a one-column
`eda.graphical_summary` result for the current immutable dataset version and
filter snapshot. Its inline quick view reuses the same histogram and boxplot
components in `quick` mode; the full method uses `full` mode and additionally
shows Q-Q and ECDF. Quick results never overwrite the descriptive result and
are invalidated when the active dataset or filter draft changes.

## Later Phase 2 Backlog

- Pearson scatter: row index or safe point index, X, Y, fitted/reference value.
- Run/Individuals/Subgroup and P/NP/C/U charts: point order, statistic,
  center/LCL/UCL, signal code, frozen-limit identity where applicable.
- Gage Run Chart: part/operator/replicate-safe identifiers and measurement
  already present in the bounded result payload.

Each migration must preserve the method's existing point cap and explicitly
define whether row indices or safe design identifiers are exposed.

## Phase 3 Backlog

- DOE main and interaction effect coordinates;
- RSM contour grid coordinates and response values.

Zoom/pan, chart image artifacts, arbitrary HTML tooltips, full-dataset browser
loading, and a heavy chart dependency are outside this contract. Any future
dependency requires a separate license, bundle, offline, accessibility, and
Windows review.
