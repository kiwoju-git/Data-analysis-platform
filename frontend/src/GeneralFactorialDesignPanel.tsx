import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";

import {
  createGeneralFactorialAnalysis,
  createGeneralFactorialDesign,
  fetchGeneralFactorialDesign,
  fetchGeneralFactorialResponses,
  saveGeneralFactorialResponses,
  type GeneralFactorialAnalysisResponse,
  type GeneralFactorialDesignCreateRequest,
  type GeneralFactorialDesignResponse,
} from "./api";
import { DoeActionBar, DoeFormSection } from "./doe/DoeFormPrimitives";
import { DoeSettingsTable } from "./doe/DoeSettingsTable";

interface GeneralFactorDraft {
  id: string;
  name: string;
  levels: string;
  unit: string;
}

export function GeneralFactorialDesignPanel({
  initialDesignId = null,
}: {
  initialDesignId?: string | null;
}) {
  const [name, setName] = useState("3-level general factorial design");
  const [replicates, setReplicates] = useState("1");
  const [seed, setSeed] = useState("20260806");
  const [randomize, setRandomize] = useState(true);
  const [interactionOrder, setInteractionOrder] = useState("2");
  const [factors, setFactors] = useState<GeneralFactorDraft[]>([
    { id: "general-factor-1", name: "Temperature", levels: "60, 70, 80", unit: "C" },
    { id: "general-factor-2", name: "Material", levels: "A, B, C", unit: "" },
  ]);
  const [design, setDesign] = useState<GeneralFactorialDesignResponse | null>(null);
  const [responses, setResponses] = useState<Record<number, string>>({});
  const [responseName, setResponseName] = useState("Yield");
  const [responseUnit, setResponseUnit] = useState("");
  const [analysis, setAnalysis] = useState<GeneralFactorialAnalysisResponse | null>(null);
  const [pending, setPending] = useState<"create" | "save" | "analysis" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const validation = useMemo(
    () => validateGeneralDraft(name, factors, replicates, seed, randomize, interactionOrder),
    [factors, interactionOrder, name, randomize, replicates, seed],
  );

  useEffect(() => {
    if (initialDesignId === null) return;
    let current = true;
    setError(null);
    void Promise.all([
      fetchGeneralFactorialDesign(initialDesignId),
      fetchGeneralFactorialResponses(initialDesignId).catch(() => null),
    ])
      .then(([restoredDesign, restoredResponseCollection]) => {
        if (!current) return;
        setDesign(restoredDesign);
        setName(restoredDesign.name);
        setReplicates(String(restoredDesign.options.replicates));
        setSeed(String(restoredDesign.options.randomization_seed));
        setRandomize(restoredDesign.options.randomize);
        setInteractionOrder(String(restoredDesign.options.max_interaction_order));
        setFactors(
          restoredDesign.factors.map((factor, index) => ({
            id: `restored-general-factor-${index + 1}`,
            levels: factor.levels.join(", "),
            name: factor.name,
            unit: factor.unit ?? "",
          })),
        );
        const response = restoredResponseCollection?.responses[0];
        if (response !== undefined) {
          setResponseName(response.response_name);
          setResponseUnit(response.unit ?? "");
          setResponses(
            Object.fromEntries(response.values.map((value) => [value.run_order, String(value.value)])),
          );
        } else {
          setResponses(Object.fromEntries(restoredDesign.runs.map((run) => [run.run_order, ""])));
        }
      })
      .catch((caught) => {
        if (current) {
          setError(
            caught instanceof Error
              ? caught.message
              : "doe_general_factorial_design_fetch_failed",
          );
        }
      });
    return () => {
      current = false;
    };
  }, [initialDesignId]);

  async function onCreate() {
    if (validation.request === null) return;
    setPending("create");
    setError(null);
    try {
      const created = await createGeneralFactorialDesign(validation.request);
      setDesign(created);
      setResponses(Object.fromEntries(created.runs.map((run) => [run.run_order, ""])));
      setAnalysis(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "doe_general_factorial_design_failed");
    } finally {
      setPending(null);
    }
  }

  async function onSaveResponses() {
    if (design === null) return;
    const values = design.runs.map((run) => ({
      run_order: run.run_order,
      value: Number(responses[run.run_order]),
    }));
    if (values.some((item) => !Number.isFinite(item.value))) {
      setError("모든 run의 반응값을 유한한 숫자로 입력하세요.");
      return;
    }
    setPending("save");
    setError(null);
    try {
      await saveGeneralFactorialResponses(design.design_id, {
        response_name: responseName.trim(),
        unit: responseUnit.trim() || null,
        values,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "doe_general_factorial_responses_failed");
    } finally {
      setPending(null);
    }
  }

  async function onAnalyze() {
    if (design === null) return;
    setPending("analysis");
    setError(null);
    try {
      setAnalysis(
        await createGeneralFactorialAnalysis(design.design_id, {
          response_name: responseName.trim(),
          max_interaction_order: Number(interactionOrder),
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "doe_general_factorial_analysis_failed");
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="general-factorial-workspace">
      <DoeFormSection
        title="일반 완전요인 설정"
        description="각 숫자 또는 문자 수준의 모든 조합을 생성하며, 숫자 수준도 범주형 수준으로 분석합니다."
      >
        <DoeSettingsTable
          ariaLabel="일반 완전요인 기본 설정"
          fields={[
            {
              key: "name",
              label: "설계 이름",
              controlId: "general-factorial-name",
              control: <input id="general-factorial-name" value={name} onChange={(event) => setName(event.currentTarget.value)} />,
            },
            {
              key: "replicates",
              label: "반복",
              controlId: "general-factorial-replicates",
              control: <input id="general-factorial-replicates" inputMode="numeric" value={replicates} onChange={(event) => setReplicates(event.currentTarget.value)} />,
            },
            {
              key: "interaction",
              label: "상호작용 차수",
              controlId: "general-factorial-interaction",
              control: (
                <select id="general-factorial-interaction" value={interactionOrder} onChange={(event) => setInteractionOrder(event.currentTarget.value)}>
                  <option value="1">주효과</option>
                  <option value="2">2차 상호작용까지</option>
                  <option value="3">3차 상호작용까지</option>
                </select>
              ),
            },
            {
              key: "seed",
              label: "무작위화 seed",
              controlId: "general-factorial-seed",
              control: <input id="general-factorial-seed" inputMode="numeric" value={seed} onChange={(event) => setSeed(event.currentTarget.value)} />,
            },
          ]}
        />
        <label className="doe-table-toggle">
          <input checked={randomize} type="checkbox" onChange={(event) => setRandomize(event.currentTarget.checked)} />
          <span>실행 순서 무작위화</span>
        </label>
      </DoeFormSection>

      <section className="doe-compact-section">
        <div className="panel-heading compact-heading">
          <div><h4>요인 수준</h4><p>수준은 쉼표로 구분합니다. 각 요인은 2~10개 수준을 지원합니다.</p></div>
          <button
            className="secondary-button"
            disabled={factors.length >= 6}
            onClick={() => setFactors((current) => [...current, { id: `general-factor-${Date.now()}`, name: `Factor ${current.length + 1}`, levels: "Low, Middle, High", unit: "" }])}
            type="button"
          >요인 추가</button>
        </div>
        <div className="table-wrap">
          <table className="result-table doe-factor-table">
            <thead><tr><th>요인</th><th>수준 목록</th><th>단위</th><th>수준 수</th><th>작업</th></tr></thead>
            <tbody>
              {factors.map((factor, index) => (
                <tr key={factor.id}>
                  <td><input aria-label={`일반 요인 ${index + 1} 이름`} value={factor.name} onChange={(event) => updateFactor(factor.id, "name", event.currentTarget.value, setFactors)} /></td>
                  <td><input aria-label={`${factor.name} 수준 목록`} value={factor.levels} onChange={(event) => updateFactor(factor.id, "levels", event.currentTarget.value, setFactors)} /></td>
                  <td><input aria-label={`${factor.name} 단위`} value={factor.unit} onChange={(event) => updateFactor(factor.id, "unit", event.currentTarget.value, setFactors)} /></td>
                  <td>{parseLevels(factor.levels).length}</td>
                  <td><button className="secondary-button compact-button" disabled={factors.length <= 2} onClick={() => setFactors((current) => current.filter((item) => item.id !== factor.id))} type="button">삭제</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <div className="notice-box">
        예상 실험 수 {validation.runCount.toLocaleString()}개. 연속 요인의 곡률 최적화가 목적이면 반응표면법을 검토하세요.
      </div>
      {validation.message !== null ? <div className="notice-box notice-warning">{validation.message}</div> : null}
      {error !== null ? <div className="error-box">오류 코드: {error}</div> : null}
      <DoeActionBar summary={`최대 256 runs · 현재 ${validation.runCount.toLocaleString()} runs`}>
        <button className="primary-button" disabled={pending !== null || validation.request === null} onClick={() => void onCreate()} type="button">
          {pending === "create" ? "생성 중" : "일반 완전요인 설계 생성"}
        </button>
      </DoeActionBar>
      {design !== null ? (
        <GeneralFactorialResult
          analysis={analysis}
          design={design}
          interactionOrder={Number(interactionOrder)}
          onAnalyze={() => void onAnalyze()}
          onSave={() => void onSaveResponses()}
          pending={pending}
          responseName={responseName}
          responseUnit={responseUnit}
          responses={responses}
          setResponseName={setResponseName}
          setResponses={setResponses}
          setResponseUnit={setResponseUnit}
        />
      ) : null}
    </div>
  );
}

function GeneralFactorialResult({ analysis, design, onAnalyze, onSave, pending, responseName, responseUnit, responses, setResponseName, setResponses, setResponseUnit }: {
  analysis: GeneralFactorialAnalysisResponse | null;
  design: GeneralFactorialDesignResponse;
  interactionOrder: number;
  onAnalyze: () => void;
  onSave: () => void;
  pending: "create" | "save" | "analysis" | null;
  responseName: string;
  responseUnit: string;
  responses: Record<number, string>;
  setResponseName: (value: string) => void;
  setResponses: Dispatch<SetStateAction<Record<number, string>>>;
  setResponseUnit: (value: string) => void;
}) {
  return <section className="result-section">
    <h3>일반 완전요인 설계</h3>
    <div className="metadata-grid"><span>설계</span><strong>{design.name}</strong><span>실험 수</span><strong>{design.run_count}</strong><span>분석 coding</span><strong>Treatment coding</strong><span>범위</span><strong>숫자·문자 범주 수준</strong></div>
    <div className="table-wrap"><table className="result-table"><thead><tr><th>Run</th><th>Standard</th><th>Rep</th>{design.factors.map((factor) => <th key={factor.name}>{factor.name}</th>)}</tr></thead><tbody>{design.runs.map((run) => <tr key={run.run_order}><td>{run.run_order}</td><td>{run.standard_order}</td><td>{run.replicate_index}</td>{design.factors.map((factor) => <td key={factor.name}>{String(run.factor_levels[factor.name])}</td>)}</tr>)}</tbody></table></div>
    <DoeSettingsTable ariaLabel="일반 완전요인 반응 설정" fields={[
      { key: "response", label: "반응 이름", controlId: "general-factorial-response", control: <input id="general-factorial-response" value={responseName} onChange={(event) => setResponseName(event.currentTarget.value)} /> },
      { key: "unit", label: "반응 단위", controlId: "general-factorial-response-unit", control: <input id="general-factorial-response-unit" value={responseUnit} onChange={(event) => setResponseUnit(event.currentTarget.value)} /> },
    ]} />
    <div className="table-wrap"><table className="result-table"><thead><tr><th>Run</th>{design.factors.map((factor) => <th key={factor.name}>{factor.name}</th>)}<th>반응</th></tr></thead><tbody>{design.runs.map((run) => <tr key={run.run_order}><td>{run.run_order}</td>{design.factors.map((factor) => <td key={factor.name}>{String(run.factor_levels[factor.name])}</td>)}<td><input aria-label={`run ${run.run_order} 반응`} inputMode="decimal" value={responses[run.run_order] ?? ""} onChange={(event) => {
      const value = event.currentTarget.value;
      setResponses((current) => ({ ...current, [run.run_order]: value }));
    }} /></td></tr>)}</tbody></table></div>
    <DoeActionBar summary="반응 저장 후 범주형 term-block ANOVA를 실행합니다."><button className="secondary-button" disabled={pending !== null} onClick={onSave} type="button">{pending === "save" ? "저장 중" : "반응 저장"}</button><button className="primary-button" disabled={pending !== null} onClick={onAnalyze} type="button">{pending === "analysis" ? "분석 중" : "일반 완전요인 ANOVA"}</button></DoeActionBar>
    {analysis !== null ? <GeneralFactorialAnalysisView analysis={analysis} /> : null}
  </section>;
}

function GeneralFactorialAnalysisView({ analysis }: { analysis: GeneralFactorialAnalysisResponse }) {
  return <section className="result-section"><h3>분산분석</h3><div className="metadata-grid"><span>R²</span><strong>{(analysis.result.fit.r_squared * 100).toFixed(2)}%</strong><span>Adjusted R²</span><strong>{analysis.result.fit.adjusted_r_squared === null ? "-" : `${(analysis.result.fit.adjusted_r_squared * 100).toFixed(2)}%`}</strong><span>Residual DF</span><strong>{analysis.result.sample.df_residual}</strong><span>Coding</span><strong>Treatment</strong></div><div className="table-wrap"><table className="result-table"><thead><tr><th>Source</th><th>DF</th><th>Adj SS</th><th>Adj MS</th><th>F</th><th>P</th></tr></thead><tbody>{analysis.result.anova.rows.map((row) => <tr key={row.term_id}><td>{row.source}</td><td>{row.df}</td><td>{formatNumber(row.adjusted_sum_squares)}</td><td>{formatNumber(row.adjusted_mean_square)}</td><td>{formatNumber(row.f_statistic)}</td><td>{formatNumber(row.p_value)}</td></tr>)}</tbody></table></div>{analysis.result.warnings.map((warning) => <div className="notice-box notice-warning" key={warning}>{warning}</div>)}</section>;
}

function validateGeneralDraft(name: string, factors: GeneralFactorDraft[], replicatesText: string, seedText: string, randomize: boolean, interactionText: string): { request: GeneralFactorialDesignCreateRequest | null; runCount: number; message: string | null } {
  const replicates = Number(replicatesText);
  const seed = Number(seedText);
  const interaction = Number(interactionText);
  const parsed = factors.map((factor) => ({ ...factor, parsedLevels: parseLevels(factor.levels) }));
  const runCount = parsed.reduce((count, factor) => count * factor.parsedLevels.length, Math.max(1, replicates));
  if (!name.trim() || !Number.isInteger(replicates) || replicates < 1 || !Number.isInteger(seed) || seed < 0) return { request: null, runCount, message: "설계 이름, 반복 수와 seed를 확인하세요." };
  if (new Set(parsed.map((factor) => factor.name.trim().toLocaleLowerCase())).size !== parsed.length || parsed.some((factor) => !factor.name.trim() || factor.parsedLevels.length < 2 || factor.parsedLevels.length > 10)) return { request: null, runCount, message: "요인 이름은 고유해야 하며 각 요인은 2~10개 수준이 필요합니다." };
  if (runCount > 256) return { request: null, runCount, message: `예상 ${runCount} runs로 상한 256을 초과합니다.` };
  return { request: { name: name.trim(), factors: parsed.map((factor) => ({ name: factor.name.trim(), levels: factor.parsedLevels.map(parseLevel), unit: factor.unit.trim() || null })), replicates, randomize, randomization_seed: seed, max_interaction_order: Math.min(interaction, factors.length) }, runCount, message: null };
}

function parseLevels(value: string): string[] { return value.split(",").map((item) => item.trim()).filter(Boolean); }
function parseLevel(value: string): number | string { const numeric = Number(value); return value !== "" && Number.isFinite(numeric) ? numeric : value; }
function updateFactor(
  id: string,
  field: "name" | "levels" | "unit",
  value: string,
  setter: Dispatch<SetStateAction<GeneralFactorDraft[]>>,
) {
  setter((current) =>
    current.map((factor) => (factor.id === id ? { ...factor, [field]: value } : factor)),
  );
}
function formatNumber(value: number | null): string { return value === null ? "-" : Number(value.toPrecision(6)).toString(); }
