import { useEffect, useMemo, useState } from "react";

import {
  fetchDatasetGroupLevels,
  type AnalysisResultEnvelope,
  type DatasetColumnResponse,
  type DatasetVersionResponse,
  type GroupLevelPreflightItem,
  type MannWhitneyResult,
} from "./api";
import { serializeAnalysisFilterDrafts, type AnalysisFilterDraft } from "./analysisFilters";
import { useI18n } from "./i18n/LocaleProvider";

export type MannWhitneyInputLayout = "stacked" | "unstacked";

export interface MannWhitneyExecutionOptions {
  inputLayout: MannWhitneyInputLayout;
  group1Value?: string;
  group2Value?: string;
  sample1ColumnId?: string;
  sample2ColumnId?: string;
}

interface MannWhitneyPanelProps {
  alpha: number;
  alternative: string;
  analysisResult: AnalysisResultEnvelope | null;
  filterDrafts: AnalysisFilterDraft[];
  filterValidationError: string | null;
  groupColumnId: string | null;
  groupColumns: DatasetColumnResponse[];
  isRunningAnalysis: boolean;
  method: string;
  methodId: string;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: MannWhitneyResult | null;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onAlternativeChange: (alternative: string) => void;
  onGroupColumnChange: (columnId: string) => void;
  onMethodChange: (method: string) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: (options: MannWhitneyExecutionOptions) => void;
}

export function MannWhitneyPanel(props: MannWhitneyPanelProps) {
  const { t, formatNumber } = useI18n();
  const [inputLayout, setInputLayout] = useState<MannWhitneyInputLayout>("stacked");
  const [sample1ColumnId, setSample1ColumnId] = useState("");
  const [sample2ColumnId, setSample2ColumnId] = useState("");
  const [levels, setLevels] = useState<GroupLevelPreflightItem[]>([]);
  const [group1Value, setGroup1Value] = useState("");
  const [group2Value, setGroup2Value] = useState("");
  const [preflightError, setPreflightError] = useState<string | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);

  useEffect(() => {
    if (sample1ColumnId.length === 0 && props.responseColumns.length > 0) {
      setSample1ColumnId(props.responseColumnId ?? props.responseColumns[0].column_id);
    }
    if (sample2ColumnId.length === 0 && props.responseColumns.length > 1) {
      const first = props.responseColumnId ?? props.responseColumns[0].column_id;
      setSample2ColumnId(
        props.responseColumns.find((column) => column.column_id !== first)?.column_id ?? "",
      );
    }
  }, [props.responseColumnId, props.responseColumns, sample1ColumnId, sample2ColumnId]);

  const filterSnapshot = useMemo(() => {
    if (props.version === null || props.filterValidationError !== null) return null;
    return {
      expression_version: 1 as const,
      conditions: serializeAnalysisFilterDrafts(props.filterDrafts, props.version.columns),
    };
  }, [props.filterDrafts, props.filterValidationError, props.version]);

  useEffect(() => {
    setLevels([]);
    setGroup1Value("");
    setGroup2Value("");
    setPreflightError(null);
    if (
      props.version === null ||
      props.groupColumnId === null ||
      filterSnapshot === null
    ) {
      return;
    }
    let cancelled = false;
    setPreflightLoading(true);
    void fetchDatasetGroupLevels(props.version.version_id, {
      group_column_id: props.groupColumnId,
      filter_snapshot: filterSnapshot,
      maximum_levels: 100,
    })
      .then((response) => {
        if (cancelled) return;
        setLevels(response.levels);
        if (response.truncated) {
          setPreflightError("failed");
        } else if (response.levels.length < 2) {
          setPreflightError("need_two_levels");
        } else if (response.levels.length === 2) {
          setGroup1Value(response.levels[0].value);
          setGroup2Value(response.levels[1].value);
        }
      })
      .catch(() => {
        if (!cancelled) setPreflightError("failed");
      })
      .finally(() => {
        if (!cancelled) setPreflightLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filterSnapshot, props.groupColumnId, props.version]);

  const sample1Label = columnLabel(props.responseColumns, sample1ColumnId);
  const sample2Label = columnLabel(props.responseColumns, sample2ColumnId);
  const group1Label = levelLabel(levels, group1Value);
  const group2Label = levelLabel(levels, group2Value);
  const firstLabel = inputLayout === "stacked" ? group1Label : sample1Label;
  const secondLabel = inputLayout === "stacked" ? group2Label : sample2Label;
  const stackedReady =
    props.responseColumnId !== null &&
    props.groupColumnId !== null &&
    props.responseColumnId !== props.groupColumnId &&
    group1Value.length > 0 &&
    group2Value.length > 0 &&
    group1Value !== group2Value &&
    preflightError === null &&
    !preflightLoading;
  const unstackedReady =
    sample1ColumnId.length > 0 &&
    sample2ColumnId.length > 0 &&
    sample1ColumnId !== sample2ColumnId;
  const canRun =
    props.version !== null &&
    (inputLayout === "stacked" ? stackedReady : unstackedReady) &&
    props.alpha > 0 &&
    props.alpha < 1 &&
    props.filterValidationError === null;

  return (
    <section className="analysis-run-panel" data-analysis-execution={props.methodId}>
      {props.version === null ? (
        <div className="notice-box">{t("mannWhitney.datasetRequired")}</div>
      ) : (
        <>
          <div className="segmented-control" role="group" aria-label={t("mannWhitney.inputLayout")}>
            <button
              aria-pressed={inputLayout === "stacked"}
              className={inputLayout === "stacked" ? "active" : ""}
              onClick={() => setInputLayout("stacked")}
              type="button"
            >
              {t("mannWhitney.stacked")}
            </button>
            <button
              aria-pressed={inputLayout === "unstacked"}
              className={inputLayout === "unstacked" ? "active" : ""}
              onClick={() => setInputLayout("unstacked")}
              type="button"
            >
              {t("mannWhitney.unstacked")}
            </button>
          </div>
          <div className="option-grid">
            {inputLayout === "stacked" ? (
              <>
                <ColumnSelect label={t("mannWhitney.response")} value={props.responseColumnId ?? ""} columns={props.responseColumns} onChange={props.onResponseColumnChange} />
                <ColumnSelect label={t("mannWhitney.group")} value={props.groupColumnId ?? ""} columns={props.groupColumns} onChange={props.onGroupColumnChange} />
                <LevelSelect label={t("mannWhitney.group1")} value={group1Value} levels={levels} disabled={preflightLoading} onChange={setGroup1Value} />
                <LevelSelect label={t("mannWhitney.group2")} value={group2Value} levels={levels} disabled={preflightLoading} onChange={setGroup2Value} />
              </>
            ) : (
              <>
                <ColumnSelect label={t("mannWhitney.sample1")} value={sample1ColumnId} columns={props.responseColumns} onChange={setSample1ColumnId} />
                <ColumnSelect label={t("mannWhitney.sample2")} value={sample2ColumnId} columns={props.responseColumns.filter((column) => column.column_id !== sample1ColumnId)} onChange={setSample2ColumnId} />
              </>
            )}
            <label>
              <span>{t("mannWhitney.method")}</span>
              <select value={props.method} onChange={(event) => props.onMethodChange(event.currentTarget.value)}>
                <option value="auto">{t("mannWhitney.auto")}</option>
                <option value="exact">Exact</option>
                <option value="asymptotic">Asymptotic</option>
              </select>
            </label>
            <label>
              <span>{t("mannWhitney.alternative")}</span>
              <select value={props.alternative} onChange={(event) => props.onAlternativeChange(event.currentTarget.value)}>
                <option value="two_sided">{t("mannWhitney.twoSided")}</option>
                <option value="greater">{firstLabel || t("mannWhitney.sample1")} &gt; {secondLabel || t("mannWhitney.sample2")}</option>
                <option value="less">{firstLabel || t("mannWhitney.sample1")} &lt; {secondLabel || t("mannWhitney.sample2")}</option>
              </select>
            </label>
            <label>
              <span>{t("mannWhitney.alpha")}</span>
              <input max="0.5" min="0.001" step="0.001" type="number" value={props.alpha} onChange={(event) => props.onAlphaChange(Number(event.currentTarget.value))} />
            </label>
          </div>
          {inputLayout === "stacked" && preflightLoading ? <div className="notice-box">{t("mannWhitney.preflightLoading")}</div> : null}
          {inputLayout === "stacked" && levels.length === 2 && preflightError === null ? <p className="help-text">{t("mannWhitney.autoSelected")}</p> : null}
          {inputLayout === "stacked" && levels.length > 2 ? <p className="help-text">{t("mannWhitney.chooseTwoLevels")}</p> : null}
          {inputLayout === "unstacked" ? <p className="help-text">{t("mannWhitney.availableCaseHelp")}</p> : null}
          {inputLayout === "stacked" && preflightError !== null ? <div className="error-box">{t(preflightError === "need_two_levels" ? "mannWhitney.needTwoLevels" : "mannWhitney.preflightFailed")}</div> : null}
          <button
            className="primary-button"
            disabled={props.isRunningAnalysis || !canRun}
            onClick={() => props.onRun({
              inputLayout,
              group1Value: inputLayout === "stacked" ? group1Value : undefined,
              group2Value: inputLayout === "stacked" ? group2Value : undefined,
              sample1ColumnId: inputLayout === "unstacked" ? sample1ColumnId : undefined,
              sample2ColumnId: inputLayout === "unstacked" ? sample2ColumnId : undefined,
            })}
            type="button"
          >
            {props.isRunningAnalysis ? t("mannWhitney.running") : t("mannWhitney.run")}
          </button>
          {props.analysisResult?.warnings.length ? (
            <ul className="warning-list">
              {props.analysisResult.warnings.map((warning, index) => <li key={`${warning.code}-${index}`}>{warning.message}</li>)}
            </ul>
          ) : null}
          {props.result !== null ? <MannWhitneyResults result={props.result} formatNumber={formatNumber} /> : null}
        </>
      )}
    </section>
  );
}

function MannWhitneyResults({ result, formatNumber }: { result: MannWhitneyResult; formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string }) {
  const { t } = useI18n();
  const samples = result.samples ?? result.groups.map((group, index) => ({
    sample_index: index + 1,
    label: group.group_label,
    source_column: result.response as NonNullable<MannWhitneyResult["response"]>,
    source_group_value: group.group_label,
    n_total: group.n,
    n_used: group.n,
    n_excluded_missing: 0,
    n_excluded_non_numeric: 0,
  }));
  const number = (value: number | null) => value === null ? "-" : formatNumber(value, { maximumSignificantDigits: 6 });
  return <>
    <div className="metadata-grid" aria-label={t("mannWhitney.summary")}>
      <span>{t("mannWhitney.inputLayout")}</span><strong>{t(result.input_layout === "unstacked" ? "mannWhitney.unstacked" : "mannWhitney.stacked")}</strong>
      <span>{t("mannWhitney.comparison")}</span><strong>{result.test.group_1_label} vs {result.test.group_2_label}</strong>
      <span>{t("mannWhitney.usedN")}</span><strong>{formatNumber(result.n_used)} / {formatNumber(result.n_total)}</strong>
      <span>{t("mannWhitney.method")}</span><strong>{methodLabel(result.resolved_method)}</strong>
      <span>{t("mannWhitney.ties")}</span><strong>{t(result.has_ties ? "mannWhitney.yes" : "mannWhitney.no")}</strong>
      {typeof result.n_excluded_unselected_groups === "number" && result.n_excluded_unselected_groups > 0 ? <><span>{t("mannWhitney.unselectedRows")}</span><strong>{formatNumber(result.n_excluded_unselected_groups)}</strong></> : null}
    </div>
    <div className="table-wrap"><table className="result-table"><thead><tr><th>U</th><th>p-value</th><th>rank-biserial</th><th>{t("mannWhitney.commonLanguage")}</th><th>{t("mannWhitney.decision")}</th></tr></thead><tbody><tr><td>{number(result.test.u_statistic)}</td><td>{number(result.test.p_value)}</td><td>{number(result.test.effect_size.rank_biserial)}</td><td>{number(result.test.effect_size.common_language_probability)}</td><td>{t(result.test.reject_null ? "mannWhitney.reject" : "mannWhitney.failToReject")}</td></tr></tbody></table></div>
    <div className="table-wrap"><table className="result-table"><thead><tr><th>{t("mannWhitney.sample")}</th><th>N</th><th>{t("mannWhitney.missing")}</th><th>{t("mannWhitney.median")}</th><th>{t("mannWhitney.meanRank")}</th><th>{t("mannWhitney.rankSum")}</th><th>{t("mannWhitney.range")}</th></tr></thead><tbody>{result.groups.map((group, index) => <tr key={`${group.group_index}-${group.group_label}`}><td>{group.group_label}</td><td>{group.n}</td><td>{samples[index]?.n_excluded_missing ?? 0}</td><td>{number(group.median)}</td><td>{number(group.mean_rank)}</td><td>{number(group.rank_sum)}</td><td>{number(group.min)} - {number(group.max)}</td></tr>)}</tbody></table></div>
  </>;
}

function ColumnSelect({ label, value, columns, onChange }: { label: string; value: string; columns: DatasetColumnResponse[]; onChange: (value: string) => void }) {
  const { t } = useI18n();
  return <label><span>{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(event.currentTarget.value)}><option value="">{t("mannWhitney.select")}</option>{columns.map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}</select></label>;
}

function LevelSelect({ label, value, levels, disabled, onChange }: { label: string; value: string; levels: GroupLevelPreflightItem[]; disabled: boolean; onChange: (value: string) => void }) {
  const { t } = useI18n();
  return <label><span>{label}</span><select aria-label={label} disabled={disabled} value={value} onChange={(event) => onChange(event.currentTarget.value)}><option value="">{t("mannWhitney.select")}</option>{levels.map((level) => <option key={level.value} value={level.value}>{level.display_label} (N {level.n_used})</option>)}</select></label>;
}

function columnLabel(columns: DatasetColumnResponse[], columnId: string): string {
  return columns.find((column) => column.column_id === columnId)?.display_name ?? "";
}

function levelLabel(levels: GroupLevelPreflightItem[], value: string): string {
  return levels.find((level) => level.value === value)?.display_label ?? value;
}

function methodLabel(method: string): string {
  if (method === "exact") return "Exact";
  if (method === "asymptotic") return "Asymptotic";
  return method;
}
