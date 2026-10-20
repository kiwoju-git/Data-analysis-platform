import { ResponseSurfaceGrid } from "./charts/ResponseSurfaceGrid";
import { RsmPlotOptions } from "./doe/RsmPlotOptions";
import { DoeLackOfFitNotice } from "./doe/DoeLackOfFitNotice";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import {
  createDoeResponseRevision,
  createResponseSurfaceAnalysis,
  createResponseSurfaceDesign,
  fetchDoeResponseRevisions,
  fetchDoeResponseRevision,
  fetchResponseSurfaceDesign,
  fetchResponseSurfaceAnalysis,
  saveResponseSurfaceResponses,
  type DoeResponseRevisionHistoryResponse,
  type DoeResponseSurfaceAnalysisResponse,
  type ResponseSurfaceDesignCreateRequest,
  type ResponseSurfaceDesignResponse,
} from "./api";
import {
  DoeActionBar,
  DoeAdvancedSettings,
  DoeFactorEditor,
  DoeFormSection,
} from "./doe/DoeFormPrimitives";
import { DoeFactorCountControl } from "./doe/DoeFactorCountControl";
import { DoeSettingsTable } from "./doe/DoeSettingsTable";
import { DOE_FACTOR_CAPABILITIES } from "./doe/factorCapabilities";
import {
  continuousFactorDomainDraft,
  formatDoeFactorValue,
  parseDoeFactorDomainDraft,
  type DoeFactorDomainDraft,
} from "./doe/factorDomain";
import { ResponseOptimizerPanel } from "./ResponseOptimizerPanel";
import { parseRsmResponseDraft } from "./doe/rsmResponseDraft";
import { createRsmRequestContext } from "./doe/rsmRequestContext";
import { t } from "./i18n/translate";
import { recommendedCenterPoints, strictRsmInteger, type CcdType } from "./doe/rsmDesignDraft";
import { parseDoeResponseNumber } from "./doe/doeResponsePaste";
import { RsmModelTerms, useRsmTermCatalog } from "./doe/RsmModelTerms";
import { DoeModelSelectionSettings } from "./doe/DoeModelSelectionSettings";
import { RsmModelSelectionResults } from "./doe/RsmModelSelectionResults";
import type { RsmTermPreset } from "./api/types/doe";
import type { DoeModelSelectionOptions } from "./api/types/doeModelWorkflow";
import { CcdBoundsPreview } from "./doe/CcdBoundsPreview";

interface FactorDraft extends DoeFactorDomainDraft {
  id: number;
  name: string;
  low: string;
  high: string;
  unit: string;
}

const maxFactorCount = DOE_FACTOR_CAPABILITIES.responseSurfaceCcd;

export function ResponseSurfacePanel() {
  const [name, setName] = useState("Central composite process window");
  const [factors, setFactors] = useState<FactorDraft[]>([
    { id: 1, name: "Temperature", low: "60", high: "80", unit: "C", ...continuousFactorDomainDraft },
    { id: 2, name: "Pressure", low: "5", high: "15", unit: "bar", ...continuousFactorDomainDraft },
  ]);
  const [ccdType, setCcdType] = useState<CcdType>("inscribed");
  const [axialConfirmed, setAxialConfirmed] = useState(false);
  const [centerMode, setCenterMode] = useState<"recommended" | "custom">("recommended");
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
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [requests] = useState(createRsmRequestContext);
  const [termPreset, setTermPreset] = useState<RsmTermPreset>("full_quadratic");
  const [selection, setSelection] = useState<DoeModelSelectionOptions>({
    method: "none", alpha_to_remove: 0.05, hierarchy_policy: "strong",
    saturated_start_policy: "pool_smallest_adjusted_ss", display_step_details: true, term_policies: [],
  });
  const [confidence, setConfidence] = useState(0.95);
  const termState = useRsmTermCatalog(design?.design_id ?? null, termPreset, selection);
  const [isRestoring, setIsRestoring] = useState(false);
  const [historicalRevision, setHistoricalRevision] = useState(false);
  const nextFactorId = useRef(3);
  const [savedRoute, setSavedRoute] = useState(() =>
    typeof window === "undefined" ? "" : window.location.search);

  useEffect(() => {
    const update = () => setSavedRoute(window.location.search);
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);

  useEffect(() => {
    requests.invalidate();
    setIsRestoring(false);
    setIsCreating(false);
    setIsSaving(false);
    setIsAnalyzing(false);
    setIsLoadingHistory(false);
    setError(null);
    const query = new URLSearchParams(savedRoute);
    const designId = query.get("design_id");
    const analysisId = query.get("analysis_id");
    if (!designId || !analysisId) return;
    const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuid.test(designId) || !uuid.test(analysisId)) {
      setAnalysis(null);
      setError("doe_rsm_analysis_link_invalid");
      return;
    }
    const pending = requests.begin("restore", { designId, analysisId });
    setAnalysis(null); setIsCreating(false); setIsSaving(false);
    setIsAnalyzing(false); setIsLoadingHistory(false);
    setIsRestoring(true);
    void (async () => {
      try {
        const source = await fetchResponseSurfaceDesign(designId);
        const stored = await fetchResponseSurfaceAnalysis(designId, analysisId);
        const revision = await fetchDoeResponseRevision(designId, stored.response_revision_id);
        if (!requests.isCurrent(pending)) return;
        if (stored.design_id !== source.design_id || stored.design_sha256 !== source.design_sha256 ||
          stored.design_version_id !== source.design_version_id || revision.state !== "completed" ||
          revision.design_version_id !== source.design_version_id ||
          revision.response_revision_sha256 !== stored.response_revision_sha256) {
          throw new Error("doe_rsm_analysis_dependency_mismatch");
        }
        setDesign(source); setAnalysis(stored); setName(source.name);
        setFactors(source.factors.map((factor, index) => ({
          id: index + 1, name: factor.name, low: String(factor.low), high: String(factor.high),
          unit: factor.unit ?? "", domainKind: factor.domain_kind ?? "continuous",
          step: factor.step == null ? "" : String(factor.step),
          displayDecimals: factor.display_decimals == null ? "" : String(factor.display_decimals),
        })));
        nextFactorId.current = source.factors.length + 1;
        setCcdType(source.options.ccd_type ??
          (source.options.alpha_mode === "face_centered" ? "face_centered" : "inscribed"));
        setAxialConfirmed(source.options.ccd_type === "circumscribed");
        setCenterMode("custom"); setCenterPoints(String(source.options.center_points));
        setRandomize(source.options.randomize); setRandomizationSeed(String(source.options.randomization_seed));
        setResponseName(revision.response_name); setResponseUnit(revision.unit ?? "");
        setResponseValues(Object.fromEntries(revision.values.map((row) => [row.run_order, String(row.value)])));
        setResponseRevisionId(revision.response_revision_id);
        setResponseRevisionNumber(revision.revision_number);
        setResponseRevisionSha256(revision.response_revision_sha256);
        setResponsesSaved(true); setHistoricalRevision(true); setCorrectionMode(false);
        setTermPreset(stored.result.term_preset ?? "full_quadratic");
        if (stored.result.model_selection) {
          const chosen = stored.result.model_selection;
          setSelection({ method: chosen.method, alpha_to_remove: chosen.alpha_to_remove,
            hierarchy_policy: chosen.hierarchy_policy, saturated_start_policy: "pool_smallest_adjusted_ss",
            display_step_details: chosen.display_step_details, term_policies: chosen.term_policies });
        } else {
          setSelection({
            method: "none", alpha_to_remove: 0.05, hierarchy_policy: "strong",
            saturated_start_policy: "pool_smallest_adjusted_ss",
            display_step_details: true, term_policies: [],
          });
        }
        setConfidence(stored.result.terms.find((term) => term.confidence_interval)?.confidence_interval?.level ?? 0.95);
        setError(null);
        try {
          const history = await fetchDoeResponseRevisions(designId, revision.response_name);
          if (requests.isCurrent(pending)) { setRevisionHistory(history); setHistoryError(null); }
        } catch (caught) {
          if (requests.isCurrent(pending)) setHistoryError(errorCode(caught));
        }
      } catch (caught) {
        if (requests.isCurrent(pending)) setError(errorCode(caught));
      } finally {
        if (requests.isCurrent(pending)) setIsRestoring(false);
      }
    })();
    return () => requests.invalidateLane("restore");
  }, [savedRoute, requests]);

  useEffect(
    () => () => requests.invalidate(),
    [requests],
  );

  function invalidateSource(responseChanged = false) {
    requests.invalidate();
    setIsCreating(false);
    setIsSaving(false);
    setIsAnalyzing(false);
    setIsLoadingHistory(false);
    setIsRestoring(false);
    setError(null);
    setHistoryError(null);
    if (responseChanged) {
      setResponsesSaved(false);
      setAnalysis(null);
    }
  }

  const estimatedRunCount = useMemo(() => {
    const center = strictRsmInteger(centerPoints);
    return center !== null ? 2 ** factors.length + 2 * factors.length + center : 0;
  }, [centerPoints, factors.length]);

  function resizeFactors(count: number) {
    invalidateSource();
    setAxialConfirmed(false);
    if (centerMode === "recommended") setCenterPoints(String(recommendedCenterPoints(count) ?? ""));
    setFactors((current) => {
      if (count <= current.length) return current.slice(0, count);
      const next = [...current];
      while (next.length < count) {
        const id = nextFactorId.current++;
        next.push({
          id,
          name: `Factor ${next.length + 1}`,
          low: "-1",
          high: "1",
          unit: "",
          ...continuousFactorDomainDraft,
        });
      }
      return next;
    });
  }

  function changeFactor(id: number, key: keyof Omit<FactorDraft, "id">, value: string) {
    invalidateSource();
    setAxialConfirmed(false);
    updateFactor(setFactors, id, key, value);
  }

  const createDesign = async () => {
    const request = designRequest({
      name,
      factors,
      ccdType,
      axialConfirmed,
      centerPoints,
      centerMode,
      randomize,
      randomizationSeed,
    });
    if (typeof request === "string") {
      setError(request);
      return;
    }
    invalidateSource();
    const pending = requests.begin("create", request);
    setIsCreating(true);
    setError(null);
    try {
      const created = await createResponseSurfaceDesign(pending.snapshot);
      if (!requests.isCurrent(pending)) return;
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
      setHistoricalRevision(false);
      setSelection((current) => ({ ...current, term_policies: [] }));
      setResponseValues(Object.fromEntries(created.runs.map((run) => [run.run_order, ""])));
    } catch (caught) {
      if (requests.isCurrent(pending)) setError(errorCode(caught));
    } finally {
      if (requests.isCurrent(pending)) setIsCreating(false);
    }
  };

  const loadHistory = async (sourceDesign = design, name = responseName.trim()) => {
    if (sourceDesign === null || !name) return;
    const pending = requests.begin("history", {
      designId: sourceDesign.design_id,
      designSha256: sourceDesign.design_sha256,
      responseName: name,
    });
    setHistoryError(null);
    setIsLoadingHistory(true);
    try {
      const history = await fetchDoeResponseRevisions(
        pending.snapshot.designId, pending.snapshot.responseName,
      );
      if (requests.isCurrent(pending)) setRevisionHistory(history);
    } catch (caught) {
      if (requests.isCurrent(pending)) setHistoryError(errorCode(caught));
    } finally {
      if (requests.isCurrent(pending)) setIsLoadingHistory(false);
    }
  };

  const saveResponses = async () => {
    if (design === null) return;
    const trimmedName = responseName.trim();
    if (trimmedName.length === 0) {
      setError("doe_rsm_response_name_required");
      return;
    }
    const parsed = parseRsmResponseDraft(design.runs.map((run) => run.run_order), responseValues);
    if (!parsed.ok) {
      setError(parsed.code);
      return;
    }
    invalidateSource(true);
    const pending = requests.begin("save", {
      designId: design.design_id,
      designVersionId: design.design_version_id,
      designSha256: design.design_sha256,
      previousRevisionId: responseRevisionId,
      previousRevisionSha256: responseRevisionSha256,
      correctionMode,
      payload: {
        response_name: trimmedName,
        unit: responseUnit.trim() || null,
        values: parsed.values,
      },
    });
    setIsSaving(true);
    setError(null);
    try {
      const stored = pending.snapshot.correctionMode
        ? await createDoeResponseRevision(pending.snapshot.designId, {
            ...pending.snapshot.payload,
            supersedes_response_revision_id: pending.snapshot.previousRevisionId,
          })
        : await saveResponseSurfaceResponses(pending.snapshot.designId, pending.snapshot.payload);
      if (!requests.isCurrent(pending)) return;
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
      void loadHistory(design, pending.snapshot.payload.response_name);
    } catch (caught) {
      if (requests.isCurrent(pending)) setError(errorCode(caught));
    } finally {
      if (requests.isCurrent(pending)) setIsSaving(false);
    }
  };

  const runAnalysis = async () => {
    if (design === null || !responsesSaved || !termState.ready) return;
    if (!(confidence > 0 && confidence < 1) || !(selection.alpha_to_remove > 0 && selection.alpha_to_remove < 1)) {
      setError("doe_rsm_confidence_or_selection_invalid");
      return;
    }
    const pending = requests.begin("analyze", {
      designId: design.design_id,
      designVersionId: design.design_version_id,
      designSha256: design.design_sha256,
      responseRevisionSha256,
      payload: {
        response_name: responseName.trim(),
        response_revision_id: responseRevisionId,
        confidence_level: confidence,
        point_limit: 256,
        contour_grid_size: 21,
        term_preset: termPreset,
        model_selection: { ...termState.options, saturated_start_policy: "require_positive_residual_df" as const },
      },
    });
    setIsAnalyzing(true);
    setError(null);
    try {
      const created = await createResponseSurfaceAnalysis(
        pending.snapshot.designId, pending.snapshot.payload,
      );
      if (!requests.isCurrent(pending)) return;
      setAnalysis(created);
      setDesign((current) => (current === null ? null : { ...current, status: "analyzed" }));
    } catch (caught) {
      if (requests.isCurrent(pending)) setError(errorCode(caught));
    } finally {
      if (requests.isCurrent(pending)) setIsAnalyzing(false);
    }
  };

  function changeModel() {
    invalidateSource();
    setAnalysis(null);
  }

  async function restoreRevision(revisionId: string) {
    if (!design) return;
    invalidateSource(true);
    const pending = requests.begin("restore", {
      designId: design.design_id, designVersionId: design.design_version_id,
      designSha256: design.design_sha256, revisionId,
    });
    setIsRestoring(true);
    try {
      const restored = await fetchDoeResponseRevision(pending.snapshot.designId, pending.snapshot.revisionId);
      if (!requests.isCurrent(pending)) return;
      if (restored.design_version_id !== pending.snapshot.designVersionId || restored.state !== "completed") {
        setError("doe_rsm_response_revision_invalid");
        return;
      }
      setResponseName(restored.response_name);
      setResponseUnit(restored.unit ?? "");
      setResponseValues(Object.fromEntries(restored.values.map((row) => [row.run_order, String(row.value)])));
      setResponseRevisionId(restored.response_revision_id);
      setResponseRevisionNumber(restored.revision_number);
      setResponseRevisionSha256(restored.response_revision_sha256);
      setResponsesSaved(true);
      setCorrectionMode(false);
      setHistoricalRevision(true);
    } catch (caught) {
      if (requests.isCurrent(pending)) setError(errorCode(caught));
    } finally {
      if (requests.isCurrent(pending)) setIsRestoring(false);
    }
  }

  return (
    <section className="analysis-run-panel" aria-label="반응표면법 설계와 분석 입력">
      <DoeFormSection
        title="설계 기본 설정"
        description="반응표면 설계 방식과 센터점 수를 정합니다."
      >
        <DoeSettingsTable
          ariaLabel="RSM 설계 기본 설정"
          fields={[
            {
              key: "name",
              label: "설계 이름",
              controlId: "rsm-design-name",
              control: (
                <input
                  id="rsm-design-name"
                  value={name}
                  onChange={(event) => { invalidateSource(); setName(event.currentTarget.value); }}
                />
              ),
            },
            {
              key: "alpha-mode",
              label: "CCD 방식",
              controlId: "rsm-alpha-mode",
              control: (
                <select
                  id="rsm-alpha-mode"
                  value={ccdType}
                  onChange={(event) => {
                    invalidateSource();
                    setCcdType(event.currentTarget.value as CcdType);
                    setAxialConfirmed(false);
                  }}
                >
                  <option value="inscribed">CCI — Inscribed</option>
                  <option value="circumscribed">CCC — Circumscribed</option>
                  <option value="face_centered">CCF — Face-centered</option>
                </select>
              ),
            },
            {
              key: "center-points",
              label: "센터점",
              controlId: "rsm-center-points",
              control: (
                <input
                  id="rsm-center-points"
                  inputMode="numeric"
                  value={centerPoints}
                  onChange={(event) => { invalidateSource(); setCenterMode("custom"); setCenterPoints(event.currentTarget.value); }}
                />
              ),
            },
          ]}
        />
        <div className="button-row">
          <label><span>{t("doe.rsm.centerMode")}</span><select value={centerMode} onChange={(event) => {
            invalidateSource();
            const mode = event.currentTarget.value as "recommended" | "custom";
            setCenterMode(mode);
            if (mode === "recommended") setCenterPoints(String(recommendedCenterPoints(factors.length) ?? ""));
          }}><option value="recommended">{t("doe.rsm.recommended")}</option><option value="custom">{t("doe.rsm.custom")}</option></select></label>
          <button type="button" className="secondary-button" onClick={() => {
            invalidateSource(); setCenterMode("recommended");
            setCenterPoints(String(recommendedCenterPoints(factors.length) ?? ""));
          }}>{t("doe.rsm.applyCenters")}</button>
        </div>
        <p className="field-help">{t("doe.rsm.centerPolicy", { count: recommendedCenterPoints(factors.length) ?? "-" })}</p>
        <DoeAdvancedSettings
          summaryText={`seed ${randomizationSeed} · ${randomize ? "실행 순서 무작위화" : "표준 순서"}`}
        >
          <DoeSettingsTable
            ariaLabel="RSM 고급 설정"
            fields={[
              {
                key: "seed",
                label: "무작위화 seed",
                controlId: "rsm-randomization-seed",
                control: (
                  <input
                    id="rsm-randomization-seed"
                    inputMode="numeric"
                    value={randomizationSeed}
                    onChange={(event) => { invalidateSource(); setRandomizationSeed(event.currentTarget.value); }}
                  />
                ),
              },
              {
                key: "randomize",
                label: "실행 순서 무작위화",
                controlId: "rsm-randomize",
                control: (
                  <label className="doe-table-toggle" htmlFor="rsm-randomize">
                    <input
                      id="rsm-randomize"
                      type="checkbox"
                      checked={randomize}
                      onChange={(event) => { invalidateSource(); setRandomize(event.currentTarget.checked); }}
                    />
                    <span>사용</span>
                  </label>
                ),
              },
            ]}
          />
        </DoeAdvancedSettings>
      </DoeFormSection>

      <DoeFactorEditor
        action={
          <div className="doe-factor-editor-actions">
            <DoeFactorCountControl
              count={factors.length}
              factorLabels={factors.map((factor) => factor.name)}
              maximum={maxFactorCount}
              minimum={2}
              onResize={resizeFactors}
            />
            <button
              type="button"
              className="secondary-button"
              disabled={factors.length >= maxFactorCount}
              onClick={() => resizeFactors(factors.length + 1)}
            >
              요인 추가
            </button>
          </div>
        }
      >
      <div className="notice-box">
        현재 Central Composite Design은 최대 5개의 연속형 요인을 지원합니다.
        더 많은 요인은 Screening Design 또는 LHS로 먼저 탐색한 뒤 중요 요인을 선택하세요.
      </div>
      <div className="table-wrap">
        <table className="result-table doe-factor-table">
          <colgroup>
            <col className="doe-factor-name-column" />
            <col className="doe-factor-bound-column" />
            <col className="doe-factor-bound-column" />
            <col className="doe-factor-domain-column" />
            <col className="doe-factor-bound-column" />
            <col className="doe-factor-bound-column" />
            <col className="doe-factor-unit-column" />
            <col className="doe-factor-action-column" />
          </colgroup>
          <thead>
            <tr>
              <th>요인</th>
              <th>설계 하한</th>
              <th>설계 상한</th>
              <th>설정 방식</th>
              <th>실행 간격</th>
              <th>표시 자리수</th>
              <th>단위</th>
              <th className="doe-factor-action-cell">작업</th>
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
                      changeFactor(factor.id, "name", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `요인 ${index + 1}`} 하한`}
                    inputMode="decimal"
                    value={factor.low}
                    onChange={(event) =>
                      changeFactor(factor.id, "low", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `요인 ${index + 1}`} 상한`}
                    inputMode="decimal"
                    value={factor.high}
                    onChange={(event) =>
                      changeFactor(factor.id, "high", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <select
                    aria-label={`${factor.name || `요인 ${index + 1}`} 설정 방식`}
                    value={factor.domainKind ?? "continuous"}
                    onChange={(event) =>
                      changeFactor(factor.id, "domainKind", event.currentTarget.value)
                    }
                  >
                    <option value="continuous">연속형</option>
                    <option value="discrete_numeric">일정 간격 숫자</option>
                  </select>
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `요인 ${index + 1}`} 실행 간격`}
                    disabled={(factor.domainKind ?? "continuous") === "continuous"}
                    inputMode="decimal"
                    placeholder="-"
                    value={factor.step ?? ""}
                    onChange={(event) =>
                      changeFactor(factor.id, "step", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `요인 ${index + 1}`} 표시 자리수`}
                    inputMode="numeric"
                    placeholder="자동"
                    value={factor.displayDecimals ?? ""}
                    onChange={(event) =>
                      changeFactor(factor.id, "displayDecimals", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `요인 ${index + 1}`} 단위`}
                    value={factor.unit}
                    onChange={(event) =>
                      changeFactor(factor.id, "unit", event.currentTarget.value)
                    }
                  />
                </td>
                <td className="doe-factor-action-cell">
                  <button
                    type="button"
                    className="secondary-button compact-button"
                    disabled={factors.length <= 2}
                    onClick={() => {
                      invalidateSource();
                      setAxialConfirmed(false);
                      if (centerMode === "recommended") setCenterPoints(String(recommendedCenterPoints(factors.length - 1) ?? ""));
                      setFactors((current) => current.filter((item) => item.id !== factor.id));
                    }}
                  >
                    제거
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </DoeFactorEditor>
      <p className="field-help">{t(ccdType === "circumscribed" ? "doe.rsm.cccBounds" : "doe.rsm.axialBounds")}</p>
      <CcdBoundsPreview factors={factors} ccdType={ccdType} />
      {ccdType === "circumscribed" ? <label className="doe-table-toggle"><input type="checkbox"
        checked={axialConfirmed} onChange={(event) => { invalidateSource(); setAxialConfirmed(event.currentTarget.checked); }} />
        <span>{t("doe.rsm.confirmAxial")}</span></label> : null}
      <DoeActionBar summary={`예상 실험 ${estimatedRunCount}개`}>
        <button
          type="button"
          className="primary-button"
          disabled={isCreating || (ccdType === "circumscribed" && !axialConfirmed)}
          onClick={() => void createDesign()}
        >
          {isCreating ? "생성 중" : "CCD 생성"}
        </button>
      </DoeActionBar>
      <div className="metadata-grid" aria-label="반응표면 설계 입력 요약">
        <span>예상 run</span>
        <strong>{estimatedRunCount}</strong>
        <span>요인 수</span>
        <strong>{factors.length}</strong>
        <span>모형 정책</span>
        <strong>{t(`doe.rsm.preset.${termPreset}`)}</strong>
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
          historyError={historyError}
          isLoadingHistory={isLoadingHistory}
          onRetryHistory={() => void loadHistory()}
          correctionMode={correctionMode}
          isSaving={isSaving}
          isAnalyzing={isAnalyzing}
          canAnalyze={termState.ready && !isRestoring}
          historicalRevision={historicalRevision}
          onSelectRevision={(id) => void restoreRevision(id)}
          isRestoring={isRestoring}
          modelSettings={<>
            <RsmModelTerms preset={termPreset} state={termState} options={selection}
              onPresetChange={(preset) => { changeModel(); setTermPreset(preset); setSelection((current) => ({ ...current, term_policies: [] })); }}
              onOptionsChange={(options) => { changeModel(); setSelection(options); }} />
            <DoeModelSelectionSettings modelKind="rsm" value={selection} confidence={confidence}
              onChange={(options) => { changeModel(); setSelection(options); }}
              onConfidenceChange={(value) => { changeModel(); setConfidence(value); }} />
          </>}
          onResponseNameChange={(value) => {
            invalidateSource(true);
            setResponseName(value);
          }}
          onResponseUnitChange={(value) => {
            invalidateSource(true);
            setResponseUnit(value);
          }}
          onResponseValueChange={(runOrder, value) => {
            invalidateSource(true);
            setResponseValues((current) => ({ ...current, [runOrder]: value }));
          }}
          onStartCorrection={() => {
            invalidateSource(true);
            setCorrectionMode(true);
            setHistoricalRevision(false);
            void loadHistory();
          }}
          onSave={() => void saveResponses()}
          onAnalyze={() => void runAnalysis()}
        />
      ) : null}
      {analysis !== null && design !== null ? (
        <>
          <ResponseSurfaceResult analysis={analysis} design={design} />
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
  historyError?: string | null;
  isLoadingHistory?: boolean;
  onRetryHistory?: () => void;
  correctionMode: boolean;
  isSaving: boolean;
  isAnalyzing: boolean;
  onResponseNameChange: (value: string) => void;
  onResponseUnitChange: (value: string) => void;
  onResponseValueChange: (runOrder: number, value: string) => void;
  onStartCorrection: () => void;
  onSave: () => void;
  onAnalyze: () => void;
  modelSettings?: ReactNode;
  canAnalyze?: boolean;
  historicalRevision?: boolean;
  isRestoring?: boolean;
  onSelectRevision?: (revisionId: string) => void;
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
  historyError = null,
  isLoadingHistory = false,
  onRetryHistory,
  correctionMode,
  isSaving,
  isAnalyzing,
  onResponseNameChange,
  onResponseUnitChange,
  onResponseValueChange,
  onStartCorrection,
  onSave,
  onAnalyze,
  modelSettings, canAnalyze = true, historicalRevision = false, isRestoring = false, onSelectRevision,
}: ResponseEntryProps) {
  const responsesLocked = (design.status === "analyzed" || historicalRevision) && !correctionMode;
  return (
    <section className="analysis-result-section" aria-labelledby="rsm-response-title" data-rsm-response-entry>
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
        <strong>{t(design.options.ccd_type === "circumscribed" ? "doe.rsm.storedCubeBounds" : "doe.rsm.storedAxialBounds")}</strong>
        <span>{t("doe.rsm.centerMode")}</span>
        <strong>{design.options.center_points} ({t(design.options.center_point_mode === "recommended" ? "doe.rsm.recommended" : "doe.rsm.custom")})</strong>
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
                  <td key={factor.name}>
                    {formatDoeFactorValue(
                      run.factor_levels[factor.name],
                      factor.display_decimals,
                    )}
                  </td>
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
      {modelSettings}
      <div className="button-row">
        <button
          type="button"
          className="secondary-button"
          disabled={isSaving || responsesLocked}
          onClick={onSave}
        >
          {isSaving ? "저장 중" : correctionMode ? "새 revision 저장" : "반응 저장"}
        </button>
        {(responseRevisionNumber !== null || design.status === "analyzed" || historicalRevision) && !correctionMode ? (
          <button type="button" className="secondary-button" onClick={onStartCorrection}>
            새 revision으로 수정
          </button>
        ) : null}
        <button
          type="button"
          className="primary-button"
          disabled={!responsesSaved || isAnalyzing || !canAnalyze}
          onClick={onAnalyze}
        >
          {isAnalyzing ? "분석 중" : t("doe.rsm.fitModel")}
        </button>
      </div>
      {historyError !== null ? (
        <div className="notice-box notice-warning" role="status">
          <p>{t("doe.rsm.historyFailure")}</p>
          <code>{historyError}</code>
          <button type="button" className="secondary-button" disabled={isLoadingHistory} onClick={onRetryHistory}>
            {t("doe.rsm.retryHistory")}
          </button>
        </div>
      ) : null}
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
                  <td>{onSelectRevision ? <button type="button" className="secondary-button"
                    disabled={isRestoring || revision.state !== "completed"}
                    onClick={() => onSelectRevision(revision.response_revision_id)}>
                    r{revision.revision_number}</button> : `r${revision.revision_number}`}</td>
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

function ResponseSurfaceResult({ analysis, design }: {
  analysis: DoeResponseSurfaceAnalysisResponse; design: ResponseSurfaceDesignResponse;
}) {
  const { result } = analysis;
  const stationary = result.stationary_point;
  return (
    <section className="analysis-result-section" aria-labelledby="rsm-result-title">
      <div className="panel-heading compact-heading">
        <div>
          <h4 id="rsm-result-title">{t("doe.rsm.resultTitle")}</h4>
          <p>{analysis.method_id} v{analysis.method_version}</p>
        </div>
        <span className="status-pill status-ready">검증 저장됨</span>
      </div>
      {result.model_selection ? <RsmModelSelectionResults result={result} /> : null}
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
      ) : <p className="notice-box">{t("doe.rsm.stationaryUnavailable")}</p>}
      <div className="chart-panel">
        <span className="chart-panel-title">예측 contour</span>
        {result.plot_bundle ? <RsmPlotOptions key={analysis.analysis_id} analysis={analysis} design={design} />
          : <ResponseSurfaceGrid analysis={analysis} />}
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
      <DoeLackOfFitNotice lack={result.anova.lack_of_fit} />
      {result.warnings.map((warning) => (
        <div className="notice-box notice-warning" key={warning}>{warning === "doe_rsm_post_selection_inference_exploratory" ? t("doe.selection.exploratory") : warning}</div>
      ))}
    </section>
  );
}

function designRequest(input: {
  name: string;
  factors: FactorDraft[];
  ccdType: CcdType;
  axialConfirmed: boolean;
  centerPoints: string;
  centerMode: "recommended" | "custom";
  randomize: boolean;
  randomizationSeed: string;
}): ResponseSurfaceDesignCreateRequest | string {
  const centerPoints = strictRsmInteger(input.centerPoints);
  const seed = strictRsmInteger(input.randomizationSeed);
  if (centerPoints === null || centerPoints < 1 || centerPoints > 32) {
    return "doe_rsm_center_points_invalid";
  }
  if (seed === null || seed > 2_147_483_647) return "doe_rsm_seed_invalid";
  if (input.ccdType === "circumscribed" && !input.axialConfirmed) return "doe_rsm_axial_confirmation_required";
  const names = input.factors.map((factor) => factor.name.trim().toLocaleLowerCase());
  if (names.some((name) => name.length === 0) || new Set(names).size !== names.length) {
    return "doe_rsm_factor_names_not_unique";
  }
  const factors = input.factors.map((factor) => {
    const low = parseDoeResponseNumber(factor.low) ?? NaN;
    const high = parseDoeResponseNumber(factor.high) ?? NaN;
    const domain = parseDoeFactorDomainDraft(factor, low, high);
    return {
      name: factor.name.trim(),
      low,
      high,
      unit: factor.unit.trim() || null,
      domain_kind: domain?.domain_kind,
      step: domain?.step,
      display_decimals: domain?.display_decimals,
      validDomain: domain !== null,
    };
  });
  if (factors.some((factor) => !Number.isFinite(factor.low) || !Number.isFinite(factor.high) || factor.low >= factor.high || !factor.validDomain)) {
    return "doe_rsm_factor_range_invalid";
  }
  return {
    name: input.name.trim() || "Central composite design",
    factors: factors.map((factor) => ({
      name: factor.name,
      low: factor.low,
      high: factor.high,
      unit: factor.unit,
      domain_kind: factor.domain_kind,
      step: factor.step,
      display_decimals: factor.display_decimals,
    })),
    alpha_mode: input.ccdType === "face_centered" ? "face_centered" : "rotatable",
    ccd_type: input.ccdType,
    axial_points_confirmed: input.axialConfirmed,
    factorial_replicates: 1,
    axial_replicates: 1,
    center_points: centerPoints,
    center_point_mode: input.centerMode,
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
