import type { AutoStrategyEvidence } from "../../api/types/boAugmentation";
import { useI18n } from "../../i18n/LocaleProvider";
import { augmentationPolicyLabel } from "../../i18n/boAugmentation";
import { autoEvidenceMessages } from "../../i18n/boAutoEvidence";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";

export function BayesianAutoEvidence({ evidence, responses }: {
  evidence: AutoStrategyEvidence; responses: { response_id: string; name: string }[];
}) {
  const { locale } = useI18n(), text = autoEvidenceMessages(locale);
  const diagnostic = evidence.diagnostic, decision = evidence.decision;
  return <section className="bo-auto-evidence" aria-label={text.title}>
    <h4>{text.title}</h4>
    <p>{augmentationPolicyLabel(decision.recommended_policy!, locale)}</p>
    <dl className="bo-planning-source">
      <div><dt>{text.threshold}</dt><dd>{exact(decision.threshold)}</dd></div>
      <div><dt>{text.routing}</dt><dd>{diagnostic.model_id}</dd></div>
    </dl>
    <div className="table-wrap"><table className="result-table"><thead><tr><th>{text.response}</th><th>LOO R²</th><th>RMSE</th><th>N</th></tr></thead>
      <tbody>{diagnostic.calculation.responses.map(row => <tr key={row.response_id}>
        <th scope="row">{responses.find(response => response.response_id === row.response_id)?.name ?? row.response_id}</th>
        <td>{exact(row.r_squared)}</td><td>{exact(row.rmse)}</td><td>{row.n_scored}</td>
      </tr>)}</tbody></table></div>
    <p>{text.limitation}</p>
    <details><summary>{text.source}</summary><dl className="bo-planning-source">
      <div><dt>model_sha256</dt><dd>{diagnostic.model_sha256}</dd></div>
      <div><dt>history_sha256</dt><dd>{diagnostic.history_sha256}</dd></div>
      <div><dt>decision_sha256</dt><dd>{evidence.decision_sha256}</dd></div>
      <div><dt>{text.policy}</dt><dd>{decision.policy}</dd></div>
    </dl></details>
  </section>;
}
