# Statistical Twin Presentation Preview 2026.08.1

This prerelease is a scoped presentation build based on full source commit
`f633ba401494937990d4746ccd1e1cd109a5e32f`.

## Public demonstration scope

- Home
- Dataset registration and preparation
- Exploratory Analysis
- Hypothesis Tests

The top-level presentation navigation contains only Home, Dataset, and
Analysis. The Analysis catalog contains only Exploratory Analysis and
Hypothesis Tests. This is not the complete product distribution.

## Intentionally unavailable

Categorical Analysis, Correlation and Regression, Quality Control, DOE,
Bayesian Optimization, Graph Builder, Report Center, Asset Management, and
Help are excluded from the presentation profile. The backend rejects hidden
analysis methods and does not register the dedicated DOE, Bayesian, regression,
quality, visualization, or asset-management routers.

## Runtime isolation

- Full application: backend 8000, frontend 8600
- Presentation preview: backend 8001, frontend 8601
- Presentation workspace: `%LOCALAPPDATA%\StatisticalTwinPresentation`

The full and presentation processes can run concurrently and do not share a
workspace database.

## Validation

- Presentation backend profile tests: 3 passed
- Presentation frontend profile tests: 2 passed
- Full-profile backend contract regression: 240 passed
- Full frontend Vitest: 266 passed across 34 files
- Full and presentation concurrent Playwright smoke: passed
- Full and presentation production builds: passed

The existing Vite chunk-size warning remains informational.
