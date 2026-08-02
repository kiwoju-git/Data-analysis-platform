import { useEffect, useMemo, useState } from "react";

import {
  fetchDatasetGroupLevels,
  type AnalysisResultEnvelope,
  type DatasetColumnResponse,
  type DatasetVersionResponse,
  type EquivalenceTostResult,
  type GroupLevelPreflightItem,
} from "./api";
import { serializeAnalysisFilterDrafts, type AnalysisFilterDraft } from "./analysisFilters";
import { EquivalenceResultView } from "./EquivalenceResultView";

export interface TwoSampleEquivalenceExecutionOptions {
  testGroupLabel: string;
  referenceGroupLabel: string;
  varianceAssumption: "welch" | "pooled";
}

interface Props {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  filterDrafts: AnalysisFilterDraft[];
  filterValidationError: string | null;
  groupColumnId: string | null;
  groupColumns: DatasetColumnResponse[];
  isRunningAnalysis: boolean;
  lowerBound: number;
  methodId: string;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: EquivalenceTostResult | null;
  upperBound: number;
  varianceAssumption: string;
  version: DatasetVersionResponse | null;
  onAlphaChange: (value: number) => void;
  onGroupColumnChange: (value: string) => void;
  onLowerBoundChange: (value: number) => void;
  onResponseColumnChange: (value: string) => void;
  onRun: (options: TwoSampleEquivalenceExecutionOptions) => void;
  onUpperBoundChange: (value: number) => void;
  onVarianceAssumptionChange: (value: string) => void;
}

export function TwoSampleEquivalencePanel(props: Props) {
  const [levels, setLevels] = useState<GroupLevelPreflightItem[]>([]);
  const [testGroup, setTestGroup] = useState("");
  const [referenceGroup, setReferenceGroup] = useState("");
  const [levelError, setLevelError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const filterSnapshot = useMemo(() => {
    if (props.version === null || props.filterValidationError !== null) return null;
    return { expression_version: 1 as const, conditions: serializeAnalysisFilterDrafts(props.filterDrafts, props.version.columns) };
  }, [props.filterDrafts, props.filterValidationError, props.version]);

  useEffect(() => {
    setLevels([]);
    setTestGroup("");
    setReferenceGroup("");
    setLevelError(null);
    if (props.version === null || props.groupColumnId === null || filterSnapshot === null) return;
    let cancelled = false;
    setLoading(true);
    void fetchDatasetGroupLevels(props.version.version_id, {
      group_column_id: props.groupColumnId,
      filter_snapshot: filterSnapshot,
      maximum_levels: 3,
    }).then((response) => {
      if (cancelled) return;
      setLevels(response.levels);
      if (response.truncated || response.levels.length !== 2) {
        setLevelError("독립 2-표본 동등성 검정은 정확히 2개 그룹이 필요합니다.");
        return;
      }
      setTestGroup(response.levels[0].value);
      setReferenceGroup(response.levels[1].value);
    }).catch((error: unknown) => {
      if (!cancelled) setLevelError(error instanceof Error ? error.message : "group_level_preflight_failed");
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filterSnapshot, props.groupColumnId, props.version]);

  const variance = props.varianceAssumption === "pooled" ? "pooled" : "welch";
  const canRun = props.version !== null && props.responseColumnId !== null && props.groupColumnId !== null &&
    props.responseColumnId !== props.groupColumnId && testGroup.length > 0 && referenceGroup.length > 0 &&
    testGroup !== referenceGroup && props.lowerBound < props.upperBound && props.alpha > 0 && props.alpha < 0.5 &&
    props.filterValidationError === null && levelError === null && !loading;

  return (
    <section className="analysis-run-panel" data-analysis-execution={props.methodId}>
      {props.version === null ? <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div> : <>
        <div className="option-grid">
          <SelectField label="반응 변수" value={props.responseColumnId ?? ""} columns={props.responseColumns} onChange={props.onResponseColumnChange} />
          <SelectField label="그룹 변수" value={props.groupColumnId ?? ""} columns={props.groupColumns} onChange={props.onGroupColumnChange} />
          <label><span>시험 그룹</span><select aria-label="시험 그룹" disabled={loading || levels.length !== 2} value={testGroup} onChange={(event) => setTestGroup(event.currentTarget.value)}><option value="">선택</option>{levels.map((level) => <option key={level.value} value={level.value}>{level.display_label} (N {level.n_used})</option>)}</select></label>
          <label><span>기준 그룹</span><select aria-label="기준 그룹" disabled={loading || levels.length !== 2} value={referenceGroup} onChange={(event) => setReferenceGroup(event.currentTarget.value)}><option value="">선택</option>{levels.map((level) => <option key={level.value} value={level.value}>{level.display_label} (N {level.n_used})</option>)}</select></label>
          <label><span>분산 가정</span><select aria-label="분산 가정" value={variance} onChange={(event) => props.onVarianceAssumptionChange(event.currentTarget.value)}><option value="welch">등분산 가정 안 함 (Welch)</option><option value="pooled">등분산 가정 (pooled)</option></select></label>
          <NumberField label="동등성 하한" value={props.lowerBound} onChange={props.onLowerBoundChange} />
          <NumberField label="동등성 상한" value={props.upperBound} onChange={props.onUpperBoundChange} />
          <NumberField label="유의수준 alpha" value={props.alpha} onChange={props.onAlphaChange} />
        </div>
        <p className="help-text">평균 차이는 시험 그룹 - 기준 그룹으로 계산합니다. 두 단측검정이 모두 기각되어야 동등성 근거가 있습니다.</p>
        {loading ? <div className="notice-box">그룹 수준을 확인하고 있습니다.</div> : null}
        {levelError ? <div className="error-box">{levelError}</div> : null}
        <button className="primary-button" disabled={props.isRunningAnalysis || !canRun} onClick={() => props.onRun({ testGroupLabel: testGroup, referenceGroupLabel: referenceGroup, varianceAssumption: variance })} type="button">{props.isRunningAnalysis ? "실행 중" : "2-표본 동등성 검정 실행"}</button>
        <EquivalenceResultView analysisResult={props.analysisResult} result={props.result} />
      </>}
    </section>
  );
}

function SelectField({ label, value, columns, onChange }: { label: string; value: string; columns: DatasetColumnResponse[]; onChange: (value: string) => void }) {
  return <label><span>{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(event.currentTarget.value)}><option value="">선택</option>{columns.map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}</select></label>;
}
function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <label><span>{label}</span><input step="any" type="number" value={value} onChange={(event) => onChange(Number(event.currentTarget.value))} /></label>;
}
