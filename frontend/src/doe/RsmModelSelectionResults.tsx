import type { DoeResponseSurfaceAnalysisResult } from "../api/types/doe";
import { t } from "../i18n/translate";
import { formatMeasurement } from "../statisticalNumberFormat";
import { compactTermLabel } from "./compactTermLabel";
import { DoeSelectionStepMatrix } from "./DoeSelectionStepMatrix";
import "./doeAnalysisPresentation.css";

export function RsmModelSelectionResults({ result }: { result: DoeResponseSurfaceAnalysisResult }) {
  const selection = result.model_selection;
  if (!selection) return null;
  const terms = new Map(selection.term_catalog?.map((term) => [term.term_id, term]));
  return <section className="result-section">
    <h3>{t("doe.selection.title")}</h3>
    <dl className="doe-selection-description">
      <div><dt>{t("doe.rsm.preset")}</dt><dd>{result.term_preset ? t(`doe.rsm.preset.${result.term_preset}`) : "-"}</dd></div>
      <div><dt>{t("doe.selection.title")}</dt><dd>{t(selection.method === "none" ? "doe.selection.none" : "doe.selection.backward")}</dd></div>
      <div className="doe-selection-description-wide"><dt>{t("doe.selection.stop")}</dt>
        <dd>{t(`doe.selection.stop.${selection.stop_reason === "not_requested" ? "selection_not_requested" : selection.stop_reason}` as Parameters<typeof t>[0])}</dd></div>
    </dl>
    <dl className="doe-term-summary">{([
      ["doe.terms.candidates", selection.candidate_term_ids ?? []],
      ["doe.terms.userExcluded", selection.initially_excluded_term_ids ?? []],
      ["doe.terms.forced", selection.fixed_term_ids],
      ["doe.selection.removed", selection.removed_term_ids],
      ["doe.selection.final", selection.final_term_ids],
    ] as const).map(([key, ids]) => <div key={key}><dt>{t(key)}</dt><dd>{ids.length ? <details>
      <summary>{ids.map((id) => {
        const term = terms.get(id);
        return term ? compactTermLabel(term, "coded", result.factor_names) ?? term.label : id;
      }).join(", ")}</summary>
      <ul>{ids.map((id) => <li key={id}>{terms.get(id)?.label ?? id}</li>)}</ul>
    </details> : "-"}</dd></div>)}</dl>
    <dl className="result-definition-grid">
      <div><dt>PRESS</dt><dd>{formatMeasurement(result.press)}</dd></div>
      <div><dt>Predicted R²</dt><dd>{formatMeasurement(result.predicted_r_squared)}</dd></div>
      <div><dt>Residual DF</dt><dd>{result.sample.df_residual}</dd></div>
    </dl>
    {selection.method !== "none" ? <p className="notice-box notice-warning">{t("doe.selection.exploratory")}</p> : null}
    {selection.display_step_details && selection.steps.length ? <DoeSelectionStepMatrix selection={selection} multiDf={false} /> : null}
  </section>;
}
