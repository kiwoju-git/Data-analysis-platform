# BO V2 Focused Reliability Audit

This audit covers the new BO surrogate, sufficient-statistic compression, analytic acquisition,
conditional MC batch selection, mixed search, recommendation storage and explicit replicate path.
Fixtures are synthetic. It is not a native Linux, browser, release or JMP numerical-parity claim.

## Reproduced and Fixed

### Minimize normalization validation

`validate_calculation` compared the direction-normalized model mean against the raw response mean.
For minimization with nonzero raw mean, valid calculation output was rejected with HTTP 409
`bayesian_optimization_artifact_mismatch`. The comparison now applies the stored goal direction;
the solver, normalization convention and old artifacts are unchanged.

Real FastAPI/TestClient calls, spawned calculation worker and SQLite storage used responses
`[10, 14]` and `[10000, 14000]` for both maximize and minimize. Before the fix: two minimize failures,
two maximize passes. After the fix: all four pass through creation, saved batch restore and study
restore, with original history bytes and completed trials unchanged.

### Unrepresentable fixed measurement variance

A finite fixed measurement SD of `1e308` overflowed Python exponentiation before the explicit finite
variance check. Squaring now uses multiplication followed by the existing finite/positive guard.
The input is rejected with `bayesian_surrogate_noise_invalid`, not silently clamped. The paired
underflow fixture (`1e-308`) remains an explicit error. Before the fix: overflow failed the stable-error
test and underflow passed. The full six-module focused numerical run passed 127 tests after the fix.

### Explicit replicate replay

The server correctly returns current trial states on idempotent replay. The frontend previously
required pending state even when a repeated request had already been completed or abandoned by
another view. Two deferred-hook regressions reproduced the rejection. Replay now accepts valid
terminal states while new requests, parent/version/history identity and objective-state consistency
remain strict. No POST is automatically resent and no committed observation is rewritten.

## Version Dispatch

The current method catalog and new study definitions identify BO `0.7.0`. The study/close reader
explicitly accepts that version as well as existing versions through `0.6.0`. Legacy recommendation
request schema 1 still writes method `0.6.0`; noise-aware schema 2 writes `0.7.0`. Study schema 4 and
old definition hashes remain unchanged.

Real API tests create a synthetic legacy-0.6 study using the legacy catalog and a new-0.7 study,
then create/restore both recommendation versions and close/reopen the study under the current
catalog. Both pass, and the complete original study-version database row is unchanged.

## Reviewed Numerical Boundaries

- Latent posterior covariance uses signal-only cross covariance. Future measurement variance is
  predictive variance minus latent variance; numerical jitter is not physical future noise.
- Exact replicate compression uses raw-observation normalization, unequal counts, singleton groups,
  within-group sums of squares and the raw likelihood correction, including its noise gradient.
- EI/ETI use completed-location posterior plug-in incumbents. Target response remains original Y.
- The first batch item is analytic; later marginal acquisition uses joint latent samples, common
  random numbers, one application of xi and separately labeled base/planning uncertainty.
- Mixed search holds discrete levels fixed during continuous SLSQP, validates constraints/novelty
  at final executable coordinates and reevaluates their acquisition score.
- Replicate registration is transactionally all-or-none, preserves parent identity, rejects stale
  history/pending/closed/budget conditions, and uses payload-bound idempotency.
- Saved recommendation readers validate owner, history, request/result hashes and typed schema
  without refitting or modifying historical JSON.

The existing independent Cholesky, finite-difference, numerical integration, joint-sampling and
mixed-search fixtures were rerun in the 127-test focused numerical pass. Broader API regression,
native CI and exact archive/browser evidence must be reported separately by the integration run.

## Broader API Run

The seven-file BO API/lifecycle regression run completed with **71 passed and 2 failed** before
final test corrections. This initial failure record is retained:

- The legacy single-recommendation test required both method `0.6.0` and equality with the latest
  catalog. It now checks the newly created study against the current catalog while retaining the
  explicit `0.6.0` assertion for the schema-1 recommendation.
- The 500,000-byte pipe-drain probe hit its 20-second receive timeout. Its spawn target lived in
  the API test module and therefore imported the entire app/test stack in the child. The probe is
  now isolated in `backend/tests/unit/bo_worker_probe.py`, which imports only the standard library.
  The same payload size, receive deadline, explicit timeout case and owned-child cleanup assertions
  remain. This fixture change does not change the production worker or extend its timeout.

The explicit focused rerun passed **both corrected tests** in 30.74 seconds. Ruff check and format
check passed for all three affected test/probe files. These are not retroactively counted as passes
in the initial broad run. Native CI still supplies the full integrated result.
