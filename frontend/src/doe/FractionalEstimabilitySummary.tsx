import type { DoeAnalysisTerm, DoeFractionalEstimability } from "../api/types/doeModelWorkflow";
import { t } from "../i18n/translate";
import "./doeAnalysisPresentation.css";

export function FractionalEstimabilitySummary({ plan, terms = [] }: {
  plan: DoeFractionalEstimability | null | undefined;
  terms?: readonly DoeAnalysisTerm[];
}) {
  const labels = new Map(terms.map((term) => [term.term_id, term.label]));
  if (!plan) return <p className="notice-box notice-warning">{t("doe.fraction.legacy")}</p>;
  return <section className="result-section fractional-estimability">
    <h3>{t("doe.fraction.committed")}</h3>
    <dl className="result-definition-grid">
      <div><dt>{t("doe.fraction.requestedParameters")}</dt><dd>{plan.requested_parameter_count}</dd></div>
      <div><dt>{t("doe.fraction.rank")}</dt><dd>{plan.rank}</dd></div>
      <div><dt>{t("doe.fraction.residualDf")}</dt><dd>{plan.expected_residual_df}</dd></div>
    </dl>
    <p className="field-help">{t("doe.fraction.conditional")}</p>
    <details><summary>{t("doe.fraction.aliasExcluded")} ({plan.exclusions.length})</summary>
      <div className="table-wrap"><table className="result-table"><thead><tr>
        <th>{t("doe.model.term")}</th><th>{t("doe.fraction.reason")}</th><th>{t("doe.fraction.representative")}</th>
      </tr></thead><tbody>{plan.exclusions.map((item) => <tr key={item.term_id}>
        <td>{labels.get(item.term_id) ?? item.term_id}</td>
        <td>{t(`doe.fraction.reason.${item.reason}`)}</td>
        <td>{item.representative_term_id ? `${item.sign === -1 ? "-" : ""}${labels.get(item.representative_term_id) ?? item.representative_term_id}` : "-"}</td>
      </tr>)}</tbody></table></div>
    </details>
  </section>;
}
