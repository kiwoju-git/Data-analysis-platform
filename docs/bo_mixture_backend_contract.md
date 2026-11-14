# Mixture BO Backend Contract

Mixture BO is an explicit study-schema 8, local persistent planning workflow for
one continuous group of 2-8 components, optional executable numeric/discrete or
declared nominal/ordinal process factors, and 1-4 desirability responses. The
total original-factor limit remains 10, including fixed components. Legacy scalar
EI/ETI studies are not converted. Multiple mixture groups and discrete mixture
components are unsupported and rejected by the typed creation contract.

## Actual And Model Coordinates

Creation uses `POST /api/v1/bayesian-studies/mixture` with
`MixtureStudyCreateRequest` in `api/v1/schemas/bo_mixture.py`:

- `schema_version:8`, study `name`;
- `mixture:{total,coding,components:[{factor_id,name,low,high,unit}]}`;
- `coding` is explicitly `lower`, `upper`, or `auto`;
- `process_factors`, desirability `objective`, and actual-unit `constraints`;
- `initial_design_seed` and `initial_design_size`.

All components must be supplied in every actual point. Bounds are strict;
closure uses the stored `actual_sum_16ulp_v1` comparison. Inputs are not silently
rescaled, clipped, rounded, or completed with an inferred remainder. A fixed
component is allowed; its spacing contribution is zero.

The stored lower or upper pseudocomponent affine transform, never current
sample extrema, drives GP coordinates. Numeric-only mixtures use the existing
numeric GP. Categorical process factors use the existing mixed correlation GP.
Known JSON numeric state is stored; pickle/joblib/custom-object loading is not
used. Numeric-only mixture surrogate state 2 uses
`bo_numeric_affine_surrogate_state_v1` and requires an explicit matching source
factor-domain descriptor when loading or writing. The ordinary numeric state 1
reader remains strict about its original `[0,1]` coordinates.
Pseudocomponent kernel-domain and signal-kernel codecs2 explicitly retain
their transform-derived coordinate bounds. A representable coordinate such as
`1.0000000000000002` is preserved, not clamped to1. Ordinary numeric/mixed
codec1 and its `[0,1]` validation remain unchanged.

Spacing is separately versioned as `mixture_actual_bound_width_process_v1`:
Euclidean actual bound-width normalized numeric/component differences, nominal
equality, and declared ordinal rank differences. It does not depend on model
coding or fitted length scales.

## Planning Routes

The following routes are relative to `/api/v1/bayesian-studies/{study_id}`:

- `mixture-planning-models`: create/list; `/{model_id}` reads stored state;
  `/{model_id}/evaluate` evaluates complete actual points without refitting.
- `mixture-candidate-revisions`: create; `/{revision_id}` pages stored rows.
  Sources are explicit actual rows or bounded seeded feasible generation.
- `mixture-selections`: create; `/{selection_id}` reads an immutable review;
  `/{selection_id}/confirm` requires both exact expected selection digests.
- `mixture-planning-batches/{batch_id}` reads the committed historical batch.

Source identities bind definition, study version, history revision/hash and
trial count; model/candidate/selection digests are also bound. Confirmation
requires a current active source, no pending trials, remaining trial budget,
and numerical revalidation. All pending batch trials are committed atomically.
Exact confirmed replay and historical GETs do not fit or evaluate a worker.
Ordinary trial observations, history, replication, closure, initial CSV,
retention, explicit deletion and offline workspace backup use the shared owner.

Supported selection policies are `manual_mixture_base_posterior_v1` and
`greedy_mixture_maximin_v1`. Base-posterior desirability beta EI is not advertised
as a joint/q-batch improvement score. Unverified mixture MaxPro or legacy scalar
acquisition policies are not accepted by this contract.

Snapshot3 uses `source_locked_mixture_bo_planning_model_v1`; the existing SQL
model envelope remains2. Candidate revisions are4, selections6, batch
config/result/model13 and batch items6, under method version0.17.0. Metadata37
extends actual SQL CHECK contracts without rewriting older document bytes.

## Sampling And Profiles

`bounded_seeded_mixture_polytope_v1` establishes a feasible actual point with
bounded discrete assignment enumeration and linear programming, then uses
seeded bounded conditional component allocation and constraint rejection.
Executable process levels are generated directly. Seed, algorithm, attempt
count, attempt limit, stop reason and `exact_uniform:false` are recorded.
Proven infeasibility, feasibility budget/numerical failure, and sampling budget
exhaustion have distinct machine-readable reasons. No exact uniformity or
global-optimizer claim is made.

Component profiles preserve the other components' lower-bound excess ratios or
upper-bound deficit ratios. Every component co-varies along the stored trace;
the feasible interval also respects process constraints. Zero balancing mass
returns an explicit unavailable reason. Process axes retain the mixture setting;
category levels remain separate points and discrete axes stay executable.
Untrimmed component paths retain the pure-domain helper's exact generated
points. Constraint intersections and trimmed interpolation use Decimal precision
800 and preserve validated endpoints; actual input bounds are not relaxed.

## Measured Dataset Import

The existing `import-preflight` and `from-dataset` endpoints accept explicit
mixture request schema2 from `bo_mixture_dataset_import.py`. The top-level
mixture group is required; component factor mappings use
`domain_kind:"mixture_component"` and must match every declared component in
order. Process mappings use their existing typed contracts.

Canonical dataset rows, parser/encoding, filter snapshot, missing policy,
source hashes and bounded atomic commit are reused. Imported amounts remain
unchanged; invalid closure is an error, not normalization. Repeated initial
coordinates are retained and counted. Imported-initial receipt2 records source,
row indices, mappings, exclusions, observation hash and runtime provenance;
it does not fabricate a generated-design seed. Reads and reports validate the
stored source receipt without rereading raw data or importing newer rows.
