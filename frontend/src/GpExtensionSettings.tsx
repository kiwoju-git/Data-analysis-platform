import type { DatasetColumnResponse } from "./api";
import type { GpValidationMethod } from "./api/types/analysisResultsRegression";
import { NumericColumnPicker } from "./components/NumericColumnPicker";
import { useI18n } from "./i18n/LocaleProvider";
import type { GpExtensionDraft } from "./gpExtensionOptions";

export function GpExtensionSettings({ draft, onChange, method, onMethodChange, columns, numericColumns, selectedNumeric, responseId, predictorIds }: {
  draft: GpExtensionDraft; onChange: (draft: GpExtensionDraft) => void;
  method: GpValidationMethod; onMethodChange: (method: GpValidationMethod) => void;
  columns: DatasetColumnResponse[]; numericColumns: DatasetColumnResponse[]; selectedNumeric: DatasetColumnResponse[];
  responseId: string; predictorIds: string[];
}) {
  const { t } = useI18n();
  const set = <K extends keyof GpExtensionDraft>(key: K, value: GpExtensionDraft[K]) => onChange({ ...draft, [key]: value });
  const options = (available: DatasetColumnResponse[]) => <><option value="">{t("gp.select")}</option>{available.map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}</>;
  return <div className="gp-extension-settings">
    <p className="field-help">{t(method === "group_k_fold" ? "gp.extension.groupPurpose" : method === "time_series_split" ? "gp.extension.timePurpose" : method === "none" ? "gp.extension.nonePurpose" : "gp.extension.rowPurpose")}</p>
    {(method === "k_fold" || method === "group_k_fold") && <label className="checkbox-field"><input type="checkbox" checked={method === "group_k_fold"} onChange={(event) => onMethodChange(event.currentTarget.checked ? "group_k_fold" : "k_fold")} />{t("gp.extension.groupToggle")}</label>}
    <div className="option-grid option-grid-wide">
      {method === "group_k_fold" && <label><span>{t("gp.extension.groupColumn")}</span><select value={draft.groupColumnId} onChange={(event) => set("groupColumnId", event.currentTarget.value)}>{options(columns.filter((column) => column.column_id !== responseId && !predictorIds.includes(column.column_id)))}</select></label>}
      {method === "time_series_split" && <>
        <label><span>{t("gp.extension.timeColumn")}</span><select value={draft.timeColumnId} onChange={(event) => set("timeColumnId", event.currentTarget.value)}>{options(columns.filter((column) => column.column_id !== responseId && (draft.timeFormat === "timestamp" || ["integer", "decimal"].includes(column.data_type))))}</select></label>
        <label><span>{t("gp.extension.timeFormat")}</span><select value={draft.timeFormat} onChange={(event) => set("timeFormat", event.currentTarget.value as GpExtensionDraft["timeFormat"])}><option value="numeric">{t("gp.extension.numericTime")}</option><option value="timestamp">{t("gp.extension.timestamp")}</option></select></label>
        {draft.timeFormat === "numeric" ? <label><span>{t("gp.extension.timeUnit")}</span><input value={draft.timeUnit} onChange={(event) => set("timeUnit", event.currentTarget.value)} /></label> : <label><span>{t("gp.extension.timezone")}</span><select value={draft.timestampTimezone} onChange={(event) => set("timestampTimezone", event.currentTarget.value as GpExtensionDraft["timestampTimezone"])}><option value="require_offset">{t("gp.extension.requireOffset")}</option><option value="UTC">UTC</option></select></label>}
        <label><span>{t("gp.extension.gap")}</span><input type="number" min={0} max={1000} step={1} value={draft.gapTimeBlocks} onChange={(event) => set("gapTimeBlocks", Number(event.currentTarget.value))} /></label>
      </>}
      <label><span>{t("gp.extension.resource")}</span><select value={draft.resourceProfile} onChange={(event) => set("resourceProfile", event.currentTarget.value as GpExtensionDraft["resourceProfile"])}><option value="standard_exact">{t("gp.extension.standard")}</option><option value="extended_exact">{t("gp.extension.extended")}</option></select></label>
    </div>
    {draft.resourceProfile === "extended_exact" && <p className="notice-box">{t("gp.extension.resourceNotice")}</p>}
    {method === "time_series_split" && <details open={draft.lagEnabled}><summary>{t("gp.extension.lagTitle")}</summary>
      <label className="checkbox-field"><input type="checkbox" checked={draft.lagEnabled} onChange={(event) => set("lagEnabled", event.currentTarget.checked)} />{t("gp.extension.lagEnable")}</label>
      {draft.lagEnabled && <><p className="field-help">{t("gp.extension.lagNotice")}</p>
        <NumericColumnPicker columns={numericColumns} selectedColumnIds={draft.laggedColumnIds} legend={t("gp.extension.lagColumns")} helpText={t("gp.extension.lagNotice")} minimumSelection={1} maximumSelection={12} onClear={() => set("laggedColumnIds", [])} onToggle={(id, checked) => set("laggedColumnIds", checked ? [...draft.laggedColumnIds, id] : draft.laggedColumnIds.filter((value) => value !== id))} />
        <div className="option-grid option-grid-wide"><label><span>{t("gp.extension.lags")}</span><input value={draft.lagText} onChange={(event) => set("lagText", event.currentTarget.value)} /></label><label><span>{t("gp.extension.series")}</span><select value={draft.seriesColumnId} onChange={(event) => set("seriesColumnId", event.currentTarget.value)}>{options(columns.filter((column) => column.column_id !== responseId && column.column_id !== draft.timeColumnId && !predictorIds.includes(column.column_id)))}</select></label></div>
      </>}
    </details>}
    {selectedNumeric.length >= 2 && <details><summary>{t("gp.extension.initialSurface")}</summary><div className="option-grid option-grid-wide">
      <label><span>{t("gp.surfaceX")}</span><select value={draft.initialX} onChange={(event) => onChange({ ...draft, initialX: event.currentTarget.value, initialY: event.currentTarget.value ? draft.initialY || selectedNumeric.find((column) => column.column_id !== event.currentTarget.value)?.column_id || "" : "" })}>{options(selectedNumeric)}</select></label>
      <label><span>{t("gp.surfaceY")}</span><select value={draft.initialY} onChange={(event) => onChange({ ...draft, initialY: event.currentTarget.value, initialX: event.currentTarget.value ? draft.initialX || selectedNumeric.find((column) => column.column_id !== event.currentTarget.value)?.column_id || "" : "" })}>{options(selectedNumeric)}</select></label>
    </div></details>}
  </div>;
}
