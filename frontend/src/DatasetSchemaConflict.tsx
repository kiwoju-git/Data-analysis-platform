import { Check, Pencil, RefreshCw, Undo2 } from "lucide-react";
import { useI18n } from "./i18n/LocaleProvider";
import type { SchemaConflictProps } from "./datasetSchemaDraft";
import "./datasetSchemaConflict.css";

export function DatasetSchemaConflict({
  schemaConflict = null, schemaComparison = [], schemaStaged = false,
  onSchemaConflictApply, onSchemaConflictDiscard, onSchemaConflictEdit, onSchemaConflictRetry,
}: SchemaConflictProps) {
  const { t } = useI18n();
  if (schemaConflict === null) return schemaStaged
    ? <p role="status" data-schema-staged="true">{t("dataset.schemaConflict.staged")}</p> : null;
  return <section className="schema-conflict" data-schema-conflict="true" data-conflict-state={schemaConflict.status}
    aria-label={t("dataset.schemaConflict.title")}>
    <div role="status">
      <h4>{t("dataset.schemaConflict.title")}</h4>
      <p>{t("dataset.schemaConflict.preserved")}</p>
      {schemaConflict.status === "loading" ? <p>{t("dataset.schemaConflict.loading")}</p> : null}
      {schemaConflict.status === "failed" ? <p>{t("dataset.schemaConflict.failed")} <code>{schemaConflict.errorCode}</code></p> : null}
    </div>
    {schemaConflict.status === "ready" ? <>
      <p className="cell-subtle">{t("dataset.schemaConflict.review")}</p>
      <div className="table-wrap"><table>
        <thead><tr>
          <th>{t("dataset.schemaConflict.column")}</th><th>{t("dataset.schemaConflict.field")}</th>
          <th>{t("dataset.schemaConflict.base")}</th><th>{t("dataset.schemaConflict.draft")}</th>
          <th>{t("dataset.schemaConflict.latest")}</th><th>{t("dataset.schemaConflict.change")}</th>
        </tr></thead>
        <tbody>{schemaComparison.map((item) => <tr key={`${item.columnId}:${item.field}`}>
          <td>{schemaConflict.latest?.columns.find((column) => column.column_id === item.columnId)?.original_name ?? item.columnId}</td>
          <td>{t(`dataset.schemaConflict.field.${item.field}`)}</td>
          <td>{item.base || "-"}</td><td>{item.draft || "-"}</td><td>{item.latest || "-"}</td>
          <td>{t(item.conflicting ? "dataset.schemaConflict.both" : item.localChanged ? "dataset.schemaConflict.local" : "dataset.schemaConflict.remote")}</td>
        </tr>)}</tbody>
      </table></div>
      <details><summary>{t("dataset.schemaConflict.hashes")}</summary>
        <p className="hash-text">{schemaConflict.baseHash}</p>
        <p className="hash-text">{schemaConflict.latest?.schema_hash}</p>
      </details>
    </> : null}
    <div className="button-row">
      {schemaConflict.status === "ready" ? <>
        <button type="button" className="secondary-button" data-schema-conflict-action="apply" onClick={onSchemaConflictApply}>
          <Check size={16} aria-hidden="true" />{t("dataset.schemaConflict.apply")}</button>
        <button type="button" className="secondary-button" data-schema-conflict-action="discard" onClick={onSchemaConflictDiscard}>
          <Undo2 size={16} aria-hidden="true" />{t("dataset.schemaConflict.discard")}</button>
      </> : null}
      <button type="button" className="secondary-button" data-schema-conflict-action="edit" onClick={onSchemaConflictEdit}>
        <Pencil size={16} aria-hidden="true" />{t("dataset.schemaConflict.edit")}</button>
      {schemaConflict.status === "failed" ? <button type="button" className="secondary-button" data-schema-conflict-action="retry" onClick={onSchemaConflictRetry}>
        <RefreshCw size={16} aria-hidden="true" />{t("dataset.schemaConflict.retry")}</button> : null}
    </div>
  </section>;
}
