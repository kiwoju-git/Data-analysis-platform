import { useEffect, useMemo, useRef, useState } from "react";

import {
  createDoeResponseRevision,
  createResponseSurfaceAnalysis,
  createResponseSurfaceDesign,
  fetchDoeResponseRevisions,
  saveResponseSurfaceResponses,
  type DoeResponseRevisionHistoryResponse,
  type DoeResponseSurfaceAnalysisResponse,
  type ResponseSurfaceDesignCreateRequest,
  type ResponseSurfaceDesignResponse,
} from "./api";
import { ResponseOptimizerPanel } from "./ResponseOptimizerPanel";

interface FactorDraft {
  id: number;
  name: string;
  low: string;
  high: string;
  unit: string;
}

const maxFactorCount = 5;

export function ResponseSurfacePanel() {
  const [name, setName] = useState("Central composite process window");
  const [factors, setFactors] = useState<FactorDraft[]>([
    { id: 1, name: "Temperature", low: "60", high: "80", unit: "C" },
    { id: 2, name: "Pressure", low: "5", high: "15", unit: "bar" },
  ]);
  const [alphaMode, setAlphaMode] = useState<"rotatable" | "face_centered">("rotatable");
  const [centerPoints, setCenterPoints] = useState("5");
  const [randomizationSeed, setRandomizationSeed] = useState("20260714");
  const [randomize, setRandomize] = useState(true);
  const [design, setDesign] = useState<ResponseSurfaceDesignResponse | null>(null);
  const [responseName, setResponseName] = useState("Yield");
  const [responseUnit, setResponseUnit] = useState("");
  const [responseValues, setResponseValues] = useState<Record<number, string>>({});
  const [responsesSaved, setResponsesSaved] = useState(false);
  const [responseRevisionId, setResponseRevisionId] = useState<string | null>(null);
  const [responseRevisionNumber, setResponseRevisionNumber] = useState<number | null>(null);
  const [responseRevisionSha256, setResponseRevisionSha256] = useState<string | null>(null);
  const [revisionHistory, setRevisionHistory] =
    useState<DoeResponseRevisionHistoryResponse | null>(null);
  const [correctionMode, setCorrectionMode] = useState(false);
  const [analysis, setAnalysis] = useState<DoeResponseSurfaceAnalysisResponse | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestRevision = useRef(0);
  const nextFactorId = useRef(3);

  useEffect(
    () => () => {
      requestRevision.current += 1;
    },
    [],
  );

  const estimatedRunCount = useMemo(() => {
    const center = Number.parseInt(centerPoints, 10);
    return Number.isInteger(center) ? 2 ** factors.length + 2 * factors.length + center : 0;
  }, [centerPoints, factors.length]);

  const createDesign = async () => {
    const request = designRequest({
      name,
      factors,
      alphaMode,
      centerPoints,
      randomize,
      randomizationSeed,
    });
    if (typeof request === "string") {
      setError(request);
      return;
    }
    const revision = ++requestRevision.current;
    setIsCreating(true);
    setError(null);
    try {
      const created = await createResponseSurfaceDesign(request);
      if (requestRevision.current !== revision) return;
      setDesign(created);
      setIsSaving(false);
      setIsAnalyzing(false);
      setResponsesSaved(false);
      setAnalysis(null);
      setResponseRevisionId(null);
      setResponseRevisionNumber(null);
      setResponseRevisionSha256(null);
      setRevisionHistory(null);
      setCorrectionMode(false);
      setResponseValues(Object.fromEntries(created.runs.map((run) => [run.run_order, ""])));
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsCreating(false);
    }
  };

  const saveResponses = async () => {
    if (design === null) return;
    const trimmedName = responseName.trim();
    if (trimmedName.length === 0) {
      setError("doe_rsm_response_name_required");
      return;
    }
    const values = design.runs.map((run) => ({
      run_order: run.run_order,
      value: Number(responseValues[run.run_order]),
    }));
    if (values.some((value) => !Number.isFinite(value.value))) {
      setError("doe_rsm_response_values_required");
      return;
    }
    const revision = ++requestRevision.current;
    setIsSaving(true);
    setError(null);
    try {
      const stored = correctionMode
        ? await createDoeResponseRevision(design.design_id, {
            response_name: trimmedName,
            unit: responseUnit.trim() || null,
            values,
            supersedes_response_revision_id: responseRevisionId,
          })
        : await saveResponseSurfaceResponses(design.design_id, {
            response_name: trimmedName,
            unit: responseUnit.trim() || null,
            values,
          });
      if (requestRevision.current !== revision) return;
      setResponsesSaved(true);
      setAnalysis(null);
      setCorrectionMode(false);
      if ("response_revision_id" in stored) {
        setResponseRevisionId(stored.response_revision_id);
        setResponseRevisionNumber(stored.revision_number);
        setResponseRevisionSha256(stored.response_revision_sha256);
        setDesign((current) => (current === null ? null : { ...current, status: "completed" }));
      } else {
        const current = stored.responses.find((item) => item.response_name === trimmedName) ?? null;
        setResponseRevisionId(current?.response_revision_id ?? null);
        setResponseRevisionNumber(current?.response_revision_number ?? null);
        setResponseRevisionSha256(current?.response_revision_sha256 ?? null);
        setDesign((value) => (value === null ? null : { ...value, status: stored.status }));
      }
      const history = await fetchDoeResponseRevisions(design.design_id, trimmedName);
      if (requestRevision.current === revision) setRevisionHistory(history);
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsSaving(false);
    }
  };

  const runAnalysis = async () => {
    if (design === null || !responsesSaved) return;
    const revision = ++requestRevision.current;
    setIsAnalyzing(true);
    setError(null);
    try {
      const created = await createResponseSurfaceAnalysis(design.design_id, {
        response_name: responseName.trim(),
        response_revision_id: responseRevisionId,
        confidence_level: 0.95,
        point_limit: 256,
        contour_grid_size: 21,
      });
      if (requestRevision.current !== revision) return;
      setAnalysis(created);
      setDesign((current) => (current === null ? null : { ...current, status: "analyzed" }));
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsAnalyzing(false);
    }
  };

  return (
    <section className="analysis-run-panel" aria-labelledby="response-surface-title">
      <div className="panel-heading">
        <div>
          <h3 id="response-surface-title">반응표면법</h3>
          <p>doe.response_surface</p>
        </div>
        <span className="status-pill status-ready">전용 API</span>
      </div>

      <div className="option-grid">
        <label>
          <span>설계 이름</span>
          <input value={name} onChange={(event) => setName(event.currentTarget.value)} />
        </label>
        <label>
          <span>CCD 방식</span>
          <select
            value={alphaMode}
            onChange={(event) =>
              setAlphaMode(event.currentTarget.value as "rotatable" | "face_centered")
            }
          >
            <option value="rotatable">Rotatable CCI</option>
            <option value="face_centered">Face-centered CCD</option>
          </select>
        </label>
        <label>
          <span>센터점</span>
          <input
            inputMode="numeric"
            value={centerPoints}
            onChange={(event) => setCenterPoints(event.currentTarget.value)}
          />
        </label>
        <label>
          <span>Randomization seed</span>
          <input
            inputMode="numeric"
            value={randomizationSeed}
            onChange={(event) => setRandomizationSeed(event.currentTarget.value)}
          />
        </label>
        <label className="inline-option">
          <span>실행 순서 무작위화</span>
          <input
            type="checkbox"
            checked={randomize}
            onChange={(event) => setRandomize(event.currentTarget.checked)}
          />
        </label>
      </div>

      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>요인</th>
              <th>설계 하한</th>
              <th>설계 상한</th>
              <th>단위</th>
              <th>제거</th>
            </tr>
          </thead>
          <tbody>
            {factors.map((factor, index) => (
              <tr key={factor.id}>
                <td>
                  <input
                    aria-label={`요인 ${index + 1} 이름`}
                    value={factor.name}
                    onChange={(event) =>
                      updateFactor(setFactors, factor.id, "name", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `요인 ${index + 1}`} 하한`}
                    inputMode="decimal"
                    value={factor.low}
                    onChange={(event) =>
                      updateFactor(setFactors, factor.id, "low", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `요인 ${index + 1}`} 상한`}
                    inputMode="decimal"
                    value={factor.high}
                    onChange={(event) =>
                      updateFactor(setFactors, factor.id, "high", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `요인 ${index + 1}`} 단위`}
                    value={factor.unit}
                    onChange={(event) =>
                      updateFactor(setFactors, factor.id, "unit", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={factors.length <= 2}
                    onClick={() => setFactors((current) => current.filter((item) => item.id !== factor.id))}
                  >
                    제거
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="button-row">
        <button
          type="button"
          className="secondary-button"
          disabled={factors.length >= maxFactorCount}
          onClick={() => {
            const id = nextFactorId.current++;
            setFactors((current) => [
              ...current,
              { id, name: `Factor ${id}`, low: "-1", high: "1", unit: "" },
            ]);
          }}
        >
          요인 추가
        </button>
        <button
          type="button"
          className="primary-button"
          disabled={isCreating}
          onClick={() => void createDesign()}
        >
          {isCreating ? "생성 중" : "CCD 생성"}
        </button>
      </div>
      <div className="metadata-grid" aria-label="반응표면 설계 입력 요약">
        <span>예상 run</span>
        <strong>{estimatedRunCount}</strong>
        <span>요인 수</span>
        <strong>{factors.length}</strong>
        <span>모형 정책</span>
        <strong>Full quadratic, no automatic selection</strong>
      </div>
      {error !== null ? <div className="error-box">오류 코드: {error}</div> : null}

      {design !== null ? (
        <ResponseSurfaceResponseEntry
          design={design}
          responseName={responseName}
          responseUnit={responseUnit}
          responseValues={responseValues}
          responsesSaved={responsesSaved}
          responseRevisionNumber={responseRevisionNumber}
          responseRevisionSha256={responseRevisionSha256}
          revisionHistory={revisionHistory}
          correctionMode={correctionMode}
          isSaving={isSaving}
          isAnalyzing={isAnalyzing}
          onResponseNameChange={(value) => {
            setResponseName(value);
            setResponsesSaved(false);
          }}
          onResponseUnitChange={setResponseUnit}
          onResponseValueChange={(runOrder, value) => {
            setResponsesSaved(false);
            setResponseValues((current) => ({ ...current, [runOrder]: value }));
          }}
          onStartCorrection={() => {
            setCorrectionMode(true);
            setError(null);
            const revision = ++requestRevision.current;
            if (responseName.trim().length > 0) {
              void fetchDoeResponseRevisions(design.design_id, responseName.trim())
                .then((history) => {
                  if (requestRevision.current === revision) setRevisionHistory(history);
                })
                .catch((caught: unknown) => {
                  if (requestRevision.current === revision) setError(errorCode(caught));
                });
            }
          }}
          onSave={() => void saveResponses()}
          onAnalyze={() => void runAnalysis()}
        />
      ) : null}
      {analysis !== null && design !== null ? (
        <>
          <ResponseSurfaceResult analysis={analysis} />
          <ResponseOptimizerPanel design={design} analysis={analysis} />
        </>
      ) : null}
    </section>
  );
}

interface ResponseEntryProps {
  design: ResponseSurfaceDesignResponse;
  responseName: string;
  responseUnit: string;
  responseValues: Record<number, string>;
  responsesSaved: boolean;
  responseRevisionNumber: number | null;
  responseRevisionSha256: string | null;
  revisionHistory: DoeResponseRevisionHistoryResponse | null;
  correctionMode: boolean;
  isSaving: boolean;
  isAnalyzing: boolean;
  onResponseNameChange: (value: string) => void;
  onResponseUnitChange: (value: string) => void;
  onResponseValueChange: (runOrder: number, value: string) => void;
  onStartCorrection: () => void;
  onSave: () => void;
  onAnalyze: () => void;
}

export function ResponseSurfaceResponseEntry({
  design,
  responseName,
  responseUnit,
  responseValues,
  responsesSaved,
  responseRevisionNumber,
  responseRevisionSha256,
  revisionHistory,
  correctionMode,
  isSaving,
  isAnalyzing,
  onResponseNameChange,
  onResponseUnitChange,
  onResponseValueChange,
  onStartCorrection,
  onSave,
  onAnalyze,
}: ResponseEntryProps) {
  const responsesLocked = design.status === "analyzed" && !correctionMode;
  return (
    <section className="analysis-result-section" aria-labelledby="rsm-response-title">
      <div className="panel-heading compact-heading">
        <div>
          <h4 id="rsm-response-title">CCD 실행표와 반응 입력</h4>
          <p>{design.name}</p>
        </div>
        <span className="status-pill status-ready">{design.status}</span>
      </div>
      <div className="metadata-grid" aria-label="CCD 설계 요약">
        <span>Run</span>
        <strong>{design.run_count}</strong>
        <span>Axial distance</span>
        <strong>{formatNumber(design.options.alpha)}</strong>
        <span>설계 경계</span>
        <strong>Axial points = declared low/high</strong>
        <span>Response revision</span>
        <strong>{responseRevisionNumber === null ? "-" : `r${responseRevisionNumber}`}</strong>
        <span>Revision SHA</span>
        <strong>{responseRevisionSha256?.slice(0, 12) ?? "-"}</strong>
      </div>
      <div className="option-grid">
        <label>
          <span>반응 이름</span>
          <input
            disabled={responsesLocked || correctionMode}
            value={responseName}
            onChange={(event) => onResponseNameChange(event.currentTarget.value)}
          />
        </label>
        <label>
          <span>반응 단위</span>
          <input
            disabled={responsesLocked}
            value={responseUnit}
            onChange={(event) => onResponseUnitChange(event.currentTarget.value)}
          />
        </label>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Point</th>
              {design.factors.map((factor) => (
                <th key={factor.name}>{factor.name}</th>
              ))}
              <th>반응</th>
            </tr>
          </thead>
          <tbody>
            {design.runs.map((run) => (
              <tr key={run.run_order}>
                <td>{run.run_order}</td>
                <td>{run.point_type}</td>
                {design.factors.map((factor) => (
                  <td key={factor.name}>{formatNumber(run.factor_levels[factor.name])}</td>
                ))}
                <td>
                  <input
                    aria-label={`Run ${run.run_order} 반응`}
                    disabled={responsesLocked}
                    inputMode="decimal"
                    value={responseValues[run.run_order] ?? ""}
                    onChange={(event) => onResponseValueChange(run.run_order, event.currentTarget.value)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {responsesLocked ? (
        <div className="notice-box notice-warning" role="status">
          분석이 완료되어 현재 revision은 읽기 전용입니다. 수정은 새 revision으로만 저장되며 과거 분석은 유지됩니다.
        </div>
      ) : correctionMode ? (
        <div className="notice-box notice-warning" role="status">
          새 revision을 편집 중입니다. 저장 전 기존 revision과 분석 결과는 변경되지 않습니다.
        </div>
      ) : (
        <div className="notice-box notice-warning">
          분석을 실행하면 현재 설계의 반응값이 잠깁니다. 여러 response를 사용할 계획이면 먼저 모두 저장하세요.
        </div>
      )}
      <div className="button-row">
        <button
          type="button"
          className="secondary-button"
          disabled={isSaving || responsesLocked}
          onClick={onSave}
        >
          {isSaving ? "저장 중" : correctionMode ? "새 revision 저장" : "반응 저장"}
        </button>
        {design.status === "analyzed" && !correctionMode ? (
          <button type="button" className="secondary-button" onClick={onStartCorrection}>
            새 revision으로 수정
          </button>
        ) : null}
        <button
          type="button"
          className="primary-button"
          disabled={!responsesSaved || isAnalyzing || responsesLocked}
          onClick={onAnalyze}
        >
          {isAnalyzing ? "분석 중" : "Quadratic model 적합"}
        </button>
      </div>
      {revisionHistory !== null ? (
        <div className="table-wrap" aria-label="RSM response revision history">
          <table className="result-table">
            <thead>
              <tr>
                <th>Revision</th>
                <th>State</th>
                <th>Current</th>
                <th>Closed</th>
                <th>SHA</th>
              </tr>
            </thead>
            <tbody>
              {revisionHistory.items.map((revision) => (
                <tr key={revision.response_revision_id}>
                  <td>r{revision.revision_number}</td>
                  <td>{revision.state}</td>
                  <td>{revision.is_current ? "current" : "history"}</td>
                  <td>{revision.closed_at ?? "-"}</td>
                  <td>{revision.response_revision_sha256.slice(0, 12)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function ResponseSurfaceResult({ analysis }: { analysis: DoeResponseSurfaceAnalysisResponse }) {
  const { result } = analysis;
  const stationary = result.stationary_point;
  return (
    <section className="analysis-result-section" aria-labelledby="rsm-result-title">
      <div className="panel-heading compact-heading">
        <div>
          <h4 id="rsm-result-title">Quadratic response surface</h4>
          <p>{analysis.method_id} v{analysis.method_version}</p>
        </div>
        <span className="status-pill status-ready">검증 저장됨</span>
      </div>
      <div className="metadata-grid" aria-label="반응표면 적합 요약">
        <span>N / residual df</span>
        <strong>{result.sample.n_observations} / {result.sample.df_residual}</strong>
        <span>R² / adjusted R²</span>
        <strong>{formatNumber(result.fit.r_squared)} / {formatNullable(result.fit.adjusted_r_squared)}</strong>
        <span>Residual SE</span>
        <strong>{formatNullable(result.fit.residual_standard_error)}</strong>
        <span>Stationary point</span>
        <strong>{stationary.classification}</strong>
        <span>설계영역 내부</span>
        <strong>{stationary.within_axial_bounds ? "예" : "아니오"}</strong>
        <span>예측 반응</span>
        <strong>{formatNullable(stationary.predicted_response)}</strong>
        <span>Response revision</span>
        <strong>r{analysis.response_revision_number}</strong>
      </div>
      {stationary.available ? (
        <div className="metadata-grid" aria-label="정상점 좌표">
          {Object.entries(stationary.actual_coordinates).map(([factor, value]) => (
            <span key={factor} className="metadata-pair">
              <span>{factor}</span>
              <strong>{formatNumber(value)}</strong>
            </span>
          ))}
        </div>
      ) : null}
      <div className="chart-panel">
        <span className="chart-panel-title">예측 contour</span>
        <ContourPlot analysis={analysis} />
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>항</th>
              <th>종류</th>
              <th>계수</th>
              <th>표준오차</th>
              <th>p-value</th>
              <th>Partial SS</th>
            </tr>
          </thead>
          <tbody>
            {result.terms.map((term) => (
              <tr key={term.term_id}>
                <td>{term.label}</td>
                <td>{term.kind}</td>
                <td>{formatNumber(term.coefficient)}</td>
                <td>{formatNullable(term.standard_error)}</td>
                <td>{formatNullable(term.p_value)}</td>
                <td>{formatNullable(term.partial_sum_squares)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="metadata-grid" aria-label="반응표면 진단 요약">
        <span>Lack-of-fit p</span>
        <strong>{formatNullable(result.anova.lack_of_fit.lack_of_fit.p_value)}</strong>
        <span>Shapiro-Wilk p</span>
        <strong>{formatNullable(result.diagnostics.shapiro_wilk.p_value)}</strong>
        <span>High leverage</span>
        <strong>{result.diagnostics.high_leverage_count}</strong>
        <span>High Cook's distance</span>
        <strong>{result.diagnostics.high_cooks_distance_count}</strong>
      </div>
      {result.warnings.map((warning) => (
        <div className="notice-box notice-warning" key={warning}>{warning}</div>
      ))}
    </section>
  );
}

function ContourPlot({ analysis }: { analysis: DoeResponseSurfaceAnalysisResponse }) {
  const { contour } = analysis.result;
  const width = 540;
  const height = 380;
  const left = 64;
  const top = 20;
  const plotSize = 300;
  const cellSize = plotSize / contour.grid_size;
  const values = contour.points.map((point) => point.predicted);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  return (
    <svg
      className="chart-svg chart-svg-wide"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${contour.x_factor}와 ${contour.y_factor}의 예측 반응 contour`}
    >
      {contour.points.map((point, index) => {
        const column = index % contour.grid_size;
        const row = Math.floor(index / contour.grid_size);
        return (
          <rect
            key={`${point.x_coded}:${point.y_coded}`}
            x={left + column * cellSize}
            y={top + (contour.grid_size - row - 1) * cellSize}
            width={cellSize + 0.4}
            height={cellSize + 0.4}
            fill={contourColor(point.predicted, minimum, maximum)}
          >
            <title>{formatNumber(point.predicted)}</title>
          </rect>
        );
      })}
      <line className="chart-axis" x1={left} x2={left + plotSize} y1={top + plotSize} y2={top + plotSize} />
      <line className="chart-axis" x1={left} x2={left} y1={top} y2={top + plotSize} />
      <text className="chart-axis-label" x={left + plotSize / 2 - 20} y={top + plotSize + 32}>{contour.x_factor}</text>
      <text className="chart-axis-label" x={8} y={top + plotSize / 2}>{contour.y_factor}</text>
      <text className="chart-axis-label" x={left} y={top + plotSize + 16}>-1</text>
      <text className="chart-axis-label chart-axis-label-end" x={left + plotSize} y={top + plotSize + 16}>+1</text>
      <text className="chart-axis-label" x={left + plotSize + 24} y={top + 20}>최대 {formatNumber(maximum)}</text>
      <text className="chart-axis-label" x={left + plotSize + 24} y={top + 42}>최소 {formatNumber(minimum)}</text>
    </svg>
  );
}

function designRequest(input: {
  name: string;
  factors: FactorDraft[];
  alphaMode: "rotatable" | "face_centered";
  centerPoints: string;
  randomize: boolean;
  randomizationSeed: string;
}): ResponseSurfaceDesignCreateRequest | string {
  const centerPoints = Number.parseInt(input.centerPoints, 10);
  const seed = Number.parseInt(input.randomizationSeed, 10);
  if (!Number.isInteger(centerPoints) || centerPoints < 1 || centerPoints > 32) {
    return "doe_rsm_center_points_invalid";
  }
  if (!Number.isInteger(seed) || seed < 0) return "doe_rsm_seed_invalid";
  const names = input.factors.map((factor) => factor.name.trim().toLocaleLowerCase());
  if (names.some((name) => name.length === 0) || new Set(names).size !== names.length) {
    return "doe_rsm_factor_names_not_unique";
  }
  const factors = input.factors.map((factor) => ({
    name: factor.name.trim(),
    low: Number(factor.low),
    high: Number(factor.high),
    unit: factor.unit.trim() || null,
  }));
  if (factors.some((factor) => !Number.isFinite(factor.low) || !Number.isFinite(factor.high) || factor.low >= factor.high)) {
    return "doe_rsm_factor_range_invalid";
  }
  return {
    name: input.name.trim() || "Central composite design",
    factors,
    alpha_mode: input.alphaMode,
    factorial_replicates: 1,
    axial_replicates: 1,
    center_points: centerPoints,
    randomize: input.randomize,
    randomization_seed: seed,
  };
}

function updateFactor(
  setter: React.Dispatch<React.SetStateAction<FactorDraft[]>>,
  id: number,
  key: keyof Omit<FactorDraft, "id">,
  value: string,
) {
  setter((current) => current.map((factor) => (factor.id === id ? { ...factor, [key]: value } : factor)));
}

function errorCode(error: unknown): string {
  return error instanceof Error ? error.message : "doe_rsm_unknown_error";
}

function formatNumber(value: number): string {
  return Number.isFinite(value) ? value.toPrecision(6).replace(/\.?0+$/, "") : "-";
}

function formatNullable(value: number | null): string {
  return value === null ? "-" : formatNumber(value);
}

function contourColor(value: number, minimum: number, maximum: number): string {
  const ratio = maximum === minimum ? 0.5 : (value - minimum) / (maximum - minimum);
  if (ratio <= 0.5) {
    const amount = ratio * 2;
    return mixColor([34, 117, 111], [245, 240, 204], amount);
  }
  return mixColor([245, 240, 204], [181, 61, 52], (ratio - 0.5) * 2);
}

function mixColor(start: [number, number, number], end: [number, number, number], amount: number): string {
  const channels = start.map((value, index) => Math.round(value + (end[index] - value) * amount));
  return `rgb(${channels.join(",")})`;
}
