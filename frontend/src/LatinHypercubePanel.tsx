import {
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import {
  createLatinHypercubeDesign,
  saveLatinHypercubeResponses,
  type LatinHypercubeDesignCreateRequest,
  type LatinHypercubeDesignResponse,
} from "./api";
import { apiRoutes } from "./api/routes";
import {
  DoeActionBar,
  DoeAdvancedSettings,
  DoeFactorEditor,
  DoeFormSection,
} from "./doe/DoeFormPrimitives";
import { DoeSettingsTable } from "./doe/DoeSettingsTable";

interface FactorDraft {
  key: number;
  name: string;
  low: string;
  high: string;
  unit: string;
}

const initialFactors: FactorDraft[] = [
  { key: 1, name: "factor_1", low: "0", high: "1", unit: "" },
  { key: 2, name: "factor_2", low: "0", high: "1", unit: "" },
  { key: 3, name: "factor_3", low: "0", high: "1", unit: "" },
];

export function LatinHypercubePanel() {
  const [name, setName] = useState("LHS 공간충전 설계");
  const [factors, setFactors] = useState(initialFactors);
  const [runCount, setRunCount] = useState("9");
  const [seed, setSeed] = useState("20260729");
  const [runOrderSeed, setRunOrderSeed] = useState("20260730");
  const [optimization, setOptimization] = useState<"random_cd" | "none">("random_cd");
  const [randomizeRunOrder, setRandomizeRunOrder] = useState(true);
  const [design, setDesign] = useState<LatinHypercubeDesignResponse | null>(null);
  const [responseName, setResponseName] = useState("response");
  const [responseUnit, setResponseUnit] = useState("");
  const [responseDrafts, setResponseDrafts] = useState<Record<number, string>>({});
  const [responseRevision, setResponseRevision] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isSavingResponses, setIsSavingResponses] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const request = useMemo(
    () => buildRequest({
      name,
      factors,
      runCount,
      seed,
      runOrderSeed,
      optimization,
      randomizeRunOrder,
    }),
    [factors, name, optimization, randomizeRunOrder, runCount, runOrderSeed, seed],
  );
  const suggestedBalanced = Math.min(64, Math.max(8, 3 * factors.length));
  const referenceSpaceFilling = Math.min(200, 10 * factors.length);
  const responseReady =
    design !== null &&
    responseName.trim() !== "" &&
    design.runs.every((run) => Number.isFinite(Number(responseDrafts[run.run_order])));

  return (
    <section className="analysis-run-panel lhs-workspace" aria-label="LHS 공간충전 설계">
      <div className="notice-box">
        <strong>연속형 요인의 사각형 범위를 고르게 탐색하는 설계입니다.</strong>
        <p>
          2수준 요인배치의 직교 효과 추정과 목적이 다르며, 범주형·정수형·선형 제약은
          현재 지원하지 않습니다. 별도 베이지안 스터디가 LHS 초기점을 생성할 수
          있으므로 같은 설계표를 중복 생성할 필요는 없습니다.
        </p>
      </div>
      <DoeFormSection
        title="설계 기본 설정"
        description="실험 수와 요인 범위를 먼저 정하고 생성 정책은 고급 설정에서 확인합니다."
      >
        <DoeSettingsTable
          ariaLabel="LHS 설계 기본 설정"
          fields={[
            {
              key: "name",
              label: "설계 이름",
              controlId: "lhs-design-name",
              control: (
                <input
                  id="lhs-design-name"
                  value={name}
                  onChange={(event) => setName(event.currentTarget.value)}
                />
              ),
            },
            {
              key: "run-count",
              label: "실험 수",
              controlId: "lhs-run-count",
              control: (
                <input
                  id="lhs-run-count"
                  aria-describedby="lhs-run-count-help"
                  inputMode="numeric"
                  value={runCount}
                  onChange={(event) => setRunCount(event.currentTarget.value)}
                />
              ),
              helper: `GP 계산 최소 ${factors.length + 1}개 · 권장 시작 ${suggestedBalanced}개 · 공간충전 참고 약 ${referenceSpaceFilling}개`,
              helperId: "lhs-run-count-help",
            },
          ]}
        />
        <DoeAdvancedSettings
          summaryText={`seed ${seed} · ${randomizeRunOrder ? "실행 순서 무작위화" : "표준 순서"}`}
        >
          <DoeSettingsTable
            ariaLabel="LHS 고급 설정"
            fields={[
              {
                key: "seed",
                label: "설계 seed",
                controlId: "lhs-design-seed",
                control: (
                  <input
                    id="lhs-design-seed"
                    inputMode="numeric"
                    value={seed}
                    onChange={(event) => setSeed(event.currentTarget.value)}
                  />
                ),
              },
              {
                key: "run-order-seed",
                label: "실행 순서 seed",
                controlId: "lhs-run-order-seed",
                control: (
                  <input
                    id="lhs-run-order-seed"
                    inputMode="numeric"
                    value={runOrderSeed}
                    disabled={!randomizeRunOrder}
                    onChange={(event) => setRunOrderSeed(event.currentTarget.value)}
                  />
                ),
              },
              {
                key: "optimization",
                label: "품질 최적화",
                controlId: "lhs-optimization",
                control: (
                  <select
                    id="lhs-optimization"
                    aria-describedby="lhs-optimization-help"
                    value={optimization}
                    onChange={(event) =>
                      setOptimization(event.currentTarget.value as "random_cd" | "none")
                    }
                  >
                    <option value="random_cd">Discrepancy 개선 (random-cd)</option>
                    <option value="none">기본 LHS</option>
                  </select>
                ),
                helper: "여러 좌표 순열 중 centered discrepancy가 작은 설계를 찾습니다.",
                helperId: "lhs-optimization-help",
              },
              {
                key: "randomize",
                label: "실행 순서 무작위화",
                controlId: "lhs-randomize-run-order",
                control: (
                  <label className="doe-table-toggle" htmlFor="lhs-randomize-run-order">
                    <input
                      id="lhs-randomize-run-order"
                      checked={randomizeRunOrder}
                      type="checkbox"
                      onChange={(event) =>
                        setRandomizeRunOrder(event.currentTarget.checked)
                      }
                    />
                    <span>사용</span>
                  </label>
                ),
                helper: randomizeRunOrder
                  ? "공간충전 좌표는 유지하고 실제 실행 순서만 seed로 섞습니다."
                  : "표준 순서와 실행 순서가 동일합니다.",
              },
            ]}
          />
        </DoeAdvancedSettings>
      </DoeFormSection>
      <DoeFactorEditor
        title="연속형 요인 범위"
        action={
          <button
            className="secondary-button"
            disabled={factors.length >= 6}
            type="button"
            onClick={() =>
              setFactors((current) => [
                ...current,
                {
                  key: Math.max(...current.map((item) => item.key)) + 1,
                  name: `factor_${current.length + 1}`,
                  low: "0",
                  high: "1",
                  unit: "",
                },
              ])
            }
          >
            요인 추가
          </button>
        }
      >
        <div className="table-wrap">
          <table className="result-table doe-factor-table">
            <colgroup>
              <col className="doe-factor-name-column" />
              <col className="doe-factor-bound-column" />
              <col className="doe-factor-bound-column" />
              <col className="doe-factor-unit-column" />
              <col className="doe-factor-action-column" />
            </colgroup>
            <thead>
              <tr>
                <th>요인</th>
                <th>하한</th>
                <th>상한</th>
                <th>단위</th>
                <th className="doe-factor-action-cell">작업</th>
              </tr>
            </thead>
            <tbody>
              {factors.map((factor, index) => (
                <tr key={factor.key}>
                  <td>
                    <input
                      aria-label={`요인 ${index + 1} 이름`}
                      value={factor.name}
                      onChange={(event) =>
                        updateFactor(setFactors, factor.key, "name", event.currentTarget.value)
                      }
                    />
                  </td>
                  <td>
                    <input
                      aria-label={`${factor.name || `요인 ${index + 1}`} 하한`}
                      inputMode="decimal"
                      value={factor.low}
                      onChange={(event) =>
                        updateFactor(setFactors, factor.key, "low", event.currentTarget.value)
                      }
                    />
                  </td>
                  <td>
                    <input
                      aria-label={`${factor.name || `요인 ${index + 1}`} 상한`}
                      inputMode="decimal"
                      value={factor.high}
                      onChange={(event) =>
                        updateFactor(setFactors, factor.key, "high", event.currentTarget.value)
                      }
                    />
                  </td>
                  <td>
                    <input
                      aria-label={`${factor.name || `요인 ${index + 1}`} 단위`}
                      value={factor.unit}
                      onChange={(event) =>
                        updateFactor(setFactors, factor.key, "unit", event.currentTarget.value)
                      }
                    />
                  </td>
                  <td className="doe-factor-action-cell">
                    <button
                      aria-label={`${factor.name || `요인 ${index + 1}`} 삭제`}
                      className="secondary-button compact-button"
                      disabled={factors.length <= 1}
                      type="button"
                      onClick={() =>
                        setFactors((current) =>
                          current.filter((item) => item.key !== factor.key),
                        )
                      }
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DoeFactorEditor>
      {error !== null ? <div className="error-box" role="alert">오류 코드: {error}</div> : null}
      <DoeActionBar summary={`예상 실험 ${runCount || "-"}개`}>
        <button
          className="primary-button"
          disabled={request === null || isCreating}
          type="button"
          onClick={() => {
            if (request === null) return;
            setIsCreating(true);
            setError(null);
            setDesign(null);
            void createLatinHypercubeDesign(request)
              .then((next) => {
                setDesign(next);
                setResponseDrafts({});
                setResponseRevision(null);
              })
              .catch((reason) =>
                setError(reason instanceof Error ? reason.message : "lhs_design_failed"),
              )
              .finally(() => setIsCreating(false));
          }}
        >
          {isCreating ? "LHS 설계 생성 중" : "LHS 설계 생성"}
        </button>
      </DoeActionBar>
      {design !== null ? (
        <>
          <section className="result-section" aria-labelledby="lhs-quality-title">
            <div className="panel-heading">
              <div>
                <h4 id="lhs-quality-title">설계 품질</h4>
                <p>품질 진단값이며 최적 설계를 보장하지 않습니다.</p>
              </div>
              <a
                className="secondary-button button-link"
                download
                href={apiRoutes.doeLatinHypercubeExport(design.design_id)}
              >
                CSV 내보내기
              </a>
            </div>
            <dl className="profile-quality-summary">
              <Metric label="Centered discrepancy" value={design.quality.centered_discrepancy} />
              <Metric label="최소 점간 거리" value={design.quality.minimum_pairwise_distance} />
              <Metric
                label="최대 절대 요인 상관"
                value={design.quality.maximum_absolute_factor_correlation}
              />
              <div>
                <dt>층화 검증</dt>
                <dd>{design.quality.strata_valid ? "통과" : "검토 필요"}</dd>
              </div>
            </dl>
            <div className="table-wrap">
              <table className="lhs-run-table">
                <thead>
                  <tr>
                    <th>Standard order</th>
                    <th>Run order</th>
                    {design.factors.map((factor) => <th key={factor.name}>{factor.name}</th>)}
                    {design.factors.map((factor) => (
                      <th key={`${factor.name}-normalized`}>{factor.name} [0,1)</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {design.runs.map((run) => (
                    <tr key={run.run_order}>
                      <td>{run.standard_order}</td>
                      <td>{run.run_order}</td>
                      {design.factors.map((factor) => (
                        <td key={factor.name}>{formatNumber(run.factor_levels[factor.name])}</td>
                      ))}
                      {design.factors.map((factor) => (
                        <td key={`${factor.name}-normalized`}>
                          {formatNumber(run.normalized_levels[factor.name])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="result-section" aria-labelledby="lhs-response-title">
            <div className="panel-heading">
              <div>
                <h4 id="lhs-response-title">실제 반응값 입력</h4>
                <p>
                  LHS는 설계표를 생성합니다. 반응값을 저장해도 이 화면이 최적점을
                  자동 확정하지 않습니다.
                </p>
              </div>
              {responseRevision !== null ? (
                <span className="status-pill status-ready">revision {responseRevision}</span>
              ) : null}
            </div>
            <div className="option-grid">
              <label>
                <span>반응 이름</span>
                <input
                  value={responseName}
                  onChange={(event) => setResponseName(event.currentTarget.value)}
                />
              </label>
              <label>
                <span>단위</span>
                <input
                  value={responseUnit}
                  onChange={(event) => setResponseUnit(event.currentTarget.value)}
                />
              </label>
            </div>
            <div className="lhs-response-grid">
              {design.runs.map((run) => (
                <label key={run.run_order}>
                  <span>Run {run.run_order}</span>
                  <input
                    inputMode="decimal"
                    value={responseDrafts[run.run_order] ?? ""}
                    onChange={(event) => {
                      const nextValue = event.currentTarget.value;
                      setResponseDrafts((current) => ({
                        ...current,
                        [run.run_order]: nextValue,
                      }));
                    }}
                  />
                </label>
              ))}
            </div>
            <button
              className="primary-button"
              disabled={!responseReady || isSavingResponses}
              type="button"
              onClick={() => {
                setIsSavingResponses(true);
                setError(null);
                void saveLatinHypercubeResponses(design.design_id, {
                  response_name: responseName.trim(),
                  unit: responseUnit.trim() || null,
                  values: design.runs.map((run) => ({
                    run_order: run.run_order,
                    value: Number(responseDrafts[run.run_order]),
                  })),
                })
                  .then((saved) => {
                    const current = saved.responses.find(
                      (item) => item.response_name === responseName.trim(),
                    );
                    setResponseRevision(current?.response_revision_number ?? null);
                  })
                  .catch((reason) =>
                    setError(reason instanceof Error ? reason.message : "lhs_responses_failed"),
                  )
                  .finally(() => setIsSavingResponses(false));
              }}
            >
              {isSavingResponses ? "반응 revision 저장 중" : "반응 revision 저장"}
            </button>
          </section>
        </>
      ) : null}
    </section>
  );
}

function buildRequest(input: {
  name: string;
  factors: FactorDraft[];
  runCount: string;
  seed: string;
  runOrderSeed: string;
  optimization: "random_cd" | "none";
  randomizeRunOrder: boolean;
}): LatinHypercubeDesignCreateRequest | null {
  const runCount = Number(input.runCount);
  const seed = Number(input.seed);
  const runOrderSeed = Number(input.runOrderSeed);
  const factors = input.factors.map((item) => ({
    name: item.name.trim(),
    low: Number(item.low),
    high: Number(item.high),
    unit: item.unit.trim() || null,
  }));
  if (
    input.name.trim() === "" ||
    !Number.isInteger(runCount) ||
    runCount < 2 ||
    runCount > 200 ||
    !Number.isInteger(seed) ||
    seed < 0 ||
    !Number.isInteger(runOrderSeed) ||
    runOrderSeed < 0 ||
    new Set(factors.map((item) => item.name)).size !== factors.length ||
    factors.some(
      (item) =>
        item.name === "" ||
        !Number.isFinite(item.low) ||
        !Number.isFinite(item.high) ||
        item.low >= item.high,
    )
  ) {
    return null;
  }
  return {
    name: input.name.trim(),
    factors,
    run_count: runCount,
    seed,
    randomize_run_order: input.randomizeRunOrder,
    run_order_seed: runOrderSeed,
    optimization: input.optimization,
  };
}

function updateFactor(
  setFactors: Dispatch<SetStateAction<FactorDraft[]>>,
  key: number,
  field: keyof Omit<FactorDraft, "key">,
  value: string,
) {
  setFactors((current) =>
    current.map((item) =>
      item.key === key ? { ...item, [field]: value } : item,
    ),
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{formatNumber(value)}</dd>
    </div>
  );
}

function formatNumber(value: number | undefined): string {
  return value === undefined
    ? "-"
    : value.toLocaleString("ko-KR", { maximumSignificantDigits: 7 });
}
