# BO Progress And Candidate Context

Approved conversational scope: 2026-11-12. Preserve existing controls, tables,
navigation and shared interactive SVG charts. Add measured progress, observed
desirability and factor-space views; collapse explicit replicate controls; show
saved recommendation goals and strategy. Compare supplied JMP example outputs,
record evidence and limitations, and integrate through protected main. Linux
release publication is excluded.

## Approach

Reuse the existing bounded Study response and ChartFrame/InteractiveScatterChart.
No new chart dependency, training endpoint, database migration or artifact rewrite.
A separate dashboard and replacing the existing tables were rejected because the
owner requested an additive change to the existing UI. Stored model diagnostics
and profilers remain in place rather than being built again.

## Display Contract

- Progress uses completed trials only, preserving individual replicates. The X
  axis is registered trial number, not clock time or inferred batch iteration.
- Maximize/minimize show actual Y and cumulative max/min. Target goals show
  actual Y with a target reference and an optional absolute target-distance view.
- Multiresponse studies expose a response selector, never combine different units
  on an unlabeled axis. Observed composite desirability uses the immutable stored
  DS-linear/peak-one Gaussian target definitions and weighted geometric mean.
  It is a derived goal score, not a measured response or posterior expectation.
  Scalar studies lacking desirability limits do not receive invented limits.
- Factor-space plots select two distinct factors; category identity is preserved
  with categorical ticks, never interpreted as numeric distance. Completed,
  pending and abandoned trials have distinct markers. No interpolated surface or
  projection-as-slice claim. Missing Y is never zero.
- All views retain tooltip, focus, pin, Escape and responsive behavior. Locale,
  resize and view changes cause no fit/POST. Source changes clear stale pins.
- Candidate context distinguishes goal, stored exploration preference, and actual
  acquisition/augmentation reason. Balanced EI is not relabeled JMP Refine.
  Historical results never take labels from current editable draft settings.
- Replicate controls initially collapse. Existing retry/error/success notices
  remain visible; collapsing does not cancel a committed server operation.

## Validation And Limits

Synthetic pure/component/browser tests cover empty/single/constant histories,
pending/abandoned/replicates, target goals, multiresponse, nominal/ordinal axes,
stored strategy after draft changes, KO/EN and chart keyboard/resize interactions.
Independent fixed-value desirability cases guard the display projection against
the backend's established semantics. Existing BO math and schemas remain unchanged.

JMP comparison distinguishes saved Word/PPT/JRN output from a live JMP rerun.
Private source files, raw rows, models and paths are not committed or transmitted.
Publish only a non-identifying comparison summary; identify missing final-fit
settings/candidate pools and avoid claiming identical JMP Auto internals.

## Sources

- https://www.jmp.com/support/help/en/19.2/jmp/current-batch.shtml
- https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml
- https://community.jmp.com/t5/JMPer-Cable-Blog/Introducing-the-Bayesian-Optimization-platform-in-JMP-Pro/ba-p/897807

JMP documents a reason-added column and observed desirability run chart. The
additional actual-response/best-so-far and factor-space views are product choices,
not a claim to reproduce every JMP plot or numerical implementation.
