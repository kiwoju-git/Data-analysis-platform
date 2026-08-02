import { useEffect, useMemo, useState } from "react";

import {
  fetchDatasetGroupLevels,
  type AnalysisResultEnvelope,
  type DatasetColumnResponse,
  type DatasetVersionResponse,
  type GroupLevelPreflightItem,
  type OneWayAnovaResult,
} from "./api";
import {
  serializeAnalysisFilterDrafts,
  type AnalysisFilterDraft,
} from "./analysisFilters";

export interface OneWayAnovaExecutionOptions {
  anovaType: "standard" | "welch";
  posthocMethod: "none" | "tukey_kramer" | "dunnett" | "games_howell";
  posthocPolicy: "when_requested" | "after_significant";
  controlGroupLabel: string | null;
}

interface OneWayAnovaPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  filterDrafts: AnalysisFilterDraft[];
  filterValidationError: string | null;
  groupColumnId: string | null;
  groupColumns: DatasetColumnResponse[];
  isRunningAnalysis: boolean;
  methodId: string;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: OneWayAnovaResult | null;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onGroupColumnChange: (columnId: string) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: (options: OneWayAnovaExecutionOptions) => void;
}

export function OneWayAnovaPanel({
  alpha,
  analysisResult,
  confidenceLevel,
  filterDrafts,
  filterValidationError,
  groupColumnId,
  groupColumns,
  isRunningAnalysis,
  methodId,
  responseColumnId,
  responseColumns,
  result,
  version,
  onAlphaChange,
  onConfidenceLevelChange,
  onGroupColumnChange,
  onResponseColumnChange,
  onRun,
}: OneWayAnovaPanelProps) {
  const [anovaType, setAnovaType] = useState<"standard" | "welch">("standard");
  const [posthocMethod, setPosthocMethod] = useState<
    "none" | "tukey_kramer" | "dunnett" | "games_howell"
  >("tukey_kramer");
  const [posthocPolicy, setPosthocPolicy] = useState<
    "when_requested" | "after_significant"
  >("when_requested");
  const [controlGroupLabel, setControlGroupLabel] = useState<string | null>(null);
  const [groupLevels, setGroupLevels] = useState<GroupLevelPreflightItem[]>([]);
  const [groupLevelsError, setGroupLevelsError] = useState<string | null>(null);
  const [isLoadingGroupLevels, setIsLoadingGroupLevels] = useState(false);

  const filterSnapshot = useMemo(() => {
    if (version === null || filterValidationError !== null) {
      return null;
    }
    return {
      expression_version: 1,
      conditions: serializeAnalysisFilterDrafts(filterDrafts, version.columns),
    };
  }, [filterDrafts, filterValidationError, version]);

  useEffect(() => {
    setControlGroupLabel(null);
    setGroupLevels([]);
    setGroupLevelsError(null);
    if (
      version === null ||
      groupColumnId === null ||
      posthocMethod !== "dunnett" ||
      filterSnapshot === null
    ) {
      setIsLoadingGroupLevels(false);
      return;
    }
    let cancelled = false;
    setIsLoadingGroupLevels(true);
    void fetchDatasetGroupLevels(version.version_id, {
      group_column_id: groupColumnId,
      filter_snapshot: filterSnapshot,
      maximum_levels: 20,
    })
      .then((preflight) => {
        if (cancelled) return;
        setGroupLevels(preflight.levels);
        if (preflight.truncated) {
          setGroupLevelsError("그룹 수준이 20개를 초과하여 Dunnett 비교를 실행할 수 없습니다.");
        } else {
          setControlGroupLabel(preflight.levels[0]?.value ?? null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setGroupLevelsError(
            error instanceof Error ? error.message : "group_level_preflight_failed",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoadingGroupLevels(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filterSnapshot, groupColumnId, posthocMethod, version]);

  const canRun =
    version !== null &&
    responseColumnId !== null &&
    groupColumnId !== null &&
    responseColumnId !== groupColumnId &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    filterValidationError === null &&
    groupLevelsError === null &&
    !isLoadingGroupLevels &&
    (posthocMethod !== "dunnett" || controlGroupLabel !== null);

  function changeAnovaType(nextType: "standard" | "welch") {
    setAnovaType(nextType);
    setPosthocMethod(nextType === "standard" ? "tukey_kramer" : "games_howell");
    setControlGroupLabel(null);
  }

  return (
    <section className="analysis-run-panel" data-analysis-execution={methodId}>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid">
            <label>
              <span>반응 변수</span>
              <select aria-label="반응 변수" value={responseColumnId ?? ""} onChange={(event) => onResponseColumnChange(event.currentTarget.value)}>
                <option value="">선택</option>
                {responseColumns.map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}
              </select>
            </label>
            <label>
              <span>그룹 변수</span>
              <select aria-label="그룹 변수" value={groupColumnId ?? ""} onChange={(event) => onGroupColumnChange(event.currentTarget.value)}>
                <option value="">선택</option>
                {groupColumns.map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}
              </select>
            </label>
            <label>
              <span>유의수준 alpha</span>
              <input max="0.5" min="0.001" step="0.001" type="number" value={alpha} onChange={(event) => onAlphaChange(Number(event.currentTarget.value))} />
            </label>
            <label>
              <span>신뢰수준</span>
              <input max="0.999" min="0.001" step="0.001" type="number" value={confidenceLevel} onChange={(event) => onConfidenceLevelChange(Number(event.currentTarget.value))} />
            </label>
          </div>

          <fieldset className="segmented-fieldset">
            <legend>분산 가정</legend>
            <div className="segmented-control">
              <label><input checked={anovaType === "standard"} name="anova-variance-model" type="radio" onChange={() => changeAnovaType("standard")} /><span>등분산 가정</span></label>
              <label><input checked={anovaType === "welch"} name="anova-variance-model" type="radio" onChange={() => changeAnovaType("welch")} /><span>등분산 가정 안 함</span></label>
            </div>
            <p className="cell-subtext">
              {anovaType === "standard" ? "공통 오차분산을 사용하는 표준 일원분산분석입니다." : "그룹별 분산이 다를 수 있다고 보는 Welch 일원분산분석입니다."}
            </p>
          </fieldset>

          <div className="option-grid">
            <label>
              <span>사후비교</span>
              <select aria-label="사후비교" value={posthocMethod} onChange={(event) => setPosthocMethod(event.currentTarget.value as typeof posthocMethod)}>
                <option value="none">사후비교 안 함</option>
                {anovaType === "standard" ? <>
                  <option value="tukey_kramer">Tukey-Kramer - 모든 그룹 쌍</option>
                  <option value="dunnett">Dunnett - 기준군과 비교</option>
                </> : <option value="games_howell">Games-Howell - 모든 그룹 쌍</option>}
              </select>
              <span className="cell-subtext">{posthocDescription(posthocMethod)}</span>
            </label>
            {posthocMethod === "dunnett" ? (
              <label>
                <span>기준 그룹</span>
                <select aria-label="기준 그룹" disabled={isLoadingGroupLevels || groupLevelsError !== null} value={controlGroupLabel ?? ""} onChange={(event) => setControlGroupLabel(event.currentTarget.value || null)}>
                  <option value="">{isLoadingGroupLevels ? "그룹 수준 확인 중" : "선택"}</option>
                  {groupLevels.map((level) => <option key={level.value} value={level.value}>{level.display_label} (N {level.n_used.toLocaleString()})</option>)}
                </select>
                {groupLevelsError !== null ? <span className="field-error">{groupLevelsError}</span> : null}
              </label>
            ) : null}
            <label className="checkbox-row">
              <input checked={posthocPolicy === "after_significant"} type="checkbox" onChange={(event) => setPosthocPolicy(event.currentTarget.checked ? "after_significant" : "when_requested")} />
              <span>전체 ANOVA가 유의한 경우에만 사후비교</span>
            </label>
          </div>

          <button className="primary-button" disabled={isRunningAnalysis || !canRun} onClick={() => onRun({ anovaType, posthocMethod, posthocPolicy, controlGroupLabel })} type="button">
            {isRunningAnalysis ? "실행 중" : "일원분산분석 실행"}
          </button>
          {analysisResult?.warnings.length ? <ul className="warning-list" aria-label="분석 경고">{analysisResult.warnings.map((warning, index) => <li key={`${warning.code}-${index}`}>{warning.message}</li>)}</ul> : null}
          {result !== null ? <OneWayAnovaResults result={result} /> : null}
        </>
      )}
    </section>
  );
}

function OneWayAnovaResults({ result }: { result: OneWayAnovaResult }) {
  const varianceModel = result.variance_model ?? (result.anova_type === "welch" ? "unequal" : "equal");
  const posthocMethod = result.posthoc.method;
  const isDunnett = posthocMethod === "dunnett";
  return <>
    <div className="metadata-grid" aria-label="일원분산분석 요약">
      <span>사용 N</span><strong>{result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}</strong>
      <span>분산 가정</span><strong>{varianceModel === "unequal" ? "등분산 가정 안 함" : "등분산 가정"}</strong>
      <span>전체 검정</span><strong>{varianceModel === "unequal" ? "Welch 일원분산분석" : "표준 일원분산분석"}</strong>
      <span>사후비교</span><strong>{posthocMethodLabel(posthocMethod)}</strong>
      {isDunnett ? <><span>Dunnett 기준군</span><strong>{result.posthoc.control_group_label ?? result.control_group_label ?? "-"}</strong></> : null}
    </div>
    <div className="table-wrap"><table className="result-table"><thead><tr><th>F</th><th>분자 df</th><th>분모 df</th><th>p-value</th><th>효과크기</th><th>결정</th></tr></thead><tbody><tr>
      <td>{formatAnalysisNumber(result.test.f_statistic)}</td><td>{formatAnalysisNumber(result.test.df_numerator ?? result.test.df_between)}</td><td>{formatAnalysisNumber(result.test.df_denominator ?? result.test.df_within)}</td><td>{formatAnalysisNumber(result.test.p_value)}</td>
      <td>{result.test.effect_size === null ? "Welch 효과크기 미제공" : `omega squared ${formatAnalysisNumber(result.test.effect_size.omega_squared)}; eta squared ${formatAnalysisNumber(result.test.effect_size.eta_squared)}`}</td>
      <td>{result.test.reject_null ? "기각" : "기각하지 않음"}</td>
    </tr></tbody></table></div>
    {result.anova_table !== null ? <div className="table-wrap"><table className="result-table"><thead><tr><th>source</th><th>SS</th><th>df</th><th>MS</th></tr></thead><tbody>{result.anova_table.rows.map((row) => <tr key={row.source}><td>{row.source}</td><td>{formatAnalysisNumber(row.sum_squares)}</td><td>{row.df}</td><td>{formatAnalysisNumber(row.mean_square)}</td></tr>)}</tbody></table></div> : null}
    <div className="table-wrap"><table className="result-table"><thead><tr><th>그룹</th><th>N</th><th>평균</th><th>SD</th><th>평균 CI</th></tr></thead><tbody>{result.groups.map((group) => <tr key={`${group.group_index}-${group.group_label}`}><td>{group.group_label}</td><td>{group.n}</td><td>{formatAnalysisNumber(group.mean)}</td><td>{formatAnalysisNumber(group.std)}</td><td>{formatAnalysisNumber(group.mean_confidence_interval.lower)} - {formatAnalysisNumber(group.mean_confidence_interval.upper)}</td></tr>)}</tbody></table></div>
    {result.posthoc.comparisons.length > 0 ? <div className="table-wrap"><table className="result-table"><thead><tr>{isDunnett ? <><th>처리 그룹</th><th>기준 그룹</th></> : <th>비교</th>}<th>평균 차이</th><th>CI</th><th>{isDunnett ? "Dunnett p" : "adjusted p"}</th><th>결정</th></tr></thead><tbody>{result.posthoc.comparisons.map((comparison) => <tr key={comparison.comparison_id ?? `${comparison.group_1_label}-${comparison.group_2_label}`}>{isDunnett ? <><td>{comparison.group_1_label}</td><td>{comparison.group_2_label}</td></> : <td>{comparison.group_1_label} vs {comparison.group_2_label}</td>}<td>{formatAnalysisNumber(comparison.mean_difference)}</td><td>{formatAnalysisNumber(comparison.confidence_interval.lower)} - {formatAnalysisNumber(comparison.confidence_interval.upper)}</td><td>{formatAnalysisNumber(comparison.adjusted_p_value)}</td><td>{comparison.reject_adjusted ? "차이 신호" : "차이 근거 부족"}</td></tr>)}</tbody></table></div> : null}
  </>;
}

function posthocDescription(method: string): string {
  if (method === "tukey_kramer") return "모든 그룹 쌍의 평균을 비교하고 family-wise error를 제어합니다.";
  if (method === "dunnett") return "선택한 기준 그룹과 나머지 그룹의 평균을 비교합니다.";
  if (method === "games_howell") return "등분산을 가정하지 않고 모든 그룹 쌍을 비교합니다.";
  return "그룹별 요약과 전체 검정만 계산합니다.";
}

function posthocMethodLabel(method: string): string {
  return { tukey_kramer: "Tukey-Kramer", dunnett: "Dunnett", games_howell: "Games-Howell", none: "없음" }[method] ?? method;
}

function formatAnalysisNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  if (Math.abs(value) >= 1000 || (Math.abs(value) > 0 && Math.abs(value) < 0.001)) return value.toExponential(3);
  return value.toLocaleString(undefined, { maximumFractionDigits: 6 });
}
