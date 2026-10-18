# Numeric display contract

## Scope

F02/F03 changes display coordinates and text only. Statistical calculations,
raw result values, prediction snapshots, model manifests, requests and saved
artifacts are not rounded or rewritten. The general locale number formatter
keeps its previous defaults.

The installed ui-ux-pro-max chart guidance was consulted for visible axis labels,
accessible detail and non-color information. The existing chart system, density,
colors, locale behavior and fixed viewBox remain in place; no chart dependency is
added. `data_prd.md` is absent in this checkout.

## Numeric axes

`numericAxisPlan.ts` and `report_numeric_axis.py` use finite increasing positions
with nice 1/2/2.5/5/10 steps. A nearby origin and at most 32 candidate positions
avoid large index multiplication and absolute-coordinate significant-digit
rounding. Unrepresentable steps fall back to the two actual distinct endpoints.
Invalid/non-increasing ranges produce no generated ticks. Domain values are never
clamped into duplicate endpoint ticks.

Spacing determines significant digits, with collision escalation up to 17.
Ranges with a baseline-to-span ratio above 1,000,000 use an explicit visible base
offset in the common axis renderer; the accessible explanation preserves the
axis name and unit. Subtract the displayed base only for tick labels, never for
data coordinates, plot values, tooltips or stored output. Legacy tick-list callers
retain absolute standalone labels because they cannot display a base annotation.

Priority remains explicit tick labels, axis-specific callback, legacy callback,
adaptive default. A callback receives the original value and an optional context
(range, step, offset, suggested significant digits). Existing one-argument
callbacks remain valid and are never overridden. Generic fixed-precision numeric
callbacks were removed from GP/PLS/PCA, quality, Pearson/Gage/prediction, Graph
Builder, Q-Q, individual-value, Factorial and Two Variances chart axes so these
use the common spacing-aware default. Their details, category labels, actual
component ticks, integer row ticks and unit semantics remain separate.

Overflow-safe display projection uses half-scaled differences only when the
finite domain subtraction overflows. Padding stays within finite IEEE-754 limits.
It does not change any analysis result or recompute statistical ranges.
This pass does not expand the heatmap color-value contract to extreme
opposite-sign IEEE-754 limits. Grid color normalization and its singleton-cell
edge cases need separate validation; the finite extreme guarantees here cover
the shared numeric axis plan and scatter/static plot projection.
Nonfinite expanded grid edges continue to fail explicitly; unsupported extreme
grids must not produce successful SVG with NaN or infinite geometry.

## Prediction and tables

`statisticalNumberFormat.ts` provides seven-significant-digit measurement text,
small/large scientific notation, actual probability text, exact roundtrip text,
and paired interval formatting. Distinct finite interval endpoints increase
precision together up to 17 digits rather than displaying a false zero-width
interval. Missing/nonfinite values display a dash; actual zero is normalized and
nonzero finite measurements never become zero or negative zero. No threshold or
inequality is fabricated for p-values.

GP mean, latent SD, predictive SD and intervals use these helpers. PLS direct
prediction and the shared regression prediction table use the same measurement
policy. Locale changes render text without resubmitting prediction. Exact scalar
values remain in titles and prediction JSON snapshots; original input strings
and warnings remain untouched.

`report_table` formats finite **float** values by column, starting at its existing
10-significant-digit policy and increasing precision only when distinct values
would collide. Exact roundtrip values are preserved in title/accessibility text.
An optional numeric-column formatter receives immutable column context; custom
formatting takes precedence. Integers remain exact, booleans and user strings are
not parsed or coerced. Precision comparisons also include exact integer strings,
so an integer endpoint and an adjacent float cannot collapse; even unbounded
Python integers are never coerced to float. HTML escapes visible and detail text.
Completed GP and saved regression prediction reports explicitly group each
interval's lower/upper columns into one precision context. This also preserves
distinct endpoints in a single-row report; absent intervals remain dashes.
The static Two Variances ratio-interval graph uses the same adaptive axis plan,
including a visible base offset when needed. Static point/reference details
retain exact saved numeric values instead of fixed significant-digit labels.

## Verification

`tests/fixtures/numeric_display_cases.json` is consumed by both Vitest and pytest.
It covers narrow positive/negative ranges, large offsets, small and subnormal
values, crossing zero, constant padded ranges, extreme finite ranges and adjacent
representable values. Tests assert finite ordered unique in-domain positions,
bounded work, distinct labels, offsets, explicit category precedence, KO/EN
rendering and finite actual SVG positions. Direct GP component tests verify
small positive/negative/zero means, SDs, narrow intervals, locale rerender without
new requests, and unchanged exported snapshot values.

The existing browser-only formatter fixture adds visible narrow-range and offset
assertions without adding a production route. Browser execution evidence and
full integration gates are recorded in the pilot follow-up ledger, not inferred
from these unit tests. Existing HTML artifacts retain their original bytes; new
exports identify the updated report renderer version.
