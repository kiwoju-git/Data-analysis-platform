# Statistical Twin Presentation Preview

This prerelease profile is a deliberately scoped public demonstration of the
full Statistical Twin source at the commit recorded in `SOURCE_COMMIT.txt`.
It is not the complete product distribution.

## Included scope

- Home
- Dataset registration, schema confirmation, and profiling
- Exploratory Analysis
- Hypothesis Tests

The presentation backend publishes only the EDA and Hypothesis method catalog
and rejects other analysis execution requests with
`presentation_profile_method_unavailable`. DOE, Bayesian, regression, quality,
graph-builder, report-center, and destructive management routers are not
registered in this profile.

## Isolated runtime

- Backend: `127.0.0.1:8001`
- Frontend: `127.0.0.1:8601`
- Workspace: `%LOCALAPPDATA%\StatisticalTwinPresentation`

Run `scripts/bootstrap-presentation.ps1`, then
`scripts/dev-presentation.ps1`. The default full application remains on ports
8000/8600 and uses its existing separate workspace.
