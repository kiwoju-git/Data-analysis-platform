# Group Identity in Stored Comparisons

## Scope and Versions

F01 separates statistical group identity from display abbreviations in these methods:

| Method | Current method version | Current result schema | Readable legacy result schemas |
| --- | --- | --- | --- |
| `eda.equal_variances` | `0.3.0` | 3 | 1, 2 |
| `hypothesis.two_sample_t` | `0.2.0` | 2 | 1 |
| `hypothesis.kruskal_wallis` | `0.2.0` | 2 | 1 |

No database migration, option change, or stored-artifact rewrite is required.
Registry-derived execution handlers and validators use the current method version;
stored-envelope readers retain the method version and bytes actually saved.

## Identity

`group_value` is the complete source group string with the existing outer `strip()`
policy only. No Unicode normalization, case folding, numeric coercion, or additional
whitespace normalization is performed. The accumulator dictionary uses this full
value. `group_index` is the zero-based first-encounter order. `group_label` remains
the presentation abbreviation (first 117 characters plus `...` if longer than 120).
Literal `...` is not evidence of truncation.

Two-sample t testing validates exactly two **full** groups, and preserves its
first-group-minus-second-group contrast for Welch/pooled and all alternatives.
Kruskal-Wallis rank accumulation and Dunn comparisons retain full identities and
explicit `group_1_index` / `group_2_index` plus full values. Equal-variance comparison
intervals are attached by validated `group_index`, never by label or returned list
position. Pair records retain labels and add left/right indexes and full values.
Malformed duplicate, missing, or mismatched interval identities fail explicitly.

ANOVA, two-proportion, and Mann-Whitney grouping were inspected: they already use
full stripped values as keys. Their calculations and contracts are unchanged.

## Presentation and Legacy

The existing compact statistical UI is preserved. Colliding abbreviations receive
a localized group number. Each affected result provides a keyboard-operable
`details[data-group-identities]` table with the full values, rendered as text and
wrapped within the result width. Rows and interval hit targets expose
`data-group-index` for stable identity. Interval accessibility text, tooltip titles,
and pinned details preserve full names. Pair associations use indexes, not labels.

HTML renderers project full values into display copies only, using existing HTML
escaping. They never fit, reread raw rows, or rewrite the saved result. Legacy
results without `group_value` show their saved labels and an explicit limitation;
lost suffixes are not reconstructed or asserted to be known.

## Verification

`test_group_identity.py` reproduces the old collision using `X` repeated 121 times,
suffixes `-A` / `-B`, and groups `C` / `D`, with values 1-5 / 11-15 / 21-25 / 31-35.
The 13 added regression cases failed before the fix; the original 14 calculation
tests passed. After the fix the combined 27 cases passed. Label-only bijections
must have exactly the same numerical results, so those assertions use exact
equality. Existing independently referenced floating-point tolerances are unchanged.

Additional tests cover Korean names, case distinction, `01` versus `1`, composed
and decomposed Unicode, literal ellipses, reversed interval order, index validation,
API save/restore, both report languages, HTML escaping, and legacy-shaped synthetic
stored envelopes whose checksum must remain unchanged after restore and export.
The latter are constructed fixtures, not a claim that a user's old artifact was
opened. Browser and final integrated results are recorded in the pilot validation
ledger; this contract does not claim that unrun checks passed.

### Recorded Collision Values

With NumPy 2.2.6 and SciPy 1.15.3, the four-group fixture gives:

| Quantity | BASE `0849aaa` | Corrected |
| --- | --- | --- |
| Group N | 10, 5, 5 | 5, 5, 5, 5 |
| Brown-Forsythe statistic | 23.97265625 | 0 |
| Brown-Forsythe p | 0.000011276113521619612 | 1 |
| Kruskal-Wallis H | 16.07142857142857 | 17.85714285714286 |
| Kruskal-Wallis df | 2 | 3 |
| Kruskal-Wallis p | 0.0003236932384041894 | 0.0004707189529993288 |

Brown-Forsythe df is not stored in this existing result contract. Its formula
`(k-1, N-k)` gives `(2,17)` before and `(3,16)` after the identity correction.
For just A/B, corrected Welch testing gives N=5/5, difference=-10, t=-10, df=8,
p=0.000008488181527628498, and 95% CI [-12.306004135204166, -7.693995864795834].
The old A/B path incorrectly rejected one merged group. The old A/B/C path
incorrectly tested N=10/5; the corrected path rejects three independent groups.

### Static Legacy and Archive Provisioning

`backend/tests/reference/fixtures/group_identity_legacy_base.json` contains actual
outputs from the three pinned BASE calculation modules, with their Git source
SHA-256, dependency versions, synthetic input, and canonical result-payload SHA-256.
The BASE modules import no current application helpers. The retained old EV/KW
outputs still have three merged groups; they must not be relabeled as corrected.
The fixed column UUIDs and decimal/text metadata make the fixture suitable for
consistent stored-source provisioning. Result-payload digest is not the enclosing
artifact-file digest.

`tests/e2e/seed_pilot_legacy.py` is a verification-only provisioner, not an application
endpoint. It refuses any nonempty workspace, uses the existing paste/confirmation,
row-snapshot and result storage lifecycle, and inserts only new records. A scoped
`unittest.mock` column-ID factory injects the fixture UUIDs before first storage;
no production implementation or existing record is patched. The result itself is
stored unchanged, without fitting. The receipt distinguishes source module,
fixture, result payload and envelope artifact hashes. Native archive validation
must still run against the installed release interpreter; local source tests do
not constitute an Ubuntu package validation.
