# BO Remaining Functional Work: Design For Review

Status: proposed domain choices; not an implementation-completion report.
Baseline: `a9abb4bac0f6104b8fd6ac270edcc80a5bc32050`, API43 / metadata34.

## Intent And Scope

Finish the remaining BO user journeys without copying an unknown JMP algorithm.
The user will conduct exact native JMP output comparisons. Preserve the current
UI, existing scalar and desirability studies, numeric/category models, immutable
history, saved batch reports, and the canonical GPR regression menu.

Use at most two auxiliary agents and one heavy local test/build/fit at a time.
Keep private JMP training material and user workspaces out of Git and diagnostics.
No Linux Release publication in this work. Existing native/archive checks remain.

## Approaches

1. Extend the existing source-owned BO planning/domain/report modules. This keeps
   user workflows and safe persisted models, but requires explicit versioned
   contracts for new domains and views. Recommended under the user's existing
   instruction to preserve UI and features.
2. Build a separate mixture/Profiler BO workspace. This would duplicate the
   existing lifecycle, validation and persistence and conflict with that
   instruction; it is not proposed.
3. Treat a mixture as two independent linear inequalities. This fails to define
   closure-preserving sampling, pseudocomponent encoding and conditional curves;
   it is not a correct substitute.

The first approach is the only proposed architecture. The size of the mixture
domain (one versus multiple groups) is pending the user's asynchronous answer.
The defaults below are engineering proposals, not claimed prior user approval.

## Deliverable 1: Complete Profiler Matrix

- Reuse `BayesianProfileGrid`, `InteractiveScatterChart`, saved-model evaluation
  endpoints and their numeric/mixed source validation. No GP refit on display,
  hold changes, locale, resizing, hover or quantity selection.
- Capture one complete model ID/hash, history identity, hold vector and view
  revision before requesting every factor's profile. Numeric curves use the
  existing executable coordinate generator. Category curves enumerate full
  declared levels and remain disconnected points.
- Evaluate sequential bounded chunks (existing maximum 100 points/request),
  never parallel model workers. A whole matrix has a finite time/point budget,
  displayed explicitly; do not silently skip levels/factors on budget failure.
- Commit the displayed matrix only when all requested axes validate against the
  captured source. Editing any hold/model/source invalidates success, error and
  finally application. No partially completed matrix is labeled complete.
- Response rows and factor columns use shared per-response Y ranges. Page factor
  columns when necessary instead of shrinking text. Every factor remains
  reachable, and applied holds/units/model hash are visible separately from draft.
- Keep mean, latent SD, new-observation predictive SD, and expected composite
  desirability distinct. User response names are never reserved selectors.
- Show constraint-violating predictions with non-color cues and exact point
  details; they are not eligible experiment candidates. Preserve predictions.

## Deliverable 2: Saved Views And Reports

- Introduce an immutable, versioned BO view owned by a saved planning model and
  its exact study/history. View kinds: profiler matrix and conditional LOO
  diagnostic. Existing batch/Auto-evidence report contracts stay unchanged.
- Server-generated numeric payload contains applied request, source hashes,
  prediction/diagnostic values, coverage, units, warnings and resource counts.
  Never accept client HTML, executable code or unchecked client predictions.
- Explicit save uses a request ID and exact view/model/source digests. Repeated
  identical saves are idempotent; reusing an ID with another payload is 409.
  Do not refit on save. If a server-side evaluated receipt has expired, require
  a new evaluation and visible review rather than substituting a different view.
- Add a bounded BO-owned view table if no existing artifact owner can represent
  it correctly. Do not masquerade BO views as `analysis_runs` or DOE assets.
  An additive migration is justified only for this actual SQL change.
- Connect a new typed attachment to `BayesianHistoryReportSource` through the
  existing report service, catalog, retention, deletion and offline backup paths.
  Export reads the stored view only; no evaluation, fit, CV or raw-data load.
- Preserve older document bytes and hashes. Restored views are historical views
  when the current study history differs, not permission to confirm stale trials.
- Historical models may generate and save diagnostic views. Persist predictions,
  fixed design-constraint status and the exact model/history only; omit live
  novelty, pending-trial and confirmation eligibility from this view contract.
  Those are evaluated afresh by the existing candidate/confirmation workflow.
  This is an engineering choice: a diagnostic view is not an eligibility receipt.

## Deliverable 3: Legacy Augmentation Renewal

Unconfirmed q1/ordered recommendations are memory-only reviews (20-minute TTL),
so they do not travel in workspace backups. Restart/expiry means a new review.
Persisted unconfirmed numeric augmentation selections do travel.

Recommended resolution: explicit renewed review, not a broader trust exception.

- Keep all historical GET/report bytes and stored EI values intact.
- A persisted legacy EI selection receives a stable renewal-required explanation
  before first confirmation. Already-confirmed selection replay stays supported.
- Explicit renewal captures the old stored request, exact fitted model, candidate
  revision and history, but uses a new request ID and current numerical policy.
  Do not take mutable UI defaults, refit, import newer observations or auto-confirm.
- Recheck source, active state, pending lifecycle and budget. Changed source is
  an error, not permission to silently upgrade the old selection.
- Display the new selection and changed rows/scores for review. The old record
  remains accessible. Durable lineage belongs in a new sidecar/new schema, never
  fields injected into the old hash payload.
- Concurrent identical confirmations may return the exact committed batch only
  after owner and both expected selection hashes are revalidated.
- New worker/current-policy validation remains strict. No caller-supplied
  `skip_recompute`, fake provenance or arbitrary receipt can authorize a batch.

## Deliverable 4: First-Class Mixture Domain

Proposed initial scope: one continuous mixture group, 2-8 components, optionally
with numeric/discrete/nominal/ordinal process factors; total original factors
still <=10. Discrete mixture components and multiple independent mixture groups
are explicit unsupported configurations, not rounded or coerced inputs.

The initial mixture workflow uses the existing persistent planning contract:
1-4 responses with explicit desirability goals. It does not silently convert a
legacy scalar EI/ETI study or promise scalar EI/ETI mixture support. Such requests
are explicitly rejected outside this contract. This follows the existing
persistent numeric/mixed study boundary, rather than inventing another workflow.

### Coordinate Contract

- User declares finite positive total `S`, common component amount unit and each
  component's lower/upper bounds. Require nonnegative bounds, feasible closure,
  and positive-dimensional region. A collapsed single composition is not BO.
- Raw input/export/trial coordinates remain actual amounts. Require
  `sum(x_i)=S` using a documented floating-point comparison; no silent rescaling
  of imported rows, clipping to bounds, or inserting an omitted component.
- Lower pseudocomponent coding: `z_i=(x_i-L_i)/(S-sum(L))`.
- Upper coding: `z_i=(U_i-x_i)/(sum(U)-S)`.
- Expose explicit lower/upper coding; a documented automatic choice compares
  the two positive denominators and records the effective mode. Do not infer
  component bounds from current sample extrema.
- Persist component IDs/order, total, bounds, coding mode and affine transform
  in the new study/model contract. Numeric process scaling and category equality
  remain separate. A restored model uses its stored transform, not new defaults.
- Keep old study schemas 5/6/7 and models unchanged; a new versioned study/domain
  dispatch opts into closure. Do not add default mixture fields to old checksums.
- Novelty, minimum batch distance and maximin use a separately versioned actual
  design-domain metric, independent of lower/upper pseudocomponent model coding.
  Normalize each numeric coordinate by its declared actual bound width; a fixed
  component contributes zero. Retain the existing nominal equality and ordinal
  level-distance conventions for process factors. Persist this metric policy and
  report distances in normalized design units. Changing model coding cannot
  silently change the meaning of an experiment-spacing setting.

### Feasible Candidates And Predictions

- Use a bounded, seeded sampler that operates inside the closure polytope,
  incorporating component bounds and actual-unit linear process constraints.
  Establish feasibility before sampling. Record seed, algorithm, attempts and
  stop reason; no claim of exact uniform coverage from a finite sampler.
- Explicit imported/candidate rows must satisfy closure and domain checks before
  model evaluation or confirmation. Reuse current novelty, pending, budget,
  exact source and atomic batch guards.
- No rounded SLSQP objective. Initial mixture support uses the existing bounded
  candidate planning workflow with explicitly feasible candidates; advertise
  only the acquisition/augmentation policies whose domain assumptions pass.
- GP kernel uses stored pseudocomponent coordinates plus existing process
  factors. Do not reuse an independent per-component low/high normalization
  that erases the declared transform. No custom-object serialization or pickle.

### Mixture Profiler

Changing one component while holding all others fixed violates closure. Use an
explicit compensation policy: preserve ratios of the other components' excess
above lower bounds (or upper-bound deficits for upper coding). Compute the
feasible trace interval before evaluation, respecting every component bound and
process constraint. A zero balancing mass is unavailable with a reason, not an
invented equal split. Display that components co-vary; it is not an independent
factor effect. Original actual units remain the visible axes/details.

## Deliberate Boundaries

- Existing DS-linear maximize/minimize desirability is implemented. Exact JMP
  asymmetric/private tail behavior and private Auto switching remain unverified.
  Do not invent a formula and label it JMP. A new public nonlinear tail option
  requires a separately named policy and independent moment tests.
- No new 3D renderer, generic mixture DOE/Scheffe regression engine, multi-user
  server, new chart library, dependency family or reconstructed JMP executable.
- No claimed universal parity, automatic safety of mixtures, global optimum,
  or statistical validity of correlated response independence.

## Validation Gates

1. Deterministic failing tests first; narrow tests then relevant/full suites.
2. Matrix: every factor/response, 100-point boundaries, user Unicode labels,
   same-model/hash, stale A-B-A, failure in a later chunk, no partial state,
   constraint flags, latent/predictive distinction, KO/EN and keyboard/pin.
3. Views: save/read/restart/backup/restore/report, corrupted hashes/owner mismatch,
   save retry, source changes, retention/deletion, no refit/export recomputation.
4. Mixture: hand NIST bounds L=(.3,.4,.1), S=1; z=(1,0,0) -> x=(.5,.4,.1),
   round trip, upper coding, totals other than1, infeasible bounds, near-degenerate
   denominator, no silent input normalization, every candidate closure and
   executable process level, seed determinism, profile compensation identity.
5. Cross-path actual setting: fit prediction / profiler / candidate evaluation /
   restored model / stored report agrees within justified numerical tolerance.
6. Real built-app import -> fit -> matrix -> save -> select -> confirm -> observed
   values -> next recommendation; no pending partial write on any failure.
7. Windows3.10/Linux3.12/Python3.11/security/archive gates; no skipped/running gate
   is reported as passed. Main push only after the completed scope is verified.

## Official Sources

- [JMP mixture properties and coding](https://www.jmp.com/support/help/en/19.2/jmp/mixture.shtml)
- [NIST constrained mixtures](https://itl.nist.gov/div898/handbook/pri/section5/pri544.htm)
- [JMP mixture profiler scope](https://www.jmp.com/support/help/en/19.2/jmp/mixture-profiler.shtml)
- [JMP profiler linear constraints](https://www.jmp.com/support/help/en/19.2/jmp/linear-constraints.shtml)

These sources establish public domain semantics, not exact JMP BO kernel,
optimizer or acquisition-output parity. Native JMP comparison remains user-owned.
