import {
  Fragment,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import {
  createGeneralFactorialAnalysis,
  createDoeResponseRevision,
  createGeneralFactorialDesign,
  fetchGeneralFactorialDesign,
  fetchGeneralFactorialResponses,
  saveGeneralFactorialResponses,
  type GeneralFactorialAnalysisResponse,
  type GeneralFactorialDesignResponse,
  type DoeDesignResponsesResponse,
} from "./api";
import { DoeActionBar, DoeFormSection } from "./doe/DoeFormPrimitives";
import { DoeFactorCountControl } from "./doe/DoeFactorCountControl";
import { DoeSettingsTable } from "./doe/DoeSettingsTable";
import { DoeResponsePasteDialog } from "./doe/DoeResponsePasteDialog";
import { DoeModelSelectionSettings } from "./doe/DoeModelSelectionSettings";
import { DoeTermSelection, useDoeTermCatalog } from "./doe/DoeTermSelection";
import { defaultDoeSelection, interactionOrderLabel, factorialWorkflowMessage } from "./doe/factorialWorkflowPresentation";
import { FactorialModelSelectionResults } from "./FactorialModelSelectionResults";
import { FactorialResidualPlots } from "./FactorialResidualPlots";
import { FactorialPlotsPanel } from "./FactorialPlotsPanel";
import { FactorialStoredModelWorkflow } from "./FactorialStoredModelWorkflow";
import { fetchStoredGeneralFactorialAnalysis } from "./api/factorialWorkflow";
import { DOE_FACTOR_CAPABILITIES } from "./doe/factorCapabilities";
import {
  parsePastedLevels,
  threeLevelPresetLevels,
  validateGeneralDraft,
  type GeneralFactorDraft,
} from "./generalFactorialDraft";
import { resolveLocalizedText, t } from "./i18n/translate";

export function GeneralFactorialDesignPanel({
  initialDesignId = null,
  initialAnalysisId = null,
}: {
  initialDesignId?: string | null;
  initialAnalysisId?: string | null;
}) {
  const [name, setName] = useState("3-level general factorial design");
  const [replicates, setReplicates] = useState("1");
  const [seed, setSeed] = useState("20260806");
  const [randomize, setRandomize] = useState(true);
  const [interactionOrder, setInteractionOrder] = useState("2");
  const [factors, setFactors] = useState<GeneralFactorDraft[]>([
    {
      id: "general-factor-1",
      name: "Temperature",
      levelType: "numeric",
      levels: ["60", "70", "80"],
      unit: "C",
      expanded: true,
      pasteDraft: "",
    },
    {
      id: "general-factor-2",
      name: "Material",
      levelType: "categorical",
      levels: ["A", "B", "C"],
      unit: "",
      expanded: false,
      pasteDraft: "",
    },
  ]);
  const [design, setDesign] = useState<GeneralFactorialDesignResponse | null>(null);
  const [responses, setResponses] = useState<Record<number, string>>({});
  const [responseName, setResponseName] = useState("Yield");
  const [responseUnit, setResponseUnit] = useState("");
  const [analysis, setAnalysis] = useState<GeneralFactorialAnalysisResponse | null>(null);
  const [savedResponses, setSavedResponses] = useState<DoeDesignResponsesResponse | null>(null);
  const [correctionMode, setCorrectionMode] = useState(false);
  const [modelSelection, setModelSelection] = useState(defaultDoeSelection);
  useEffect(() => { setModelSelection(defaultDoeSelection); }, [design?.design_id]);
  const termCatalog = useDoeTermCatalog(design?.design_id ?? null, Number(interactionOrder), modelSelection);
  const [confidence, setConfidence] = useState(0.95);
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
      initialAnalysisId ? fetchStoredGeneralFactorialAnalysis(initialDesignId, initialAnalysisId) : Promise.resolve(null),
    ])
      .then(([restoredDesign, restoredResponseCollection, restoredAnalysis]) => {
        if (!current) return;
        setDesign(restoredDesign);
        setAnalysis(restoredAnalysis);
        setSavedResponses(restoredResponseCollection);
        setCorrectionMode(false);
        setName(restoredDesign.name);
        setReplicates(String(restoredDesign.options.replicates));
        setSeed(String(restoredDesign.options.randomization_seed));
        setRandomize(restoredDesign.options.randomize);
        setInteractionOrder(String(restoredDesign.options.max_interaction_order));
        setFactors(
          restoredDesign.factors.map((factor, index) => ({
            id: `restored-general-factor-${index + 1}`,
            levelType: factor.levels.every((level) => typeof level === "number")
              ? "numeric"
              : "categorical",
            levels: factor.levels.map(String),
            name: factor.name,
            unit: factor.unit ?? "",
            expanded: false,
            pasteDraft: "",
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
  }, [initialDesignId, initialAnalysisId]);

  async function onCreate() {
    if (validation.request === null) return;
    setPending("create");
    setError(null);
    try {
      const created = await createGeneralFactorialDesign(validation.request);
      setDesign(created);
      setResponses(Object.fromEntries(created.runs.map((run) => [run.run_order, ""])));
      setAnalysis(null);
      setSavedResponses(null);
      setCorrectionMode(false);
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
    if (values.some((item) => !Number.isFinite(item.value) || !responses[item.run_order]?.trim())) {
      setError(t("doe.response.invalid"));
      return;
    }
    setPending("save");
    setError(null);
    try {
      const request = {
        response_name: responseName.trim(),
        unit: responseUnit.trim() || null,
        values,
      };
      if (correctionMode) {
        await createDoeResponseRevision(design.design_id, { ...request,
          supersedes_response_revision_id: savedResponses?.responses[0]?.response_revision_id ?? null });
        setSavedResponses(await fetchGeneralFactorialResponses(design.design_id));
      } else {
        setSavedResponses(await saveGeneralFactorialResponses(design.design_id, request));
      }
      setCorrectionMode(false);
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
          response_revision_id: savedResponses?.responses[0]?.response_revision_id ?? null,
        model_selection: termCatalog.options,
          confidence_level: confidence,
          point_limit: 256,
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
                  {[1, 2, 3].map((order) => <option key={order} value={order}>{interactionOrderLabel(order)}</option>)}
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
          <div>
            <h4>요인 수준</h4>
            <p>요인마다 2~10개의 숫자 또는 문자 수준을 입력 순서대로 지정합니다.</p>
          </div>
          <div className="button-row compact-actions">
            <DoeFactorCountControl
              count={factors.length}
              factorLabels={factors.map((factor) => factor.name)}
              maximum={DOE_FACTOR_CAPABILITIES.generalFactorialAuthoring}
              minimum={2}
              onResize={(count) => setFactors((current) => resizeGeneralFactors(current, count))}
            />
            <button
              className="secondary-button"
              onClick={() => applyThreeLevelPreset(factors, setFactors)}
              type="button"
            >
              모든 요인을 3수준으로 설정
            </button>
            <button
              className="secondary-button"
              disabled={factors.length >= DOE_FACTOR_CAPABILITIES.generalFactorialAuthoring}
              onClick={() => setFactors((current) => resizeGeneralFactors(current, current.length + 1))}
              type="button"
            >
              요인 추가
            </button>
          </div>
        </div>
        <div className="table-wrap">
          <table className="result-table doe-factor-table">
            <thead>
              <tr>
                <th>요인</th>
                <th>수준 유형</th>
                <th>수준 수</th>
                <th>수준 편집</th>
                <th>단위</th>
                <th>작업</th>
              </tr>
            </thead>
            <tbody>
              {factors.map((factor, index) => (
                <Fragment key={factor.id}>
                  <tr>
                    <td>
                      <input
                        aria-label={`일반 요인 ${index + 1} 이름`}
                        value={factor.name}
                        onChange={(event) =>
                          updateGeneralFactor(
                            factor.id,
                            { name: event.currentTarget.value },
                            setFactors,
                          )
                        }
                      />
                    </td>
                    <td>
                      <select
                        aria-label={`${factor.name} 수준 유형`}
                        value={factor.levelType}
                        onChange={(event) =>
                          updateGeneralFactor(
                            factor.id,
                            {
                              levelType: event.currentTarget.value as GeneralFactorDraft["levelType"],
                            },
                            setFactors,
                          )
                        }
                      >
                        <option value="numeric">숫자 수준</option>
                        <option value="categorical">문자 수준</option>
                      </select>
                    </td>
                    <td>
                      <select
                        aria-label={`${factor.name} 수준 수`}
                        value={factor.levels.length}
                        onChange={(event) =>
                          changeGeneralLevelCount(
                            factor,
                            Number(event.currentTarget.value),
                            setFactors,
                          )
                        }
                      >
                        {Array.from({ length: 9 }, (_, offset) => offset + 2).map((count) => (
                          <option key={count} value={count}>{count}</option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <button
                        aria-expanded={factor.expanded}
                        aria-controls={`${factor.id}-level-editor`}
                        className="secondary-button compact-button"
                        onClick={() =>
                          updateGeneralFactor(
                            factor.id,
                            { expanded: !factor.expanded },
                            setFactors,
                          )
                        }
                        type="button"
                      >
                        {factor.expanded ? "편집 닫기" : "수준 편집"}
                      </button>
                    </td>
                    <td>
                      <input
                        aria-label={`${factor.name} 단위`}
                        value={factor.unit}
                        onChange={(event) =>
                          updateGeneralFactor(
                            factor.id,
                            { unit: event.currentTarget.value },
                            setFactors,
                          )
                        }
                      />
                    </td>
                    <td>
                      <button
                        className="secondary-button compact-button"
                        disabled={factors.length <= 2}
                        onClick={() =>
                          setFactors((current) => current.filter((item) => item.id !== factor.id))
                        }
                        type="button"
                      >
                        삭제
                      </button>
                    </td>
                  </tr>
                  {factor.expanded ? (
                    <tr className="doe-factor-detail-row">
                      <td colSpan={6}>
                        <GeneralFactorLevelEditor factor={factor} setFactors={setFactors} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        <div className="notice-box">
          첫 수준은 treatment coding의 기준 수준입니다. 입력 순서는 자동 정렬되지 않습니다.
        </div>
      </section>
      <div className="notice-box">
        예상 실험 수 {validation.runCount.toLocaleString()}개. 3수준 완전요인은 일반 완전요인 설계의 한 형태입니다.
        연속 요인의 2차 곡률 최적화가 목적이면 반응표면법을 검토하세요.
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
          locked={(analysis !== null || savedResponses?.status === "analyzed") && !correctionMode}
          correctionMode={correctionMode}
          onCorrection={() => setCorrectionMode(true)}
          analysisSettings={<><DoeModelSelectionSettings value={modelSelection} onChange={setModelSelection}
            confidence={confidence} onConfidenceChange={setConfidence} disabled={pending !== null} />
            <DoeTermSelection state={termCatalog} value={modelSelection} onChange={setModelSelection} disabled={pending !== null} /></>}
          canAnalyze={termCatalog.ready && savedResponses !== null && !correctionMode && confidence > 0 && confidence < 1 &&
            (modelSelection.method === "none" || (modelSelection.alpha_to_remove > 0 && modelSelection.alpha_to_remove < 1))}
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

function resizeGeneralFactors(
  current: GeneralFactorDraft[],
  count: number,
): GeneralFactorDraft[] {
  if (count <= current.length) return current.slice(0, count);
  const next = [...current];
  const seed = Date.now();
  while (next.length < count) {
    const index = next.length + 1;
    next.push({
      id: `general-factor-${seed}-${index}`,
      name: `Factor ${index}`,
      levelType: "categorical",
      levels: ["Low", "Middle", "High"],
      unit: "",
      expanded: true,
      pasteDraft: "",
    });
  }
  return next;
}

function GeneralFactorLevelEditor({
  factor,
  setFactors,
}: {
  factor: GeneralFactorDraft;
  setFactors: Dispatch<SetStateAction<GeneralFactorDraft[]>>;
}) {
  const pastedLevels = parsePastedLevels(factor.pasteDraft);
  const canApplyPaste = pastedLevels.length >= 2 && pastedLevels.length <= 10;
  const canCalculateMidpoint =
    factor.levelType === "numeric" &&
    factor.levels.length === 3 &&
    Number.isFinite(Number(factor.levels[0])) &&
    Number.isFinite(Number(factor.levels[2]));
  return (
    <section
      aria-label={`${factor.name} 수준 편집`}
      className="general-factorial-level-editor"
      id={`${factor.id}-level-editor`}
    >
      <div className="general-factorial-level-grid">
        {factor.levels.map((level, index) => (
          <div className="general-factorial-level-field" key={`${factor.id}-level-${index}`}>
            <label htmlFor={`${factor.id}-level-${index}`}>수준 {index + 1}</label>
            <div className="general-factorial-level-control">
              <input
                id={`${factor.id}-level-${index}`}
                inputMode={factor.levelType === "numeric" ? "decimal" : "text"}
                value={level}
                onChange={(event) =>
                  updateGeneralLevel(factor.id, index, event.currentTarget.value, setFactors)
                }
              />
              <button
                aria-label={`${factor.name} 수준 ${index + 1} 위로 이동`}
                className="icon-button"
                disabled={index === 0}
                onClick={() => moveGeneralLevel(factor.id, index, index - 1, setFactors)}
                title="위로 이동"
                type="button"
              >
                ↑
              </button>
              <button
                aria-label={`${factor.name} 수준 ${index + 1} 아래로 이동`}
                className="icon-button"
                disabled={index === factor.levels.length - 1}
                onClick={() => moveGeneralLevel(factor.id, index, index + 1, setFactors)}
                title="아래로 이동"
                type="button"
              >
                ↓
              </button>
            </div>
          </div>
        ))}
      </div>
      <div className="button-row compact-actions">
        <button
          className="secondary-button compact-button"
          disabled={factor.levels.length >= 10}
          onClick={() => changeGeneralLevelCount(factor, factor.levels.length + 1, setFactors)}
          type="button"
        >
          수준 추가
        </button>
        {factor.levelType === "numeric" ? (
          <button
            className="secondary-button compact-button"
            disabled={!canCalculateMidpoint}
            onClick={() => calculateGeneralMidpoint(factor, setFactors)}
            type="button"
          >
            중간값 자동 계산
          </button>
        ) : null}
      </div>
      <div className="general-factorial-paste-editor">
        <label htmlFor={`${factor.id}-paste`}>수준 붙여넣기</label>
        <textarea
          id={`${factor.id}-paste`}
          placeholder={"A\nB\nC 또는 A, B, C"}
          rows={3}
          value={factor.pasteDraft}
          onChange={(event) =>
            updateGeneralFactor(
              factor.id,
              { pasteDraft: event.currentTarget.value },
              setFactors,
            )
          }
        />
        <div className="button-row compact-actions">
          <span>{pastedLevels.length}개 수준 미리보기</span>
          <button
            className="secondary-button compact-button"
            disabled={!canApplyPaste}
            onClick={() =>
              updateGeneralFactor(
                factor.id,
                { levels: pastedLevels, pasteDraft: "" },
                setFactors,
              )
            }
            type="button"
          >
            붙여넣기 적용
          </button>
        </div>
      </div>
    </section>
  );
}

function GeneralFactorialResult({ analysis, design, onAnalyze, onSave, pending, responseName, responseUnit, responses, setResponseName, setResponses, setResponseUnit, locked, correctionMode, onCorrection, analysisSettings, canAnalyze }: {
  locked: boolean;
  correctionMode: boolean;
  onCorrection: () => void;
  analysisSettings: import("react").ReactNode;
  canAnalyze: boolean;
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
    <DoeResponsePasteDialog runOrders={design.runs.map((run) => run.run_order)} disabled={locked || pending !== null} onApply={setResponses} />
    <DoeSettingsTable ariaLabel="일반 완전요인 반응 설정" fields={[
      { key: "response", label: "반응 이름", controlId: "general-factorial-response", control: <input id="general-factorial-response" disabled={locked || correctionMode} value={responseName} onChange={(event) => setResponseName(event.currentTarget.value)} /> },
      { key: "unit", label: "반응 단위", controlId: "general-factorial-response-unit", control: <input id="general-factorial-response-unit" disabled={locked} value={responseUnit} onChange={(event) => setResponseUnit(event.currentTarget.value)} /> },
    ]} />
    <div className="table-wrap"><table className="result-table"><thead><tr><th>Run</th>{design.factors.map((factor) => <th key={factor.name}>{factor.name}</th>)}<th>반응</th></tr></thead><tbody>{design.runs.map((run) => <tr key={run.run_order}><td>{run.run_order}</td>{design.factors.map((factor) => <td key={factor.name}>{String(run.factor_levels[factor.name])}</td>)}<td><input aria-label={`run ${run.run_order} 반응`} disabled={locked} inputMode="decimal" value={responses[run.run_order] ?? ""} onChange={(event) => {
      const value = event.currentTarget.value;
      setResponses((current) => ({ ...current, [run.run_order]: value }));
    }} /></td></tr>)}</tbody></table></div>
    {locked ? <><p className="notice-box notice-warning">{t("doe.response.locked")}</p><button className="secondary-button" type="button" disabled={pending !== null} onClick={onCorrection}>{t("doe.response.correct")}</button></> : null}
    {correctionMode ? <p className="notice-box notice-warning">{t("doe.response.draft")}</p> : null}
    {analysisSettings}
    <DoeActionBar summary="반응 저장 후 범주형 term-block ANOVA를 실행합니다."><button className="secondary-button" disabled={pending !== null || locked} onClick={onSave} type="button">{pending === "save" ? "저장 중" : "반응 저장"}</button><button className="primary-button" disabled={pending !== null || !canAnalyze} onClick={onAnalyze} type="button">{pending === "analysis" ? "분석 중" : "일반 완전요인 ANOVA"}</button></DoeActionBar>
    {analysis?.result.final_model && analysis.result.model_selection ? <FactorialModelSelectionResults selection={analysis.result.model_selection} model={analysis.result.final_model} fit={analysis.result.fit} n={analysis.result.sample.n_observations} /> : null}
    {analysis !== null ? <GeneralFactorialAnalysisView analysis={analysis} /> : null}
    {analysis?.result.final_model ? <><FactorialResidualPlots plots={analysis.result.final_model.residual_plots} /><FactorialPlotsPanel model={analysis.result.final_model} design={design} /></> : null}
    {analysis ? <FactorialStoredModelWorkflow design={design} analysisId={analysis.analysis_id} model={analysis.result.final_model} /> : null}
  </section>;
}

function GeneralFactorialAnalysisView({ analysis }: { analysis: GeneralFactorialAnalysisResponse }) {
  return <section className="result-section"><h3>분산분석</h3><div className="metadata-grid"><span>R²</span><strong>{(analysis.result.fit.r_squared * 100).toFixed(2)}%</strong><span>Adjusted R²</span><strong>{analysis.result.fit.adjusted_r_squared === null ? "-" : `${(analysis.result.fit.adjusted_r_squared * 100).toFixed(2)}%`}</strong><span>Residual DF</span><strong>{analysis.result.sample.df_residual}</strong><span>Coding</span><strong>Treatment</strong></div><div className="table-wrap"><table className="result-table"><thead><tr><th>Source</th><th>DF</th><th>Adj SS</th><th>Adj MS</th><th>F</th><th>P</th></tr></thead><tbody>{analysis.result.anova.rows.map((row) => <tr key={row.term_id}><td>{row.source}</td><td>{row.df}</td><td>{formatNumber(row.adjusted_sum_squares)}</td><td>{formatNumber(row.adjusted_mean_square)}</td><td>{formatNumber(row.f_statistic)}</td><td>{formatNumber(row.p_value)}</td></tr>)}</tbody></table></div>{analysis.result.warnings.map((warning) => <div className="notice-box notice-warning" key={warning}>{factorialWorkflowMessage(warning)}</div>)}</section>;
}

function updateGeneralFactor(
  id: string,
  patch: Partial<GeneralFactorDraft>,
  setter: Dispatch<SetStateAction<GeneralFactorDraft[]>>,
) {
  setter((current) =>
    current.map((factor) => (factor.id === id ? { ...factor, ...patch } : factor)),
  );
}

function updateGeneralLevel(id: string, index: number, value: string, setter: Dispatch<SetStateAction<GeneralFactorDraft[]>>) {
  setter((current) => current.map((factor) => {
    if (factor.id !== id) return factor;
    const levels = [...factor.levels];
    levels[index] = value;
    return { ...factor, levels };
  }));
}

function moveGeneralLevel(id: string, fromIndex: number, toIndex: number, setter: Dispatch<SetStateAction<GeneralFactorDraft[]>>) {
  setter((current) => current.map((factor) => {
    if (factor.id !== id || toIndex < 0 || toIndex >= factor.levels.length) return factor;
    const levels = [...factor.levels];
    [levels[fromIndex], levels[toIndex]] = [levels[toIndex], levels[fromIndex]];
    return { ...factor, levels };
  }));
}

function changeGeneralLevelCount(factor: GeneralFactorDraft, requestedCount: number, setter: Dispatch<SetStateAction<GeneralFactorDraft[]>>) {
  const nextCount = Math.max(2, Math.min(10, requestedCount));
  if (nextCount < factor.levels.length) {
    const removed = factor.levels.slice(nextCount).filter((level) => level.trim() !== "");
    if (
      removed.length > 0 &&
      !window.confirm(
        resolveLocalizedText(`제거될 수준: ${removed.join(", ")}\n계속하시겠습니까?`),
      )
    ) return;
  }
  const levels = factor.levels.slice(0, nextCount);
  while (levels.length < nextCount) levels.push("");
  updateGeneralFactor(factor.id, { levels, expanded: true }, setter);
}

function applyThreeLevelPreset(factors: GeneralFactorDraft[], setter: Dispatch<SetStateAction<GeneralFactorDraft[]>>) {
  if (
    factors.some((factor) => factor.levels.length > 3) &&
    !window.confirm(
      resolveLocalizedText("3수준으로 줄이면 일부 중간 수준이 제거됩니다. 계속하시겠습니까?"),
    )
  ) return;
  setter((current) => current.map((factor) => {
    if (factor.levels.length === 3) return factor;
    return { ...factor, levels: threeLevelPresetLevels(factor.levels), expanded: true };
  }));
}

function calculateGeneralMidpoint(factor: GeneralFactorDraft, setter: Dispatch<SetStateAction<GeneralFactorDraft[]>>) {
  const low = Number(factor.levels[0]);
  const high = Number(factor.levels[2]);
  if (!Number.isFinite(low) || !Number.isFinite(high)) return;
  const levels = [...factor.levels];
  levels[1] = String((low + high) / 2);
  updateGeneralFactor(factor.id, { levels }, setter);
}

function formatNumber(value: number | null): string { return value === null ? "-" : Number(value.toPrecision(6)).toString(); }
