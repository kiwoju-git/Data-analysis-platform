# CI Status

Last updated: 2026-07-04

## Workflow Configuration

- Workflow file: `.github/workflows/ci.yml`
- Triggers: `pull_request` and `push` to `main`
- Required runner in file: `windows-latest`
- Runtime setup in file: Python `3.10`, Node `22`
- Main check command in file: `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`

This satisfies the current repository-side requirement that main pushes should start the Windows CI workflow.

## Local Validation

- Full local Windows validation for the current DOE design report and statistical QA working tree passed on 2026-07-04 with `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`.
- The run passed backend ruff check, backend ruff format check, backend mypy over 75 source files, backend pytest with 377 tests, frontend lint, frontend typecheck, frontend Vitest with 45 tests, and frontend production build.
- The previous documentation mismatch between 267/277/301/311/320/329/338/348/357/361/363/375 backend tests is resolved; the latest recorded backend pytest count is 377.

## Remote GitHub Actions Verification

- Public browser/API access to `https://github.com/kiwoju-git/Data-analysis-platform/actions` returned no inspectable workflow run from this environment, consistent with a private repository or unauthenticated access boundary.
- `gh`/`gh.exe` is not installed in the current WSL environment, so authenticated run listing could not be performed here.
- Branch protection and repository settings were not changed in this PR.

## Follow-up

- After pushing this PR or main update, verify the latest Actions run in GitHub UI or with an authenticated `gh run list --repo kiwoju-git/Data-analysis-platform --branch main --limit 5`.
- If Actions still does not run on main push, debug repository-level Actions settings outside this code PR.
