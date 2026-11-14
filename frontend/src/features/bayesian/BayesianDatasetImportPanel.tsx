import { useEffect, useRef, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import type { AnalysisFilterSnapshot, DatasetVersionResponse } from "../../api";
import type { AnyBayesianStudyResponse } from "../../api/types/boMixed";
import type { MixtureStudy } from "../../api/boMixture";
import { mixtureMessages } from "../../i18n/boMixture";
import { useI18n } from "../../i18n/LocaleProvider";
import { datasetImportMessages } from "../../i18n/boDatasetImport";
import { mixedMessages } from "../../i18n/boMixed";
import { newMixedFactor, type MixedFactorDraft } from "./boMixedDraft";
import { newResponseDraft, type ResponseGoalDraft } from "./bayesianVectorDraft";
import { buildDatasetImportRequest, type DatasetImportDraft } from "./boDatasetImportDraft";
import { BayesianResponseGoals } from "./BayesianResponseGoals";
import { BayesianConstraintEditor } from "./BayesianConstraintEditor";
import { BayesianCategoryCorrelationEditor } from "./BayesianCategoryCorrelationEditor";
import { useDatasetImport } from "./hooks/useDatasetImport";
import "./boDatasetImport.css";

export interface BayesianDatasetSourceProps {
  version?: DatasetVersionResponse | null;
  filterSnapshot?: AnalysisFilterSnapshot | null;
}
interface Props extends BayesianDatasetSourceProps {
  ownerKey: string; disabled: boolean; onBusyChange: (value: boolean) => void;
  onCreated: (value: AnyBayesianStudyResponse | MixtureStudy) => void;
}
export function BayesianDatasetImportPanel(props: Props) {
  const { locale } = useI18n();
  const text = datasetImportMessages(locale);
  if (!props.version) return <div className="notice-box">{text.missingDataset}</div>;
  if (!props.filterSnapshot) return <div className="notice-box">{text.invalidFilter}</div>;
  const key = JSON.stringify([props.ownerKey, props.version.version_id, props.version.schema_hash, props.filterSnapshot]);
  return <ImportForm key={key} {...props} version={props.version} filterSnapshot={props.filterSnapshot} />;
}
function ImportForm({ version, filterSnapshot, disabled, onBusyChange, onCreated }: Props & { version: DatasetVersionResponse; filterSnapshot: AnalysisFilterSnapshot }) {
  const { locale } = useI18n();
  const text = datasetImportMessages(locale);
  const next = useRef(2);
  const nextConstraint = useRef(1);
  const [draft, setDraft] = useState<DatasetImportDraft>(() => ({
    name: "", factors: [{ ...newMixedFactor(1), columnId: "", low: "", high: "", levels: [""] }],
    responseMode: "scalar", scalarColumnId: "", goal: "maximize", target: "", tolerance: "",
    responses: [newResponseDraft(1)], responseColumns: {}, constraints: [], missingPolicy: "reject",
  }));
  const state = useDatasetImport(onCreated);
  const working = state.busy !== null;
  useEffect(() => { onBusyChange(working); return () => onBusyChange(false); }, [working, onBusyChange]);
  function edit(update: (current: DatasetImportDraft) => DatasetImportDraft) { state.invalidate(); setDraft(update); }
  const referenced = (current: DatasetImportDraft, id: string) => current.constraints.some(row => (row.coefficients[id] ?? "").trim() !== "");
  function factor(key: number, field: keyof MixedFactorDraft | "columnId", value: string | string[]) {
    edit(current => ({ ...current, factors: current.factors.map(row => row.key === key && !((field === "kind" || field === "columnId") && referenced(current, row.factorId)) ? { ...row, [field]: value } : row) }));
  }
  const selectColumn = (label: string, value: string, change: (id: string) => void, locked = false, description?: string) => <select aria-label={label} disabled={locked} aria-describedby={description} value={value} onChange={event => change(event.currentTarget.value)}>
    <option value="">{text.selectColumn}</option>{version.columns.map(column => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}
  </select>;
  const goals = {
    responseGoals: draft.responses.map(row => {
      const column = version.columns.find(item => item.column_id === draft.responseColumns[row.responseId]);
      return { ...row, name: column ? draft.displayNames?.[column.column_id] ?? column.display_name : "", unit: column?.unit ?? "" };
    }),
    updateResponseGoal: <Field extends keyof Omit<ResponseGoalDraft, "key">>(key: number, field: Field, value: ResponseGoalDraft[Field]) => edit(current => ({ ...current, responses: current.responses.map(row => row.key === key ? { ...row, [field]: value } : row) })),
    removeResponseGoal: (key: number) => edit(current => ({ ...current, responses: current.responses.filter(row => row.key !== key) })),
    addResponseGoal: () => { const key = next.current++; edit(current => ({ ...current, responses: [...current.responses, newResponseDraft(key)] })); },
  };
  return <section className="bo-dataset-import" aria-label={text.region}>
    <h3>{text.mode}</h3>
    <p className="muted">{text.sourceNotice}</p>
    <fieldset disabled={state.busy === "create" || (disabled && !working)}>
      <legend>{text.mappingLegend}</legend>
      <label>{text.studyName}<input aria-label={text.studyNameInput} value={draft.name} maxLength={120} onChange={event => { const value = event.currentTarget.value; edit(current => ({ ...current, name: value })); }} /></label>
      <label className="checkbox-label"><input type="checkbox" checked={!!draft.mixture} onChange={event => { const checked = event.currentTarget.checked; edit(current => {
        if (!checked) return { ...current, mixture: undefined };
        const rows = current.factors.length < 2 ? [...current.factors, { ...newMixedFactor(next.current++), columnId: "", low: "", high: "" }] : current.factors;
        return { ...current, factors: rows, mixture: { total: "1", unit: "g", coding: "auto", componentKeys: [] } };
      }); }} />{mixtureMessages(locale).title}</label>
      {draft.mixture && <><div className="form-grid">{(["total", "unit"] as const).map(field => <label key={field}>{mixtureMessages(locale)[field]}<input value={draft.mixture![field]} inputMode={field === "total" ? "decimal" : "text"} onChange={event => { const value = event.currentTarget.value; edit(current => current.mixture ? { ...current, mixture: { ...current.mixture, [field]: value } } : current); }} /></label>)}<label>{mixtureMessages(locale).coding}<select aria-label={mixtureMessages(locale).coding} value={draft.mixture.coding} onChange={event => { const coding = event.currentTarget.value as "lower" | "upper" | "auto"; edit(current => current.mixture ? { ...current, mixture: { ...current.mixture, coding } } : current); }}>{(["lower", "upper", "auto"] as const).map(value => <option key={value} value={value}>{mixtureMessages(locale)[value]}</option>)}</select></label></div><p>{mixtureMessages(locale).closure}</p></>}
      <div className="table-wrap"><table className="result-table"><caption>{text.predictorsCaption}</caption>
        <thead><tr>{[text.column, text.type, text.domain, text.remove].map(label => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>{draft.factors.map((row, index) => {
          const locked = referenced(draft, row.factorId), description = locked ? `bo-import-locked-${row.key}` : undefined;
          return <tr key={row.key}>
          <td>{selectColumn(`X ${index + 1}`, row.columnId, value => factor(row.key, "columnId", value), locked, description)}</td>
          <td>{draft.mixture && <label className="checkbox-label"><input type="checkbox" checked={draft.mixture.componentKeys.includes(row.key)} disabled={locked} onChange={event => { const checked = event.currentTarget.checked; edit(current => current.mixture ? { ...current, factors: current.factors.map(factor => factor.key === row.key && checked ? { ...factor, kind: "continuous" } : factor), mixture: { ...current.mixture, componentKeys: checked ? [...current.mixture.componentKeys, row.key] : current.mixture.componentKeys.filter(key => key !== row.key) } } : current); }} />{mixtureMessages(locale).components}</label>}<select aria-label={`X ${index + 1} ${text.typeInput}`} disabled={locked || !!draft.mixture?.componentKeys.includes(row.key)} aria-describedby={description} value={row.kind} onChange={event => factor(row.key, "kind", event.currentTarget.value)}>
            <option value="continuous">{text.continuous}</option><option value="discrete_numeric">{text.discreteNumeric}</option><option value="nominal">{text.nominal}</option><option value="ordinal">{text.ordinal}</option>
          </select>{locked && <p id={description} className="muted">{text.constrainedFactor}</p>}{row.kind === "nominal" && row.correlation === "ordinal_monotone_latent_rbf_v1" && <p role="alert">{text.incompatiblePolicy}</p>}</td>
          <td>{row.kind === "nominal" || row.kind === "ordinal" ? <label>{text.levelsHint}<textarea aria-label={`X ${index + 1} ${text.levelsInput}`} value={row.levels.join("\n")} onChange={event => factor(row.key, "levels", event.currentTarget.value.split("\n"))} /></label> : <div className="form-grid">
            {(["low", "high", ...(row.kind === "discrete_numeric" ? ["step"] : [])] as const).map(field => <label key={field}>{field === "low" ? text.lower : field === "high" ? text.upper : text.step}<input inputMode="decimal" aria-label={`X ${index + 1} ${field}`} value={row[field as "low" | "high" | "step"]} onChange={event => factor(row.key, field as "low" | "high" | "step", event.currentTarget.value)} /></label>)}
          </div>}</td>
          <td><button type="button" className="secondary-button" title={text.removePredictor} aria-label={`${text.removePredictor} ${index + 1}`} aria-describedby={description} disabled={draft.factors.length <= 1 || locked} onClick={() => edit(current => referenced(current, row.factorId) ? current : ({ ...current, factors: current.factors.filter(item => item.key !== row.key) }))}><Trash2 size={16} /></button></td>
        </tr>; })}</tbody></table></div>
      <button type="button" className="secondary-button" disabled={draft.factors.length >= 10} onClick={() => { const key = next.current++; edit(current => ({ ...current, factors: [...current.factors, { ...newMixedFactor(key), columnId: "", low: "", high: "", levels: [""] }] })); }}><Plus size={16} />{text.addPredictor}</button>
      {draft.mixture && draft.responseMode === "scalar" && <p role="alert">{locale === "ko" ? "혼합물은 만족도 반응 목표가 필요합니다. 반응 목적을 직접 선택하십시오. 기존 단일 반응은 자동 변환하지 않습니다." : "Mixtures require desirability response goals. Select the response objective explicitly; existing scalar goals are not converted."}</p>}
      <label>{text.responseObjective}<select aria-label={text.responseObjective} value={draft.responseMode} onChange={event => { const value = event.currentTarget.value as "scalar" | "vector"; edit(current => ({ ...current, responseMode: value })); }}>
        <option value="scalar" disabled={!!draft.mixture}>{text.singleResponse}</option><option value="vector">{text.desirabilityResponses}</option>
      </select></label>
      {draft.responseMode === "scalar" ? <div className="form-grid">
        <label>Y{selectColumn("Y", draft.scalarColumnId, value => edit(current => ({ ...current, scalarColumnId: value })))}</label>
        <label>{text.goal}<select aria-label={text.goal} value={draft.goal} onChange={event => { const value = event.currentTarget.value as typeof draft.goal; edit(current => ({ ...current, goal: value })); }}>
          <option value="maximize">{text.maximize}</option><option value="minimize">{text.minimize}</option><option value="match_target">{text.matchTarget}</option>
        </select></label>
        {draft.goal === "match_target" && (["target", "tolerance"] as const).map(field => <label key={field}>{field === "target" ? text.target : text.tolerance}<input inputMode="decimal" value={draft[field]} onChange={event => { const value = event.currentTarget.value; edit(current => ({ ...current, [field]: value })); }} /></label>)}
        {draft.factors.some(row => row.kind === "nominal" || row.kind === "ordinal") && <p className="notice-box">{text.categoryObjectiveNotice}</p>}
      </div> : <>
        <div className="form-grid">{draft.responses.map((row, index) => <label key={row.key}>{`Y ${index + 1}`}{selectColumn(`Y ${index + 1}`, draft.responseColumns[row.responseId] ?? "", value => edit(current => ({ ...current, responseColumns: { ...current.responseColumns, [row.responseId]: value } })))}</label>)}</div>
        <BayesianResponseGoals draft={goals} namesReadOnly showCreationNotice={false} sourceKey={JSON.stringify([version.version_id, draft.responseColumns])} />
      </>}
      <label>{text.missingPolicy}<select aria-label={text.missingPolicy} value={draft.missingPolicy} onChange={event => { const value = event.currentTarget.value as typeof draft.missingPolicy; edit(current => ({ ...current, missingPolicy: value })); }}>
        <option value="reject">{text.rejectMissing}</option><option value="complete_case">{text.completeCases}</option>
      </select></label>
      <p className="muted">{text.domainNotice}</p>
      <details><summary>{text.advanced}</summary>
        <BayesianConstraintEditor locale={locale} idPrefix="bo-import" factors={draft.factors.map(row => ({ ...row, name: draft.displayNames?.[row.columnId] ?? version.columns.find(column => column.column_id === row.columnId)?.display_name ?? row.factorId }))} constraints={draft.constraints}
          onChange={update => edit(current => ({ ...current, constraints: update(current.constraints) }))}
          onAdd={() => { const key = nextConstraint.current++; edit(current => ({ ...current, constraints: [...current.constraints, { key, name: `Constraint ${key}`, relation: "less_than_or_equal", bound: "", coefficients: {} }] })); }} />
        {draft.factors.filter(row => row.kind === "nominal" || row.kind === "ordinal").map(row => <BayesianCategoryCorrelationEditor key={row.key} locale={locale} factor={row}
          label={`X ${draft.factors.indexOf(row) + 1} ${mixedMessages(locale).correlation}`} onChange={value => factor(row.key, "correlation", value)} />)}
        {draft.factors.some(row => row.kind === "nominal" || row.kind === "ordinal") && <p className="muted">{mixedMessages(locale).parameterLimits}</p>}
      </details>
      <details><summary>{text.displayNames}</summary>
        <p>{text.displayNamesNotice}</p>
        {version.columns.filter(column => draft.factors.some(row => row.columnId === column.column_id) || (draft.responseMode === "scalar" ? draft.scalarColumnId === column.column_id : Object.values(draft.responseColumns).includes(column.column_id))).map(column =>
          <label key={column.column_id}>{column.display_name}<input aria-label={`${text.displayNameInput} ${column.display_name}`} value={draft.displayNames?.[column.column_id] ?? column.display_name} maxLength={80}
            onChange={event => { const value = event.currentTarget.value; edit(current => ({ ...current, displayNames: { ...current.displayNames, [column.column_id]: value } })); }} /></label>)}
      </details>
      <button type="button" className="secondary-button" disabled={working} onClick={() => void state.preflight(buildDatasetImportRequest(version, filterSnapshot, draft))}>{text.preflight}</button>
    </fieldset>
    {working && <p role="status">{state.busy === "create" ? text.saving : text.validating}</p>}
    {state.error && <div role="alert" className="error-box"><p>{text.errorNotice}</p><code>{state.error}</code>{state.retryAvailable && <p>{text.retryNotice}</p>}</div>}
    {state.review && <section aria-label={text.review}>
      <details><summary>{text.sourceHashes}</summary><dl className="metadata-grid">
        <div><dt>{text.datasetVersion}</dt><dd><code>{state.review.result.source.dataset_version_id}</code></dd></div>
        <div><dt>Schema SHA-256</dt><dd><code>{state.review.result.source.schema_hash}</code></dd></div>
        <div><dt>Canonical SHA-256</dt><dd><code>{state.review.result.source.canonical_sha256}</code></dd></div>
      </dl></details>
      <dl className="metadata-grid">{[
        [text.totalRows, state.review.result.n_total], [text.filteredRows, state.review.result.n_filtered],
        [text.missingRows, state.review.result.n_missing], [text.usedRows, state.review.result.n_used],
        [text.uniqueConditions, state.review.result.unique_coordinate_count], [text.repeatedRows, state.review.result.repeated_coordinate_count],
        [text.conflictingConditions, state.review.result.conflicting_coordinate_count],
      ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      {state.review.result.warnings.length > 0 && <div className="notice-box"><p>{text.warnings}</p><ul>{state.review.result.warnings.map(code => <li key={code}>{
        code === "bayesian_optimization_history_incomplete" ? text.incompleteHistory :
        code === "bayesian_import_repeated_coordinates_retained" ? text.repeatsRetained :
        code === "bayesian_import_complete_case_exclusions" ? text.missingExcluded : code
      }<details><summary>{text.code}</summary><code>{code}</code></details></li>)}</ul></div>}
      <p>{text.commitNotice}</p>
      <button type="button" disabled={working || disabled} onClick={() => void state.create(state.retryAvailable)}>{state.retryAvailable ? text.retry : text.create}</button>
    </section>}
  </section>;
}
