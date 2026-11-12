import type { DatasetImportedInitialDesign } from "../../api/types/boDatasetSource";
import { useI18n } from "../../i18n/LocaleProvider";
import { datasetSourceMessages } from "../../i18n/boDatasetSource";
import { validDatasetImportedInitialDesign } from "./boDatasetSource";

export function BayesianDatasetSourceSummary({ receipt }: { receipt: DatasetImportedInitialDesign }) {
  const { locale } = useI18n(), text = datasetSourceMessages(locale);
  if (!validDatasetImportedInitialDesign(receipt)) return <p role="alert" className="warning-box">{text.invalid}</p>;
  return <section aria-label={text.title}>
    <h5>{text.title}</h5>
    <dl className="bo-planning-source">
      {[[text.dataset, receipt.source.dataset_id], [text.version, receipt.source.dataset_version_id],
        [text.total, receipt.n_total], [text.filtered, receipt.n_filtered], [text.missing, receipt.n_missing],
        [text.used, receipt.n_used], [text.unique, receipt.unique_coordinate_count], [text.repeats, receipt.repeated_coordinate_count],
        [text.conflicts, receipt.conflicting_coordinate_count], [text.missingPolicy, receipt.missing_policy === "reject" ? text.reject : text.completeCase]]
        .map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
    </dl>
    {receipt.warnings.length > 0 && <ul className="warning-box">{receipt.warnings.map((warning, index) => <li key={index}><code>{warning}</code></li>)}</ul>}
    <details className="technical-details"><summary>{text.provenance}</summary>
      <dl className="bo-planning-source">
        {[['Policy', receipt.policy], ['Schema SHA-256', receipt.source.schema_hash], ['Canonical SHA-256', receipt.source.canonical_sha256],
          ['Raw SHA-256', receipt.source.raw_sha256], ['Filter SHA-256', receipt.source.filter_sha256],
          ['Preflight SHA-256', receipt.preflight_sha256], ['Observations SHA-256', receipt.observations_sha256],
          ['Request ID', receipt.request_id], [text.rows, receipt.source_row_indices.join(', ')]]
          .map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      </dl>
      {[{ label: text.x, mapping: receipt.factor_columns }, { label: text.y, mapping: receipt.response_columns }].map(({ label, mapping }) =>
        <div key={label}><h6>{label}</h6><dl className="bo-planning-source">{Object.entries(mapping).map(([id, column]) =>
          <div key={id}><dt>{id}</dt><dd>{column}</dd></div>)}</dl></div>)}
    </details>
  </section>;
}
