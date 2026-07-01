import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";

import type {
  DoeDesignResponsesResponse,
  DoeDesignResponsesUpsertRequest,
  FactorialDesignCreateRequest,
  FactorialDesignResponse,
} from "./api";

interface FactorDraft {
  id: string;
  name: string;
  low: string;
  high: string;
  unit: string;
}

interface FactorialDesignPanelProps {
  design: FactorialDesignResponse | null;
  error: string | null;
  isCreating: boolean;
  isSavingResponses: boolean;
  methodId: string;
  onCreateDesign: (request: FactorialDesignCreateRequest) => void;
  onSaveResponses: (designId: string, request: DoeDesignResponsesUpsertRequest) => void;
  responseError: string | null;
  responses: DoeDesignResponsesResponse | null;
}

interface ValidationResult {
  kind: "ready" | "error";
  message: string | null;
  request: FactorialDesignCreateRequest | null;
  runCount: number;
}

interface ResponseValidationResult {
  kind: "ready" | "error";
  message: string | null;
  request: DoeDesignResponsesUpsertRequest | null;
}

const maxFactorCount = 6;
const maxRunCount = 256;

export function FactorialDesignPanel({
  design,
  error,
  isCreating,
  isSavingResponses,
  methodId,
  onCreateDesign,
  onSaveResponses,
  responseError,
  responses,
}: FactorialDesignPanelProps) {
  const [name, setName] = useState("2-level screening design");
  const [factors, setFactors] = useState<FactorDraft[]>([
    { id: "factor-1", name: "Temperature", low: "60", high: "80", unit: "C" },
    { id: "factor-2", name: "Pressure", low: "5", high: "15", unit: "bar" },
  ]);
  const [replicates, setReplicates] = useState("1");
  const [centerPoints, setCenterPoints] = useState("1");
  const [randomize, setRandomize] = useState(true);
  const [randomizationSeed, setRandomizationSeed] = useState("20260702");
  const [blockCount, setBlockCount] = useState("1");
  const validation = useMemo(
    () =>
      validateFactorialDesignDraft({
        name,
        factors,
        replicates,
        centerPoints,
        randomize,
        randomizationSeed,
        blockCount,
      }),
    [blockCount, centerPoints, factors, name, randomizationSeed, randomize, replicates],
  );

  return (
    <section className="analysis-run-panel" aria-labelledby="factorial-design-title">
      <div className="panel-heading">
        <div>
          <h3 id="factorial-design-title">2-level full factorial 설계 생성</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      <div className="option-grid">
        <label>
          <span>설계 이름</span>
          <input
            value={name}
            onChange={(event) => {
              setName(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>반복</span>
          <input
            inputMode="numeric"
            value={replicates}
            onChange={(event) => {
              setReplicates(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>센터점</span>
          <input
            inputMode="numeric"
            value={centerPoints}
            onChange={(event) => {
              setCenterPoints(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>Seed</span>
          <input
            inputMode="numeric"
            value={randomizationSeed}
            onChange={(event) => {
              setRandomizationSeed(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>Block</span>
          <input
            inputMode="numeric"
            value={blockCount}
            onChange={(event) => {
              setBlockCount(event.currentTarget.value);
            }}
          />
        </label>
        <label className="inline-option">
          <input
            checked={randomize}
            type="checkbox"
            onChange={(event) => {
              setRandomize(event.currentTarget.checked);
            }}
          />
          <span>랜덤화</span>
        </label>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>요인</th>
              <th>Low</th>
              <th>High</th>
              <th>Unit</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {factors.map((factor, index) => (
              <tr key={factor.id}>
                <td>
                  <input
                    aria-label={`factor ${index + 1} name`}
                    value={factor.name}
                    onChange={(event) => {
                      updateFactor(factor.id, "name", event.currentTarget.value, setFactors);
                    }}
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `factor ${index + 1}`} low`}
                    inputMode="decimal"
                    value={factor.low}
                    onChange={(event) => {
                      updateFactor(factor.id, "low", event.currentTarget.value, setFactors);
                    }}
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `factor ${index + 1}`} high`}
                    inputMode="decimal"
                    value={factor.high}
                    onChange={(event) => {
                      updateFactor(factor.id, "high", event.currentTarget.value, setFactors);
                    }}
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `factor ${index + 1}`} unit`}
                    value={factor.unit}
                    onChange={(event) => {
                      updateFactor(factor.id, "unit", event.currentTarget.value, setFactors);
                    }}
                  />
                </td>
                <td>
                  <button
                    disabled={factors.length <= 2}
                    onClick={() => {
                      setFactors((current) => current.filter((item) => item.id !== factor.id));
                    }}
                    type="button"
                  >
                    삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="button-row">
        <button
          disabled={factors.length >= maxFactorCount}
          onClick={() => {
            setFactors((current) => [
              ...current,
              {
                id: `factor-${Date.now()}`,
                name: `Factor ${current.length + 1}`,
                low: "0",
                high: "1",
                unit: "",
              },
            ]);
          }}
          type="button"
        >
          요인 추가
        </button>
        <button
          className="primary-button"
          disabled={isCreating || validation.kind === "error"}
          onClick={() => {
            if (validation.request !== null) {
              onCreateDesign(validation.request);
            }
          }}
          type="button"
        >
          {isCreating ? "생성 중" : "DOE 설계 생성"}
        </button>
      </div>
      <div className="metadata-grid" aria-label="DOE 설계 입력 요약">
        <span>예상 run</span>
        <strong>{validation.runCount.toLocaleString()}</strong>
        <span>Family</span>
        <strong>two_level_full_factorial</strong>
        <span>Response</span>
        <strong>다음 slice</strong>
        <span>Analysis</span>
        <strong>효과/ANOVA 미포함</strong>
      </div>
      {validation.message !== null ? (
        <div className="notice-box notice-warning">{validation.message}</div>
      ) : null}
      {error !== null ? <div className="error-box">오류 코드: {error}</div> : null}
      {design !== null ? (
        <FactorialDesignPreview
          design={design}
          isSavingResponses={isSavingResponses}
          onSaveResponses={onSaveResponses}
          responseError={responseError}
          responses={responses}
        />
      ) : null}
    </section>
  );
}

function FactorialDesignPreview({
  design,
  isSavingResponses,
  onSaveResponses,
  responseError,
  responses,
}: {
  design: FactorialDesignResponse;
  isSavingResponses: boolean;
  onSaveResponses: (designId: string, request: DoeDesignResponsesUpsertRequest) => void;
  responseError: string | null;
  responses: DoeDesignResponsesResponse | null;
}) {
  const visibleRuns = design.runs.slice(0, 64);
  const matchingResponses = responses?.design_id === design.design_id ? responses : null;
  const firstResponse = matchingResponses?.responses[0] ?? null;
  const [responseName, setResponseName] = useState("Yield");
  const [responseUnit, setResponseUnit] = useState("");
  const [responseValues, setResponseValues] = useState<Record<number, string>>({});
  useEffect(() => {
    const nextValues: Record<number, string> = {};
    if (firstResponse !== null) {
      for (const value of firstResponse.values) {
        nextValues[value.run_order] = String(value.value);
      }
      setResponseName(firstResponse.response_name);
      setResponseUnit(firstResponse.unit ?? "");
    } else {
      for (const run of design.runs) {
        nextValues[run.run_order] = "";
      }
      setResponseName("Yield");
      setResponseUnit("");
    }
    setResponseValues(nextValues);
  }, [design.design_id, design.runs, firstResponse]);
  const responseValidation = useMemo(
    () => validateResponseDraft(design.runs, responseName, responseUnit, responseValues),
    [design.runs, responseName, responseUnit, responseValues],
  );

  return (
    <>
      <div className="metadata-grid" aria-label="DOE 설계 결과 요약">
        <span>Design</span>
        <strong>{design.name}</strong>
        <span>Version</span>
        <strong>v{design.version_number}</strong>
        <span>Status</span>
        <strong>{matchingResponses?.status ?? design.status}</strong>
        <span>Run count</span>
        <strong>{design.run_count.toLocaleString()}</strong>
        <span>SHA-256</span>
        <strong>{design.design_sha256.slice(0, 12)}</strong>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Standard</th>
              <th>Rep</th>
              <th>Block</th>
              <th>Center</th>
              {design.factors.map((factor) => (
                <th key={factor.name}>{factor.name}</th>
              ))}
              <th>Coded</th>
            </tr>
          </thead>
          <tbody>
            {visibleRuns.map((run) => (
              <tr key={run.run_order}>
                <td>{run.run_order}</td>
                <td>{run.standard_order}</td>
                <td>{run.replicate_index}</td>
                <td>{run.block_index ?? "-"}</td>
                <td>{run.center_point ? "yes" : "no"}</td>
                {design.factors.map((factor) => (
                  <td key={factor.name}>{formatFactorLevel(run.factor_levels[factor.name])}</td>
                ))}
                <td>{formatCodedLevels(run.coded_levels)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {design.runs.length > visibleRuns.length ? (
        <div className="notice-box">
          {visibleRuns.length.toLocaleString()} / {design.runs.length.toLocaleString()} runs 표시
        </div>
      ) : null}
      <div className="panel-heading compact-heading">
        <div>
          <h4>반응값 입력</h4>
          <p>현재 설계의 run_order 전체와 정확히 맞는 numeric response만 저장합니다.</p>
        </div>
        <span className="status-pill status-ready">
          {matchingResponses?.responses.length ? "저장됨" : "입력 대기"}
        </span>
      </div>
      <div className="option-grid">
        <label>
          <span>반응 이름</span>
          <input
            value={responseName}
            onChange={(event) => {
              setResponseName(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>단위</span>
          <input
            value={responseUnit}
            onChange={(event) => {
              setResponseUnit(event.currentTarget.value);
            }}
          />
        </label>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Standard</th>
              {design.factors.map((factor) => (
                <th key={factor.name}>{factor.name}</th>
              ))}
              <th>Response</th>
            </tr>
          </thead>
          <tbody>
            {design.runs.map((run) => (
              <tr key={run.run_order}>
                <td>{run.run_order}</td>
                <td>{run.standard_order}</td>
                {design.factors.map((factor) => (
                  <td key={factor.name}>{formatFactorLevel(run.factor_levels[factor.name])}</td>
                ))}
                <td>
                  <input
                    aria-label={`run ${run.run_order} response`}
                    inputMode="decimal"
                    value={responseValues[run.run_order] ?? ""}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      setResponseValues((current) => ({
                        ...current,
                        [run.run_order]: value,
                      }));
                    }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {responseValidation.message !== null ? (
        <div className="notice-box notice-warning">{responseValidation.message}</div>
      ) : null}
      {responseError !== null ? <div className="error-box">오류 코드: {responseError}</div> : null}
      <div className="button-row">
        <button
          className="primary-button"
          disabled={isSavingResponses || responseValidation.kind === "error"}
          onClick={() => {
            if (responseValidation.request !== null) {
              onSaveResponses(design.design_id, responseValidation.request);
            }
          }}
          type="button"
        >
          {isSavingResponses ? "저장 중" : "반응값 저장"}
        </button>
      </div>
      {matchingResponses?.responses.map((response) => (
        <div className="metadata-grid" key={response.response_name} aria-label="저장된 DOE 반응 요약">
          <span>Response</span>
          <strong>{response.response_name}</strong>
          <span>Count</span>
          <strong>{response.response_count.toLocaleString()}</strong>
          <span>Unit</span>
          <strong>{response.unit ?? "-"}</strong>
          <span>Analysis</span>
          <strong>다음 slice</strong>
        </div>
      ))}
    </>
  );
}

function updateFactor(
  factorId: string,
  field: keyof Omit<FactorDraft, "id">,
  value: string,
  setFactors: Dispatch<SetStateAction<FactorDraft[]>>,
) {
  setFactors((current) =>
    current.map((factor) => (factor.id === factorId ? { ...factor, [field]: value } : factor)),
  );
}

function validateFactorialDesignDraft({
  name,
  factors,
  replicates,
  centerPoints,
  randomize,
  randomizationSeed,
  blockCount,
}: {
  name: string;
  factors: FactorDraft[];
  replicates: string;
  centerPoints: string;
  randomize: boolean;
  randomizationSeed: string;
  blockCount: string;
}): ValidationResult {
  const trimmedName = name.trim();
  if (trimmedName.length === 0) {
    return validationError("설계 이름을 입력하세요.", 0);
  }
  if (factors.length < 2 || factors.length > maxFactorCount) {
    return validationError("요인은 2개 이상 6개 이하입니다.", 0);
  }

  const parsedFactors: FactorialDesignCreateRequest["factors"] = [];
  const names = new Set<string>();
  for (const factor of factors) {
    const factorName = factor.name.trim();
    const low = Number(factor.low);
    const high = Number(factor.high);
    if (factorName.length === 0) {
      return validationError("비어 있는 요인 이름이 있습니다.", 0);
    }
    const normalizedName = factorName.toLocaleLowerCase("ko-KR");
    if (names.has(normalizedName)) {
      return validationError("요인 이름은 중복될 수 없습니다.", 0);
    }
    names.add(normalizedName);
    if (!Number.isFinite(low) || !Number.isFinite(high) || low >= high) {
      return validationError(`${factorName}의 low/high를 확인하세요.`, 0);
    }
    parsedFactors.push({
      name: factorName,
      low,
      high,
      unit: factor.unit.trim().length > 0 ? factor.unit.trim() : null,
    });
  }

  const parsedReplicates = integerField(replicates);
  const parsedCenterPoints = integerField(centerPoints);
  const parsedSeed = integerField(randomizationSeed);
  const parsedBlockCount = integerField(blockCount);
  if (parsedReplicates === null || parsedReplicates < 1 || parsedReplicates > 16) {
    return validationError("반복 수는 1 이상 16 이하입니다.", 0);
  }
  if (parsedCenterPoints === null || parsedCenterPoints < 0 || parsedCenterPoints > 32) {
    return validationError("센터점 수는 0 이상 32 이하입니다.", 0);
  }
  if (parsedSeed === null || parsedSeed < 0) {
    return validationError("Seed는 0 이상의 정수입니다.", 0);
  }
  if (parsedBlockCount === null || parsedBlockCount < 1 || parsedBlockCount > 64) {
    return validationError("Block 수는 1 이상 64 이하입니다.", 0);
  }

  const runCount = 2 ** parsedFactors.length * parsedReplicates + parsedCenterPoints;
  if (runCount > maxRunCount) {
    return validationError(`현재 설계 제한은 ${maxRunCount.toLocaleString()} runs입니다.`, runCount);
  }
  if (parsedBlockCount > runCount) {
    return validationError("Block 수는 전체 run 수보다 클 수 없습니다.", runCount);
  }
  return {
    kind: "ready",
    message: null,
    request: {
      name: trimmedName,
      factors: parsedFactors,
      replicates: parsedReplicates,
      center_points: parsedCenterPoints,
      randomize,
      randomization_seed: parsedSeed,
      block_count: parsedBlockCount,
    },
    runCount,
  };
}

function validationError(message: string, runCount: number): ValidationResult {
  return {
    kind: "error",
    message,
    request: null,
    runCount,
  };
}

function validateResponseDraft(
  runs: FactorialDesignResponse["runs"],
  responseName: string,
  responseUnit: string,
  responseValues: Record<number, string>,
): ResponseValidationResult {
  const trimmedName = responseName.trim();
  if (trimmedName.length === 0) {
    return responseValidationError("반응 이름을 입력하세요.");
  }
  const values = [];
  for (const run of runs) {
    const rawValue = responseValues[run.run_order] ?? "";
    if (rawValue.trim().length === 0) {
      return responseValidationError(`Run ${run.run_order}의 반응값을 입력하세요.`);
    }
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) {
      return responseValidationError(`Run ${run.run_order}의 반응값은 숫자여야 합니다.`);
    }
    values.push({ run_order: run.run_order, value: parsed });
  }
  return {
    kind: "ready",
    message: null,
    request: {
      response_name: trimmedName,
      unit: responseUnit.trim().length > 0 ? responseUnit.trim() : null,
      values,
    },
  };
}

function responseValidationError(message: string): ResponseValidationResult {
  return {
    kind: "error",
    message,
    request: null,
  };
}

function integerField(value: string): number | null {
  const parsed = Number(value);
  return Number.isInteger(parsed) ? parsed : null;
}

function formatFactorLevel(value: number | undefined): string {
  return typeof value === "number" ? Number(value.toPrecision(12)).toLocaleString() : "-";
}

function formatCodedLevels(levels: Record<string, number>): string {
  return Object.entries(levels)
    .map(([name, level]) => `${name}:${level}`)
    .join(", ");
}
