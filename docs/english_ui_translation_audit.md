# English UI Translation Audit

Review date: 2026-09-12. Scope: the complete generated frontend catalog and
all localized TS/TSX source mappings, with manual review concentrated on
short ambiguous tokens, DOE/statistical terminology and suspicious English.
This is not a claim that every long help paragraph was independently copy-edited.

## Root Cause and Prevention

The interaction selector assembled a number and the separately translated
Korean suffix `차`. Without context its generated English value was `tea`.
Both Factorial panels now use complete named semantic keys:
`doe.interactionOrder.mainEffectsOnly`, `upToTwoWay`, `upToThreeWay`.
No CSS hiding or runtime string substitution is used. Legacy `차` translates
to `Order`, but is no longer used by these selectors.

`scripts/check_frontend_localization.mjs` checks the entire catalog for missing
mappings, unresolved Korean English values and placeholder parity. Additional
source/key-specific guards reject tea/ordinal fragments, effectiveness for
factorial effects, header/heather, LCL cutting, heat for columns, and black for
statistical tests. Ordinary English references to tea are not globally banned.

## Reviewed Corrections

| Key | Korean context | Previous English | Revised English |
|---|---|---|---|
| `ui.6ccd3f82b0317e51` | 차 | tea | Order |
| `ui.365492fbe180b06d` | 절대 효과 순위 | Absolute effectiveness ranking | Absolute effect ranking |
| `ui.604d5b8ed3fda407` | 절대 효과 순위 차트 | Absolute effectiveness ranking chart | Absolute effect ranking chart |
| `ui.6c65ef1ec2a25e01` | 헤더처럼 | like heather | Looks like a header |
| `ui.6062a6f43d8149f1` | LCL 절단 | LCL cutting | LCL truncated |
| `ui.f14d9681be156677` | 중단 | interruption | Stop |
| `ui.c4958f97f3f6ea09` | 중단됨 | interrupted | Stopped |
| `ui.eabd32d641838749` | / 열 | / heat | / columns |
| `ui.6f4112362e973dd6` | 열 | heat | columns |
| `ui.1cdf04517a34af57` | 열 · | Heat · |  columns · |
| `ui.8e807b5d10541700` | 검정 | black | Test |
| `ui.c290e6b068266a97` | 경계 | border | Boundary |
| `ui.706d4221d20530ef` | 고유값 | Eigenvalues | Distinct values |
| `ui.5b35bfb2417cd633` | 관련성 | relevance | Association |
| `ui.b8020e963ddfc1f1` | 구간 | section | Interval |
| `ui.0d655420706562b5` | 기각 | dismissed | Reject |
| `ui.364d448a22b1512f` | 대 | stand | versus |
| `ui.3182dd7d3d31e49a` | 목표 | goal | Target |
| `ui.58902391b9377fdd` | 반복 | repeat | Replicates |
| `ui.2c6d8d8368b146d0` | 분산 | dispersion | Variance |
| `ui.76eac7b6124ae791` | 비규격 | non-standard | Out of specification |
| `ui.d477cbbc779aedf6` | 상수열 | constant sequence | Constant column |
| `ui.acb3ecd29a0351cf` | 센터점 | Center branch | Center points |
| `ui.91f7f1a47f7bae93` | 양측 | both sides | Two-sided |
| `ui.d536e6255a4151ea` | 와 | Wow | and |
| `ui.982b261d5e29fe7c` | 자 / | Now / |  characters / |
| `ui.01dfd369cfa718dd` | 작업 | work | Actions |
| `ui.8b4519476f7d39b6` | 진동 | vibration | Oscillation |
| `ui.77f3b977ffedc949` | 측정자 | measurer | Operator |
| `ui.f396c26fce51c9e7` | 평균 | average | Mean |
| `ui.487749b84d4d7f4f` | 표시 | sign | Displayed |
| `ui.2b8403841b471743` | 학습 | learning | Training |
| `ui.bdb17d1f5327c0d9` | 항 | port | Term |
| `ui.72d2bae2a744d54f` | 현재 | present | Current |
| `ui.fb77d92a3c6bcd69` | 판정 | Judgment | Decision |
| `ui.5cefce2682ec6c4c` | 계수 | coefficient | Coefficient |
| `ui.a6f444699fd85260` | 요인 | factor | Factor |
| `ui.7a73f940083f5fda` | 수준 | level | Level |
| `ui.791889c5b68580a4` | 반응 | response | Response |
| `ui.19eb72507e18aaaa` | 잔차 | residual | Residual |

Seven additional contextual phrases were corrected: `ui.18bb...` quick test
selection guide, `ui.1e139...` columns/max, `ui.386bb...` statistical test switching,
`ui.545ddd...` columns/version, `ui.6077...` overall test, `ui.609bbb...` stationary
point, and `ui.cf066...` other tests. Full exact keys and values are in the Git diff.

The legacy dataset-profile label `고유값` means distinct values in that location;
PCA uses its separate eigenvalue semantic key and was not renamed.

## Deliberate Invariants

OLS, ANOVA, VIF, PRESS, DF, SS, CI, PI, SHA-256 and mathematical symbols may
remain identical in both locales. User factor/column/level/model names are
never translated. Machine-readable IDs and warning codes remain stable.
New selection, prediction, paste, residual and report controls use named
`doe.*` keys with complete Korean/English meanings.

Remaining review scope: stylistic editing of long historical help paragraphs
and user-supplied mixed-language names, not known ordinal/DOE translation bugs.
Final structural counts, browser checks and commands are recorded in
`factorial_model_workflow_validation.md` and `ci_status.md` after execution.
