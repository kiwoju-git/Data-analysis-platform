# Graph Builder Preview Contract

Route: `POST /api/v1/visualizations/preview`

Visualization schema: `1`

Runtime capability: `graph_builder_preview`

Graph Builder is a non-persisted visualization preview workflow. It reads a
confirmed immutable dataset version, applies the same versioned analysis filter
expression used by analysis runs, and returns bounded chart payloads. It does
not create an `analysis_runs` row, row snapshot, result artifact, analysis
history item, report, or export.

| Graph type | Input | Layout |
| --- | --- | --- |
| `box_plot` | 1-12 numeric columns, or one numeric column plus group | common axis or small multiples |
| `individual_value_plot` | 1-8 numeric columns, or one plus group | point strips |
| `histogram` | 1-8 numeric columns | small multiples |
| `qq_plot` | 1-8 numeric columns | small multiples |
| `ecdf` | 1-6 numeric columns | small multiples |
| `scatter_plot` | one X and 1-6 Y numeric columns | one panel per Y |
| `run_chart` | 1-6 numeric columns and optional common order | one panel per value |
| `imr_chart` | 1-6 numeric columns and optional common order | an I/MR pair per value |

The graphical summary calculation remains the source for Tukey 1.5 IQR
boxplots, histogram bins, Q-Q points, and ECDF points. Run Chart and I-MR call
their existing statistical functions.

- Point-limit overflow is a blocking error. The service does not silently
  sample, truncate, or fabricate raw points.
- Group labels are bounded to 20 levels.
- A combined original-scale boxplot rejects conflicting explicit units.
- Missing units produce a user warning; no automatic standardization occurs.

Every response includes the dataset version, source schema hash, filter hash,
preview configuration hash, total row count, and included row count. It does
not contain a source path, filename, full raw row, SQL, or traceback.

`visualization_schema_version` is operational visualization metadata. It is not
a statistical method version or an analysis result schema version.
