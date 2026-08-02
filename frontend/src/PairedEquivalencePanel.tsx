import type { AnalysisResultEnvelope, DatasetColumnResponse, DatasetVersionResponse, EquivalenceTostResult } from "./api";
import { EquivalenceResultView } from "./EquivalenceResultView";

interface Props {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  lowerBound: number;
  methodId: string;
  referenceColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: EquivalenceTostResult | null;
  testColumnId: string | null;
  upperBound: number;
  version: DatasetVersionResponse | null;
  onAlphaChange: (value: number) => void;
  onLowerBoundChange: (value: number) => void;
  onReferenceColumnChange: (value: string) => void;
  onRun: () => void;
  onTestColumnChange: (value: string) => void;
  onUpperBoundChange: (value: number) => void;
}

export function PairedEquivalencePanel(props: Props) {
  const canRun = props.version !== null && props.testColumnId !== null && props.referenceColumnId !== null &&
    props.testColumnId !== props.referenceColumnId && props.lowerBound < props.upperBound && props.alpha > 0 &&
    props.alpha < 0.5 && props.filterValidationError === null;
  return (
    <section className="analysis-run-panel" data-analysis-execution={props.methodId}>
      {props.version === null ? <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div> : <>
        <div className="option-grid">
          <ColumnField label="시험 측정" value={props.testColumnId ?? ""} columns={props.responseColumns} onChange={props.onTestColumnChange} />
          <ColumnField label="기준 측정" value={props.referenceColumnId ?? ""} columns={props.responseColumns} onChange={props.onReferenceColumnChange} />
          <NumberField label="동등성 하한" value={props.lowerBound} onChange={props.onLowerBoundChange} />
          <NumberField label="동등성 상한" value={props.upperBound} onChange={props.onUpperBoundChange} />
          <NumberField label="유의수준 alpha" value={props.alpha} onChange={props.onAlphaChange} />
          <div className="readonly-field"><span>차이 정의</span><strong>시험 측정 - 기준 측정</strong></div>
        </div>
        <p className="help-text">두 컬럼이 모두 유효한 행만 complete pair로 사용합니다. 두 단측검정이 모두 기각되어야 동등성 근거가 있습니다.</p>
        <button className="primary-button" disabled={props.isRunningAnalysis || !canRun} onClick={props.onRun} type="button">{props.isRunningAnalysis ? "실행 중" : "대응표본 동등성 검정 실행"}</button>
        <EquivalenceResultView analysisResult={props.analysisResult} result={props.result} />
      </>}
    </section>
  );
}

function ColumnField({ label, value, columns, onChange }: { label: string; value: string; columns: DatasetColumnResponse[]; onChange: (value: string) => void }) {
  return <label><span>{label}</span><select value={value} onChange={(event) => onChange(event.currentTarget.value)}><option value="">선택</option>{columns.map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}</select></label>;
}
function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <label><span>{label}</span><input step="any" type="number" value={value} onChange={(event) => onChange(Number(event.currentTarget.value))} /></label>;
}
