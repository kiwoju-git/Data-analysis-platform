# Bayesian P0 Release Checklist

Last updated: 2026-07-19

## Scope

이 checklist가 완료로 평가하는 범위는 **bounded continuous,
single-objective, sequential Bayesian Optimization P0**다. 앱이 실제 목적함수를
자동 실행하지 않으며, 추천은 확인 실험 후보이지 실제 관측값이나 전역 최적해 보장이
아니다. 모든 Bayesian Optimization 변형이 완료됐다는 의미로 사용하지 않는다.

상태는 `complete`, `complete with known limitation`,
`release evidence pending`, `out of scope` 중 하나만 사용한다.

## Audit

| Capability | Status | Implementation | Validation / limitation |
| --- | --- | --- | --- |
| available dedicated method | complete | `backend/app/analyses/registry.py`, `frontend/src/DoeAnalysisPanels.ts` | catalog/API contract tests; generic analysis-run은 dedicated error를 반환 |
| Study create/list/get | complete | `backend/app/api/v1/bayesian_studies.py`, `backend/app/services/bayesian_studies.py` | `backend/tests/unit/test_bayesian_studies_api.py` |
| factor/objective/linear-constraint validation | complete | `backend/app/api/v1/schemas/bayesian.py`, `backend/app/services/bayesian_studies.py` | request boundary와 constraint tests |
| deterministic initial design | complete | `backend/app/services/bayesian_studies.py` | fixed-seed coordinates/SHA restore tests |
| trial observation | complete | `complete_bayesian_trial` service와 typed PUT route | immutable history/optimistic-lock tests |
| trial abandon | complete | `abandon_bayesian_trial` service | stranded-study 방지와 recommendation-origin abandon tests |
| immutable history | complete | SQLite schema 12~14 history revision/head records | 200 observations/201 revisions, tamper, stale-lock tests |
| GP / Matérn 5/2 | complete | `backend/app/statistics/bayesian_optimization.py` | independent covariance/posterior and Branin reference tests |
| Expected Improvement | complete | `backend/app/statistics/bayesian_optimization.py` | analytic hand formula, minimize/maximize tests |
| candidate/duplicate/constraint handling | complete | bounded seeded candidates, SLSQP refinement, all-trial exclusion | feasibility, abandoned-coordinate, duplicate/no-candidate tests; no random fallback |
| recommendation persistence | complete | recommendation config/result/model/provenance records | `backend/tests/unit/test_bayesian_recommendations_api.py` consistency/tamper tests |
| latest recommendation | complete | `/recommendations/latest` | 21+ recommendation paging/latest tests |
| current trial reconciliation | complete | immutable snapshot plus transient `current_trial` | pending/completed/abandoned UI and API tests |
| budget/time limit | complete | typed request budgets and public `bayesian_optimization_budget_exhausted` | fit/acquisition/worker timeout tests; time budget is not mislabeled as fit failure |
| Study close | complete | immutable lifecycle event schema 1 | close precondition/idempotency/conflict/restore tests |
| successor lineage | complete with known limitation | immutable `predecessor_study_id`, explicit seed warning | observations/history/recommendations are not copied; same seed remains user-selectable |
| deletion preflight/delete | complete | closed metadata-graph preflight and transactional delete | active/predecessor blocker, exact confirmation, tamper/redaction tests |
| catalog pagination | complete with known limitation | `frontend/src/features/bayesian/hooks/useBayesianStudyCatalogState.ts` | page size 20, 51st Study and stale-page tests; full graph validation cost is measured separately |
| exact-ID deep-link restore | complete | `study_id`/`recommendation_id` query plus existing GET routes | off-page reload, mismatch, not-found, stale-response tests |
| transition action isolation | complete | selection-ID render gate and independent lifecycle/recommendation/retention guards | `frontend/src/asyncHookState.test.ts` A-to-B transition regression tests |
| checksum/dependency restore | complete | `_load_validated_study` and recommendation consistency validator | stored graph/version/checksum/tamper tests |
| tutorial smoke | complete | `scripts/tutorial_smoke.ps1` | 18 API-derived result sections; synthetic inputs only |
| browser E2E | complete | `tests/e2e/critical_path.py` | create, observe, recommend, reload, complete/abandon, budget, close/delete, lazy route coverage |
| Windows 11 / Node 22 clean release evidence | release evidence pending | repository workflow targets the required versions | current local evidence is Windows 10/Python 3.10.11/Node 24.17.0 |
| latest hosted GitHub Actions run/artifact verification | release evidence pending | `.github/workflows/ci.yml` | current host has no authenticated `gh` CLI evidence |
| multiobjective, batch, categorical/integer factors, nonlinear constraints | out of scope | none | requires separate method/contract review |
| automatic objective execution or guaranteed global optimum | out of scope | intentionally absent | would violate current local manual-observation safety contract |

The application runtime handshake also requires the current backend to report
`bayesian_optimization=true`. Until API contract 2 and that capability pass,
the frontend blocks the workspace instead of rendering an older catalog that
labels Bayesian P0 as planned. This gate changes no Bayesian calculation,
schema, budget, or method version.

## Release Interpretation

P0 functional closure does not waive the clean Windows 11/Python 3.10/Node 22 release gate.
Catalog scaling observations are recorded in
[Bayesian catalog performance](bayesian_catalog_performance.md), while numerical GP/EI worker
performance remains in [the Bayesian contract](bayesian_optimization_contract.md).
