# Graph Builder Preview Contract

Route: `POST /api/v1/visualizations/preview`

Visualization schema: `2`

Runtime capability: `graph_builder_preview`

Graph Builder is a non-persisted visualization preview workflow. It reads a
confirmed immutable dataset version, applies the same versioned analysis filter
expression used by analysis runs, and returns bounded chart payloads. It does
not create an `analysis_runs` row, row snapshot, result artifact, analysis
history item, report, or export.

| Graph type | Input | Layout |
| --- | --- | --- |
| `box_plot` | 1-12 numeric columns, or one numeric column plus group | combined boxes by variable/group or small multiples |
| `individual_value_plot` | 1-8 numeric columns, or one plus group | one combined point strip chart |
| `histogram` | 1-8 numeric columns | small multiples |
| `qq_plot` | 1-8 numeric columns | small multiples |
| `ecdf` | 1-6 numeric columns | small multiples |
| `scatter_plot` | one X and 1-6 Y numeric columns | one panel per Y |
| `run_chart` | 1-6 numeric columns and optional common order | one panel per value |
| `imr_chart` | 1-6 numeric columns, or one numeric column plus group, and optional order | an I/MR pair per value/group |

The graphical summary calculation remains the source for Tukey 1.5 IQR
boxplots, histogram bins, Q-Q points, and ECDF points. Run Chart and I-MR call
their existing statistical functions.

- Point-limit overflow is a blocking error. The service does not silently
  sample, truncate, or fabricate raw points.
- Group labels are bounded to 20 levels.
- `comparison_mode="one_value_by_group"` requires exactly one numeric value and
  one group. Group order is canonical first occurrence and missing group rows
  are excluded with an explicit count/warning.
- Grouped I-MR subsets and orders each group before calling the existing I-MR
  statistic. Centers, limits, moving ranges, and signals are independent per
  group; no moving range crosses a group boundary. A group can fail locally
  while valid groups remain in the response with a partial-result warning.
- A combined original-scale boxplot rejects conflicting explicit units.
- Missing units produce a user warning; no automatic standardization occurs.

Every response includes the dataset version, source schema hash, filter hash,
preview configuration hash, total row count, and included row count. It does
not contain a source path, filename, full raw row, SQL, or traceback.

`visualization_schema_version` is operational visualization metadata. It is not
a statistical method version or an analysis result schema version.

## Responsive Result Layout

Result layout is presentation-only and does not alter preview payloads or chart
coordinates.

- A graphical-summary card that contains one chart uses a single inner grid
  column. The full Graphical Summary keeps its two-column four-chart layout,
  and the descriptive quick view keeps its two-chart layout.
- Box Plot small multiples, Histogram, Q-Q Plot, ECDF, and Scatter Plot use up
  to two outer columns on desktop. Each chart fills the available width inside
  its card.
- A combined Box Plot and an Individual Value Plot use the full result row.
- Run Chart retains its existing responsive panel layout.
- Each I-MR variable occupies a full result row. Its I and MR charts use two
  inner columns on desktop and stack on narrow screens.

SVG `viewBox` values, scales, points, interaction coordinates, and series
colors remain unchanged. CSS supplies `width: 100%`, intrinsic aspect ratio,
and `min-width: 0` rather than scaling chart coordinates.

## Variable Selection

The variable picker remains a native checkbox group with a corporate-theme
card presentation. It shows the current selection count, maximum, available
unit metadata, and an explicit clear action. At the graph-specific maximum,
unchecked variables are disabled while selected variables remain available for
removal. The client never slices, replaces, or auto-selects values silently;
backend limits remain authoritative.

Group and order roles use labeled select controls with helper text. Box Plot
layout remains a native radio group presented as a segmented control, so
keyboard and form semantics are preserved.
