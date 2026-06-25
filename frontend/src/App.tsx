import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";

import "./App.css";
import {
  confirmDatasetParsing,
  createDatasetFromPastedText,
  createAnalysisRun,
  fetchAnalysisMethods,
  fetchDatasetProfile,
  fetchHealth,
  fetchRowsPreview,
  uploadDataset,
  updateDatasetSchema,
  type AnalysisResultEnvelope,
  type AnalysisMethodListResponse,
  type AnalysisModuleId,
  type ConfirmedParsingOptions,
  type DatasetColumnResponse,
  type DatasetColumnRole,
  type DatasetColumnProfile,
  type DatasetMeasurementLevel,
  type DatasetProfileResponse,
  type DatasetRowsPreviewResponse,
  type DatasetUploadResponse,
  type DatasetVersionResponse,
  type DescriptiveStatisticsResult,
  type HealthResponse,
} from "./api";
import {
  AnalysisFilterControls,
} from "./AnalysisFilterControls";
import { AnalysisWorkbench } from "./AnalysisWorkbench";
import { buildAnalysisPath, parseAnalysisLocation } from "./analysisNavigation";
import {
  serializeAnalysisFilterDrafts,
  validateAnalysisFilterDrafts,
  type AnalysisFilterDraft,
} from "./analysisFilters";
import { applyBayesianOptimizationPreset, type SchemaDraft } from "./schemaPresets";

type HealthState =
  | { kind: "checking" }
  | { kind: "ready"; response: HealthResponse }
  | { kind: "error"; message: string };

const workflowSteps = [
  ["업로드", "CSV, TSV, XLSX 원본을 보존하고 해시와 파싱 옵션을 기록합니다."],
  ["파싱 확정", "인코딩, 구분자, 헤더 유무, 데이터 시작 행, 결측 토큰을 명시적으로 저장합니다."],
  ["스키마 확인", "표시명, 측정 수준, 역할, 단위를 명시적으로 저장합니다."],
  ["미리보기", "서버 페이지네이션으로 현재 행 범위만 불러옵니다."],
] as const;

const previewLimit = 10;
const defaultMissingTokens = ["", "NA", "N/A", "null", "N/T"];
const numericDataTypes = new Set<DatasetColumnResponse["data_type"]>(["integer", "decimal"]);
const defaultAnalysisModuleId: AnalysisModuleId = "exploration";

const measurementLevels: Array<{ value: DatasetMeasurementLevel; label: string }> = [
  { value: "unknown", label: "미정" },
  { value: "continuous", label: "연속" },
  { value: "count", label: "카운트" },
  { value: "ordinal", label: "순서" },
  { value: "nominal", label: "명목" },
  { value: "binary", label: "이진" },
  { value: "datetime", label: "날짜시간" },
  { value: "id", label: "ID" },
];

const columnRoles: Array<{ value: DatasetColumnRole; label: string }> = [
  { value: "unspecified", label: "미지정" },
  { value: "id", label: "ID" },
  { value: "feature", label: "특성" },
  { value: "target", label: "대상" },
  { value: "group", label: "그룹" },
  { value: "time", label: "시간" },
  { value: "order", label: "순서" },
  { value: "subgroup_id", label: "부분군" },
  { value: "part_id", label: "부품" },
  { value: "operator_id", label: "측정자" },
  { value: "replicate_id", label: "반복" },
  { value: "sample_size", label: "표본수" },
  { value: "opportunities", label: "기회수" },
  { value: "factor", label: "요인" },
  { value: "response", label: "반응" },
];

function statusLabel(health: HealthState): string {
  if (health.kind === "ready") {
    return `API ${health.response.status}`;
  }
  if (health.kind === "error") {
    return health.message;
  }
  return "API 확인 중";
}

function statusClassName(health: HealthState): string {
  if (health.kind === "ready") {
    return "status-pill status-ready";
  }
  if (health.kind === "error") {
    return "status-pill status-error";
  }
  return "status-pill";
}

function canConfirmParsingOptions(options: ConfirmedParsingOptions): boolean {
  if (!(options.has_header || options.data_start_row !== null)) {
    return false;
  }
  if (options.kind === "delimited_text") {
    return options.encoding !== null && options.delimiter !== null;
  }
  return options.kind === "xlsx";
}

export default function App() {
  const initialAnalysisSelection = initialAnalysisSelectionFromLocation();
  const [health, setHealth] = useState<HealthState>({ kind: "checking" });
  const [analysisCatalog, setAnalysisCatalog] = useState<AnalysisMethodListResponse | null>(null);
  const [analysisCatalogError, setAnalysisCatalogError] = useState<string | null>(null);
  const [selectedModuleId, setSelectedModuleId] = useState<AnalysisModuleId>(
    initialAnalysisSelection.moduleId,
  );
  const [selectedMethodId, setSelectedMethodId] = useState<string | null>(
    initialAnalysisSelection.methodId,
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<DatasetUploadResponse | null>(null);
  const [parsingOptions, setParsingOptions] = useState<ConfirmedParsingOptions | null>(null);
  const [version, setVersion] = useState<DatasetVersionResponse | null>(null);
  const [schemaDrafts, setSchemaDrafts] = useState<SchemaDraft[]>([]);
  const [preview, setPreview] = useState<DatasetRowsPreviewResponse | null>(null);
  const [profile, setProfile] = useState<DatasetProfileResponse | null>(null);
  const [selectedDescriptiveColumnIds, setSelectedDescriptiveColumnIds] = useState<string[]>([]);
  const [descriptiveFilterDrafts, setDescriptiveFilterDrafts] = useState<AnalysisFilterDraft[]>(
    [],
  );
  const [analysisResult, setAnalysisResult] = useState<AnalysisResultEnvelope | null>(null);
  const pasteTextAreaRef = useRef<HTMLTextAreaElement | null>(null);
  const [pastedTextLength, setPastedTextLength] = useState(0);
  const [previewOffset, setPreviewOffset] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isPastingDataset, setIsPastingDataset] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isSavingSchema, setIsSavingSchema] = useState(false);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isRunningAnalysis, setIsRunningAnalysis] = useState(false);
  const [flowError, setFlowError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchHealth(controller.signal)
      .then((response) => {
        setHealth({ kind: "ready", response });
      })
      .catch(() => {
        setHealth({
          kind: "error",
          message: "API 연결 필요",
        });
      });

    fetchAnalysisMethods(controller.signal)
      .then((response) => {
        setAnalysisCatalog(response);
        setAnalysisCatalogError(null);
        const initialSelection = initialAnalysisSelectionFromLocation();
        const moduleId = response.modules.some(
          (module) => module.module_id === initialSelection.moduleId,
        )
          ? initialSelection.moduleId
          : (response.modules[0]?.module_id ?? defaultAnalysisModuleId);
        const moduleMethods = response.methods.filter((method) => method.module_id === moduleId);
        const methodId = moduleMethods.some(
          (method) => method.method_id === initialSelection.methodId,
        )
          ? initialSelection.methodId
          : (moduleMethods[0]?.method_id ?? null);
        setSelectedModuleId(moduleId);
        setSelectedMethodId(methodId);
        if (methodId !== null) {
          replaceAnalysisRoute(moduleId, methodId);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setAnalysisCatalogError("analysis_methods_failed");
        }
      });

    return () => {
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    function handleRouteChange() {
      const selection = initialAnalysisSelectionFromLocation();
      setSelectedModuleId(selection.moduleId);
      setSelectedMethodId(selection.methodId);
    }

    window.addEventListener("popstate", handleRouteChange);
    window.addEventListener("hashchange", handleRouteChange);
    return () => {
      window.removeEventListener("popstate", handleRouteChange);
      window.removeEventListener("hashchange", handleRouteChange);
    };
  }, []);

  const delimiterOptions = useMemo(() => {
    const candidates =
      upload?.parsing.delimiter_candidates.map((candidate) => candidate.delimiter) ?? [];
    return Array.from(new Set([",", "\t", ";", "|", ...candidates]));
  }, [upload]);

  const canConfirm =
    upload !== null &&
    parsingOptions !== null &&
    canConfirmParsingOptions(parsingOptions) &&
    !isConfirming;

  const selectedModule = useMemo(
    () => analysisCatalog?.modules.find((module) => module.module_id === selectedModuleId) ?? null,
    [analysisCatalog, selectedModuleId],
  );

  const selectedMethods = useMemo(
    () =>
      analysisCatalog?.methods.filter((method) => method.module_id === selectedModuleId) ?? [],
    [analysisCatalog, selectedModuleId],
  );

  const selectedMethod = useMemo(
    () =>
      selectedMethods.find((method) => method.method_id === selectedMethodId) ??
      selectedMethods[0] ??
      null,
    [selectedMethods, selectedMethodId],
  );

  function selectAnalysisMethod(moduleId: AnalysisModuleId, methodId: string | null) {
    setSelectedModuleId(moduleId);
    setSelectedMethodId(methodId);
    if (methodId !== null) {
      replaceAnalysisRoute(moduleId, methodId);
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.currentTarget.files?.[0] ?? null);
    setUpload(null);
    setParsingOptions(null);
    setVersion(null);
    setSchemaDrafts([]);
    setPreview(null);
    setProfile(null);
    setSelectedDescriptiveColumnIds([]);
    setDescriptiveFilterDrafts([]);
    setAnalysisResult(null);
    setPreviewOffset(0);
    setFlowError(null);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedFile === null) {
      setFlowError("업로드할 파일을 선택하세요.");
      return;
    }

    setIsUploading(true);
    setFlowError(null);
    setVersion(null);
    setSchemaDrafts([]);
    setPreview(null);
    setProfile(null);
    setSelectedDescriptiveColumnIds([]);
    setDescriptiveFilterDrafts([]);
    setAnalysisResult(null);
    setPreviewOffset(0);
    try {
      const response = await uploadDataset(selectedFile);
      setUpload(response);
      setParsingOptions(parsingSuggestionToConfirmation(response));
    } catch (error) {
      setUpload(null);
      setParsingOptions(null);
      setFlowError(error instanceof Error ? error.message : "dataset_upload_failed");
    } finally {
      setIsUploading(false);
    }
  }

  async function handlePasteDataset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = pasteTextAreaRef.current?.value ?? "";
    if (content.trim() === "") {
      setFlowError("empty_pasted_data");
      return;
    }

    setIsPastingDataset(true);
    setFlowError(null);
    setSelectedFile(null);
    setUpload(null);
    setParsingOptions(null);
    setVersion(null);
    setSchemaDrafts([]);
    setPreview(null);
    setProfile(null);
    setSelectedDescriptiveColumnIds([]);
    setDescriptiveFilterDrafts([]);
    setAnalysisResult(null);
    setPreviewOffset(0);
    try {
      const response = await createDatasetFromPastedText({
        content,
        original_filename: "pasted-data.txt",
      });
      setUpload(response);
      setParsingOptions(parsingSuggestionToConfirmation(response));
      if (pasteTextAreaRef.current !== null) {
        pasteTextAreaRef.current.value = "";
      }
      setPastedTextLength(0);
    } catch (error) {
      setUpload(null);
      setParsingOptions(null);
      setFlowError(error instanceof Error ? error.message : "dataset_paste_failed");
    } finally {
      setIsPastingDataset(false);
    }
  }

  async function handleConfirmParsing() {
    if (upload === null || parsingOptions === null) {
      return;
    }

    setIsConfirming(true);
    setFlowError(null);
    try {
      const response = await confirmDatasetParsing(upload.dataset_id, {
        parsing: parsingOptions,
        columns: [],
      });
      setVersion(response);
      setSchemaDrafts(schemaDraftsFromColumns(response.columns));
      setSelectedDescriptiveColumnIds(defaultDescriptiveColumnIds(response.columns));
      setDescriptiveFilterDrafts([]);
      setAnalysisResult(null);
      setPreviewOffset(0);
      await Promise.all([loadRowsPreview(response.version_id, 0), loadDatasetProfile(response.version_id)]);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "parsing_confirmation_failed");
    } finally {
      setIsConfirming(false);
    }
  }

  async function handleSaveSchema() {
    if (version === null) {
      return;
    }

    setIsSavingSchema(true);
    setFlowError(null);
    try {
      const response = await updateDatasetSchema(version.version_id, {
        columns: schemaDrafts.map((draft) => ({
          column_id: draft.column_id,
          display_name: draft.display_name,
          measurement_level: draft.measurement_level,
          role: draft.role,
          unit: draft.unit.trim() === "" ? null : draft.unit.trim(),
        })),
      });
      const updatedVersion: DatasetVersionResponse = {
        ...version,
        schema_hash: response.schema_hash,
        columns: response.columns,
      };
      setVersion(updatedVersion);
      setSchemaDrafts(schemaDraftsFromColumns(response.columns));
      setSelectedDescriptiveColumnIds(defaultDescriptiveColumnIds(response.columns));
      setAnalysisResult(null);
      await Promise.all([
        loadRowsPreview(version.version_id, previewOffset),
        loadDatasetProfile(version.version_id),
      ]);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "schema_update_failed");
    } finally {
      setIsSavingSchema(false);
    }
  }

  async function loadRowsPreview(versionId: string, offset: number) {
    setIsLoadingPreview(true);
    try {
      const response = await fetchRowsPreview(versionId, offset, previewLimit);
      setPreview(response);
      setPreviewOffset(offset);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "rows_preview_failed");
    } finally {
      setIsLoadingPreview(false);
    }
  }

  async function loadDatasetProfile(versionId: string) {
    setIsLoadingProfile(true);
    try {
      const response = await fetchDatasetProfile(versionId);
      setProfile(response);
    } catch (error) {
      setProfile(null);
      setFlowError(error instanceof Error ? error.message : "dataset_profile_failed");
    } finally {
      setIsLoadingProfile(false);
    }
  }

  function updateSchemaDraft(
    columnId: string,
    patch: Partial<Pick<SchemaDraft, "display_name" | "measurement_level" | "role" | "unit">>,
  ) {
    setSchemaDrafts((current) =>
      current.map((draft) => (draft.column_id === columnId ? { ...draft, ...patch } : draft)),
    );
  }

  const canApplyBayesianPreset =
    version !== null &&
    version.parsing.has_header === false &&
    schemaDrafts.length >= 34 &&
    version.columns
      .slice(0, 34)
      .every((column, index) => column.original_name === `column_${index + 1}`);

  function handleApplyBayesianPreset() {
    setSchemaDrafts((current) => applyBayesianOptimizationPreset(current));
  }

  const descriptiveColumns = useMemo(
    () => (version === null ? [] : selectableDescriptiveColumns(version.columns)),
    [version],
  );

  const descriptiveResult = isDescriptiveStatisticsResult(analysisResult?.result)
    ? analysisResult.result
    : null;

  const descriptiveFilterValidationError = useMemo(
    () =>
      version === null
        ? null
        : validateAnalysisFilterDrafts(descriptiveFilterDrafts, version.columns),
    [descriptiveFilterDrafts, version],
  );

  async function handleRunDescriptiveAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "eda.descriptive" ||
      selectedDescriptiveColumnIds.length === 0
    ) {
      setFlowError("descriptive_columns_required");
      return;
    }
    if (descriptiveFilterValidationError !== null) {
      setFlowError(descriptiveFilterValidationError);
      return;
    }

    setIsRunningAnalysis(true);
    setFlowError(null);
    try {
      const filterConditions = serializeAnalysisFilterDrafts(
        descriptiveFilterDrafts,
        version.columns,
      );
      const response = await createAnalysisRun({
        method_id: selectedMethod.method_id,
        method_version: selectedMethod.method_version,
        dataset_version_id: version.version_id,
        filter_snapshot: {
          expression_version: 1,
          conditions: filterConditions,
        },
        roles: {},
        options: {
          column_ids: selectedDescriptiveColumnIds,
          missing_policy: "available_case_by_column",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="주요 단계">
        <div className="brand">
          <h1 className="brand-title">DataLab Studio</h1>
          <p className="brand-subtitle">로컬 분석 작업대</p>
        </div>
        <ol className="nav-list">
          <li className="nav-item nav-item-active">프로젝트</li>
          <li className="nav-item">데이터셋</li>
          <li className="nav-item">분석</li>
          <li className="nav-item">리포트</li>
        </ol>
      </aside>
      <main className="main">
        <header className="topbar">
          <p className="topbar-title">Gate A 기반 구성</p>
          <span className={statusClassName(health)} aria-live="polite">
            {statusLabel(health)}
          </span>
        </header>
        {version !== null ? (
          <div className="context-bar" aria-label="데이터셋 컨텍스트">
            <span>Dataset v{version.version_number}</span>
            <span>{version.row_count.toLocaleString()}행</span>
            <span>{version.column_count.toLocaleString()}컬럼</span>
            <span className="hash-text">schema {shortHash(version.schema_hash)}</span>
            <span className="hash-text">source {shortHash(version.source_sha256)}</span>
          </div>
        ) : null}
        <section className="workspace" aria-labelledby="workspace-title">
          <section className="analysis-shell" aria-labelledby="analysis-modules-title">
            <div className="analysis-heading">
              <div>
                <h2 id="analysis-modules-title">분석 모듈</h2>
                {selectedModule !== null ? (
                  <p>
                    {selectedModule.label_ko} · {selectedModule.label_en}
                  </p>
                ) : null}
              </div>
              <span className="status-pill">Gate B0</span>
            </div>
            {analysisCatalogError !== null ? (
              <div className="notice-box">분석 메서드 registry를 불러오지 못했습니다.</div>
            ) : null}
            {analysisCatalog === null && analysisCatalogError === null ? (
              <div className="notice-box">분석 메서드 조회 중</div>
            ) : null}
            {analysisCatalog !== null ? (
              <AnalysisWorkbench
                catalog={analysisCatalog}
                profile={profile}
                selectedMethod={selectedMethod}
                selectedMethods={selectedMethods}
                selectedModuleId={selectedModuleId}
                version={version}
                onSelectMethod={selectAnalysisMethod}
                renderExecutableMethod={(method) =>
                  method.method_id === "eda.descriptive" &&
                  method.availability === "available" ? (
                    <section className="analysis-run-panel" aria-labelledby="descriptive-title">
                      <div className="panel-heading">
                        <div>
                          <h3 id="descriptive-title">기술통계 실행</h3>
                          <p>{method.method_id}</p>
                        </div>
                        <span className="status-pill status-ready">사용 가능</span>
                      </div>
                      {version === null ? (
                        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
                      ) : (
                        <>
                          <div className="column-picker" aria-label="기술통계 컬럼 선택">
                            {descriptiveColumns.map((column) => (
                              <label key={column.column_id}>
                                <input
                                  checked={selectedDescriptiveColumnIds.includes(
                                    column.column_id,
                                  )}
                                  type="checkbox"
                                  onChange={(event) => {
                                    const checked = event.currentTarget.checked;
                                    setSelectedDescriptiveColumnIds((current) =>
                                      checked
                                        ? Array.from(new Set([...current, column.column_id]))
                                        : current.filter((id) => id !== column.column_id),
                                    );
                                  }}
                                />
                                <span>{column.display_name}</span>
                              </label>
                            ))}
                          </div>
                          <AnalysisFilterControls
                            columns={version.columns}
                            drafts={descriptiveFilterDrafts}
                            onChange={(drafts) => {
                              setDescriptiveFilterDrafts(drafts);
                              setAnalysisResult(null);
                            }}
                          />
                          {descriptiveFilterValidationError !== null ? (
                            <div className="error-box">
                              {filterValidationMessage(descriptiveFilterValidationError)}
                            </div>
                          ) : null}
                          <button
                            className="primary-button"
                            disabled={
                              isRunningAnalysis ||
                              selectedDescriptiveColumnIds.length === 0 ||
                              descriptiveFilterValidationError !== null
                            }
                            onClick={() => {
                              void handleRunDescriptiveAnalysis();
                            }}
                            type="button"
                          >
                            {isRunningAnalysis ? "실행 중" : "기술통계 실행"}
                          </button>
                          {analysisResult?.provenance.row_count_included !== undefined &&
                          analysisResult.provenance.row_count_included !== null ? (
                            <div className="metadata-grid" aria-label="분석 대상 행">
                              <span>사용 행</span>
                              <strong>
                                {analysisResult.provenance.row_count_included.toLocaleString()} /
                                {" "}
                                {(
                                  analysisResult.provenance.row_count_total ??
                                  analysisResult.provenance.row_count_included
                                ).toLocaleString()}
                              </strong>
                            </div>
                          ) : null}
                          {analysisResult?.warnings.length ? (
                            <ul className="warning-list" aria-label="분석 경고">
                              {analysisResult.warnings.map((warning, index) => (
                                <li key={`${warning.code}-${index}`}>{warning.message}</li>
                              ))}
                            </ul>
                          ) : null}
                          {descriptiveResult !== null ? (
                            <div className="table-wrap">
                              <table className="result-table">
                                <thead>
                                  <tr>
                                    <th>컬럼</th>
                                    <th>N</th>
                                    <th>결측</th>
                                    <th>평균</th>
                                    <th>표준편차</th>
                                    <th>최소</th>
                                    <th>Q1</th>
                                    <th>중앙값</th>
                                    <th>Q3</th>
                                    <th>최대</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {descriptiveResult.columns.map((column) => (
                                    <tr key={column.column_id}>
                                      <td>{column.display_name}</td>
                                      <td>{column.n_used}</td>
                                      <td>{column.n_missing}</td>
                                      <td>{formatNumber(column.mean)}</td>
                                      <td>{formatNumber(column.std)}</td>
                                      <td>{formatNumber(column.min)}</td>
                                      <td>{formatNumber(column.q1)}</td>
                                      <td>{formatNumber(column.median)}</td>
                                      <td>{formatNumber(column.q3)}</td>
                                      <td>{formatNumber(column.max)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : null}
                        </>
                      )}
                    </section>
                  ) : null
                }
              />
            ) : null}
          </section>
          <div className="section">
            <h2 id="workspace-title">데이터셋 파싱 확정</h2>
            <p>
              Gate B0에서는 원본 업로드를 불변 데이터셋 버전으로 확정하고, 스키마와 행
              미리보기를 서버 페이지 단위로 확인합니다.
            </p>
          </div>
          <form
            className="upload-panel"
            onSubmit={(event) => {
              void handleUpload(event);
            }}
          >
            <label className="file-control">
              <span>원본 데이터 파일</span>
              <input
                accept=".csv,.tsv,.txt,.xlsx"
                onChange={handleFileChange}
                type="file"
              />
            </label>
            <button className="primary-button" disabled={selectedFile === null || isUploading}>
              {isUploading ? "업로드 중" : "업로드"}
            </button>
          </form>
          <form
            className="paste-panel"
            onSubmit={(event) => {
              void handlePasteDataset(event);
            }}
          >
            <label className="paste-control">
              <span>복사한 표 붙여넣기</span>
              <textarea
                ref={pasteTextAreaRef}
                onChange={(event) => {
                  setPastedTextLength(event.currentTarget.value.length);
                }}
                placeholder="Excel이나 스프레드시트에서 범위를 복사한 뒤 여기에 붙여넣으세요."
                rows={6}
              />
            </label>
            <div className="paste-actions">
              <span>{pastedTextLength.toLocaleString()}자</span>
              <button
                className="primary-button"
                disabled={pastedTextLength === 0 || isPastingDataset}
                type="submit"
              >
                {isPastingDataset ? "등록 중" : "붙여넣기 데이터 등록"}
              </button>
            </div>
          </form>
          {flowError !== null ? (
            <div className="error-box" role="alert">
              오류 코드: {flowError}
            </div>
          ) : null}
          {upload !== null && parsingOptions !== null ? (
            <section className="confirmation-panel" aria-labelledby="confirmation-title">
              <div className="panel-heading">
                <div>
                  <h3 id="confirmation-title">파싱 옵션</h3>
                  <p>{upload.original_filename}</p>
                </div>
                <span className="status-pill">SHA-256 기록됨</span>
              </div>
              <div className="metadata-grid">
                <span>형식</span>
                <strong>{upload.detected_format}</strong>
                <span>크기</span>
                <strong>{upload.size_bytes.toLocaleString()} bytes</strong>
                <span>다음 단계</span>
                <strong>{upload.next_step}</strong>
              </div>
              {upload.warnings.length > 0 ? (
                <ul className="warning-list" aria-label="업로드 경고">
                  {upload.warnings.map((warning) => (
                    <li key={warning.code}>{warning.message}</li>
                  ))}
                </ul>
              ) : null}
              {parsingOptions.kind === "delimited_text" ? (
                <div className="option-grid">
                  <label>
                    <span>인코딩</span>
                    <select
                      value={parsingOptions.encoding ?? ""}
                      onChange={(event) => {
                        setParsingOptions({
                          ...parsingOptions,
                          encoding: event.currentTarget.value,
                        });
                      }}
                    >
                      {upload.parsing.encoding_candidates.map((encoding) => (
                        <option key={encoding} value={encoding}>
                          {encoding}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>구분자</span>
                    <select
                      value={parsingOptions.delimiter ?? ""}
                      onChange={(event) => {
                        setParsingOptions({
                          ...parsingOptions,
                          delimiter: event.currentTarget.value,
                        });
                      }}
                    >
                      {delimiterOptions.map((delimiter) => (
                        <option key={delimiter} value={delimiter}>
                          {delimiterLabel(delimiter)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>첫 데이터 행을 헤더로 사용</span>
                    <input
                      checked={parsingOptions.has_header}
                      type="checkbox"
                      onChange={(event) => {
                        const hasHeader = event.currentTarget.checked;
                        setParsingOptions({
                          ...parsingOptions,
                          has_header: hasHeader,
                          data_start_row: hasHeader
                            ? parsingOptions.header_row + 1
                            : (parsingOptions.data_start_row ?? parsingOptions.header_row),
                        });
                      }}
                    />
                  </label>
                  <label>
                    <span>{parsingOptions.has_header ? "헤더 행" : "데이터 시작 행"}</span>
                    <input
                      min={1}
                      type="number"
                      value={
                        parsingOptions.has_header
                          ? parsingOptions.header_row
                          : (parsingOptions.data_start_row ?? parsingOptions.header_row)
                      }
                      onChange={(event) => {
                        const rowNumber = Number(event.currentTarget.value);
                        setParsingOptions({
                          ...parsingOptions,
                          header_row: parsingOptions.has_header
                            ? rowNumber
                            : parsingOptions.header_row,
                          data_start_row: parsingOptions.has_header
                            ? rowNumber + 1
                            : rowNumber,
                        });
                      }}
                    />
                  </label>
                  <label>
                    <span>결측 토큰</span>
                    <input
                      value={parsingOptions.missing_tokens.join(",")}
                      onChange={(event) => {
                        setParsingOptions({
                          ...parsingOptions,
                          missing_tokens: event.currentTarget.value.split(","),
                        });
                      }}
                    />
                  </label>
                </div>
              ) : (
                <div className="option-grid">
                  <label>
                    <span>시트명</span>
                    <input
                      placeholder="비우면 첫 시트"
                      value={parsingOptions.xlsx_sheet_name ?? ""}
                      onChange={(event) => {
                        const value = event.currentTarget.value.trim();
                        setParsingOptions({
                          ...parsingOptions,
                          xlsx_sheet_name: value === "" ? null : value,
                        });
                      }}
                    />
                  </label>
                  <label>
                    <span>첫 데이터 행을 헤더로 사용</span>
                    <input
                      checked={parsingOptions.has_header}
                      type="checkbox"
                      onChange={(event) => {
                        const hasHeader = event.currentTarget.checked;
                        setParsingOptions({
                          ...parsingOptions,
                          has_header: hasHeader,
                          data_start_row: hasHeader
                            ? parsingOptions.header_row + 1
                            : (parsingOptions.data_start_row ?? parsingOptions.header_row),
                        });
                      }}
                    />
                  </label>
                  <label>
                    <span>{parsingOptions.has_header ? "헤더 행" : "데이터 시작 행"}</span>
                    <input
                      min={1}
                      type="number"
                      value={
                        parsingOptions.has_header
                          ? parsingOptions.header_row
                          : (parsingOptions.data_start_row ?? parsingOptions.header_row)
                      }
                      onChange={(event) => {
                        const rowNumber = Number(event.currentTarget.value);
                        setParsingOptions({
                          ...parsingOptions,
                          header_row: parsingOptions.has_header
                            ? rowNumber
                            : parsingOptions.header_row,
                          data_start_row: parsingOptions.has_header
                            ? rowNumber + 1
                            : rowNumber,
                        });
                      }}
                    />
                  </label>
                  <label>
                    <span>결측 토큰</span>
                    <input
                      value={parsingOptions.missing_tokens.join(",")}
                      onChange={(event) => {
                        setParsingOptions({
                          ...parsingOptions,
                          missing_tokens: event.currentTarget.value.split(","),
                        });
                      }}
                    />
                  </label>
                </div>
              )}
              <button
                className="primary-button"
                disabled={!canConfirm}
                onClick={() => {
                  void handleConfirmParsing();
                }}
                type="button"
              >
                {isConfirming ? "확정 중" : "파싱 확정 및 버전 생성"}
              </button>
            </section>
          ) : null}
          {version !== null ? (
            <section className="version-panel" aria-labelledby="version-title">
              <div className="panel-heading">
                <div>
                  <h3 id="version-title">Dataset version v{version.version_number}</h3>
                  <p>{version.version_id}</p>
                </div>
                <span className="status-pill status-ready">버전 생성됨</span>
              </div>
              <div className="metadata-grid">
                <span>행</span>
                <strong>{version.row_count.toLocaleString()}</strong>
                <span>컬럼</span>
                <strong>{version.column_count.toLocaleString()}</strong>
                <span>Schema hash</span>
                <strong className="hash-text">{version.schema_hash}</strong>
                <span>Canonical</span>
                <strong className="hash-text">
                  {version.canonical_artifact === null
                    ? "대기"
                    : `${shortHash(version.canonical_artifact.sha256)} · ${formatBytes(
                        version.canonical_artifact.size_bytes,
                      )}`}
                </strong>
              </div>
              <div className="schema-actions">
                <span>프로파일 / 사전점검</span>
                <button
                  className="secondary-button"
                  disabled={isLoadingProfile}
                  onClick={() => {
                    void loadDatasetProfile(version.version_id);
                  }}
                  type="button"
                >
                  {isLoadingProfile ? "계산 중" : "다시 계산"}
                </button>
              </div>
              {profile?.warnings.length ? (
                <ul className="warning-list" aria-label="데이터셋 프로파일 경고">
                  {profile.warnings.map((warning) => (
                    <li key={warning.code}>{warning.message}</li>
                  ))}
                </ul>
              ) : null}
              {profile !== null ? (
                <div className="metadata-grid" aria-label="프로파일 사전점검">
                  <span>Canonical artifact</span>
                  <strong className="hash-text">
                    {profile.canonical_artifact === null
                      ? "없음"
                      : `${shortHash(profile.canonical_artifact.sha256)} · ${formatBytes(
                          profile.canonical_artifact.size_bytes,
                        )}`}
                  </strong>
                  <span>Profile artifact</span>
                  <strong className="hash-text">
                    {profile.profile_artifact === null
                      ? "없음"
                      : `${shortHash(profile.profile_artifact.sha256)} · ${formatBytes(
                          profile.profile_artifact.size_bytes,
                        )}`}
                  </strong>
                  <span>메모리 추정</span>
                  <strong>{formatBytes(profile.preflight.estimated_memory_bytes)}</strong>
                  <span>중복 행</span>
                  <strong>
                    {profile.preflight.duplicate_row_count.toLocaleString()}
                    {profile.preflight.duplicate_row_count_capped ? "+" : ""}
                  </strong>
                </div>
              ) : null}
              {profile !== null ? (
                <div className="table-wrap">
                  <table className="profile-table">
                    <thead>
                      <tr>
                        <th>컬럼</th>
                        <th>역할</th>
                        <th>결측</th>
                        <th>고유값</th>
                        <th>요약</th>
                        <th>점검</th>
                      </tr>
                    </thead>
                    <tbody>
                      {profile.columns.map((column) => (
                        <tr key={column.column_id}>
                          <td>
                            <strong>{column.display_name}</strong>
                            <span className="cell-subtle">{column.data_type}</span>
                          </td>
                          <td>
                            {roleLabel(column.role)}
                            <span className="cell-subtle">
                              {measurementLevelLabel(column.measurement_level)}
                            </span>
                          </td>
                          <td>
                            {column.n_missing.toLocaleString()} /{" "}
                            {column.n_total.toLocaleString()}
                            <span className="cell-subtle">
                              {formatPercent(column.missing_rate)}
                            </span>
                          </td>
                          <td>
                            {column.unique_count_capped
                              ? `${profile.unique_count_limit}+`
                              : column.unique_count.toLocaleString()}
                          </td>
                          <td>{formatProfileSummary(column)}</td>
                          <td>
                            {column.warnings.length > 0 ? (
                              <ul className="inline-warning-list">
                                {column.warnings.map((warning) => (
                                  <li key={warning.code}>{warning.message}</li>
                                ))}
                              </ul>
                            ) : (
                              <span className="cell-subtle">경고 없음</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="notice-box">
                  {isLoadingProfile ? "프로파일 계산 중" : "프로파일을 아직 불러오지 않았습니다."}
                </div>
              )}
              <div className="schema-actions">
                <span>스키마 확인</span>
                <div className="button-row">
                  {canApplyBayesianPreset ? (
                    <button
                      className="secondary-button"
                      onClick={handleApplyBayesianPreset}
                      type="button"
                    >
                      Bayesian 역할 자동 지정
                    </button>
                  ) : null}
                  <button
                    className="secondary-button"
                    disabled={isSavingSchema}
                    onClick={() => {
                      void handleSaveSchema();
                    }}
                    type="button"
                  >
                    {isSavingSchema ? "저장 중" : "스키마 저장"}
                  </button>
                </div>
              </div>
              <div className="table-wrap">
                <table className="schema-table">
                  <thead>
                    <tr>
                      <th>컬럼</th>
                      <th>표시명</th>
                      <th>타입</th>
                      <th>측정 수준</th>
                      <th>역할</th>
                      <th>단위</th>
                    </tr>
                  </thead>
                  <tbody>
                    {version.columns.map((column) => {
                      const draft = schemaDrafts.find(
                        (item) => item.column_id === column.column_id,
                      );
                      return (
                        <tr key={column.column_id}>
                          <td>{column.original_name || "(empty)"}</td>
                          <td>
                            <input
                              aria-label={`${column.original_name || "empty"} 표시명`}
                              value={draft?.display_name ?? column.display_name}
                              onChange={(event) => {
                                updateSchemaDraft(column.column_id, {
                                  display_name: event.currentTarget.value,
                                });
                              }}
                            />
                          </td>
                          <td>{column.data_type}</td>
                          <td>
                            <select
                              aria-label={`${column.original_name || "empty"} 측정 수준`}
                              value={draft?.measurement_level ?? column.measurement_level}
                              onChange={(event) => {
                                const measurementLevel = event.currentTarget
                                  .value as DatasetMeasurementLevel;
                                updateSchemaDraft(column.column_id, {
                                  measurement_level: measurementLevel,
                                });
                              }}
                            >
                              {measurementLevels.map((level) => (
                                <option key={level.value} value={level.value}>
                                  {level.label}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <select
                              aria-label={`${column.original_name || "empty"} 역할`}
                              value={draft?.role ?? column.role}
                              onChange={(event) => {
                                const role = event.currentTarget.value as DatasetColumnRole;
                                updateSchemaDraft(column.column_id, {
                                  role,
                                });
                              }}
                            >
                              {columnRoles.map((role) => (
                                <option key={role.value} value={role.value}>
                                  {role.label}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <input
                              aria-label={`${column.original_name || "empty"} 단위`}
                              value={draft?.unit ?? column.unit ?? ""}
                              onChange={(event) => {
                                updateSchemaDraft(column.column_id, {
                                  unit: event.currentTarget.value,
                                });
                              }}
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="schema-actions">
                <span>
                  행 미리보기 {previewOffset + 1}-
                  {Math.min(previewOffset + previewLimit, version.row_count).toLocaleString()}
                </span>
                <div className="button-row">
                  <button
                    className="secondary-button"
                    disabled={isLoadingPreview || previewOffset === 0}
                    onClick={() => {
                      void loadRowsPreview(
                        version.version_id,
                        Math.max(0, previewOffset - previewLimit),
                      );
                    }}
                    type="button"
                  >
                    이전
                  </button>
                  <button
                    className="secondary-button"
                    disabled={
                      isLoadingPreview || previewOffset + previewLimit >= version.row_count
                    }
                    onClick={() => {
                      void loadRowsPreview(version.version_id, previewOffset + previewLimit);
                    }}
                    type="button"
                  >
                    다음
                  </button>
                </div>
              </div>
              {preview !== null ? (
                <div className="table-wrap">
                  <table className="preview-table">
                    <thead>
                      <tr>
                        <th>행</th>
                        {preview.columns.map((column) => (
                          <th key={column.column_id}>{column.display_name}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.map((row) => (
                        <tr key={row.row_index}>
                          <td>{row.row_index + 1}</td>
                          {row.values.map((value, index) => (
                            <td key={`${row.row_index}-${index}`}>{value ?? "(missing)"}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="notice-box">버전 생성 후 행 미리보기를 불러옵니다.</div>
              )}
            </section>
          ) : null}
          <div className="workflow-grid" aria-label="작업 흐름">
            {workflowSteps.map(([title, description]) => (
              <div className="workflow-step" key={title}>
                <strong>{title}</strong>
                <span>{description}</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function parsingSuggestionToConfirmation(upload: DatasetUploadResponse): ConfirmedParsingOptions {
  return {
    kind: upload.parsing.kind,
    encoding: upload.parsing.suggested_encoding,
    delimiter: upload.parsing.suggested_delimiter,
    quote_char: upload.parsing.quote_char,
    decimal: upload.parsing.decimal,
    thousands: upload.parsing.thousands,
    has_header: upload.parsing.has_header,
    header_row: upload.parsing.header_row,
    data_start_row: upload.parsing.data_start_row,
    missing_tokens: defaultMissingTokens,
    xlsx_sheet_name: null,
  };
}

function schemaDraftsFromColumns(columns: DatasetColumnResponse[]): SchemaDraft[] {
  return columns.map((column) => ({
    column_id: column.column_id,
    display_name: column.display_name,
    measurement_level: column.measurement_level,
    role: column.role,
    unit: column.unit ?? "",
  }));
}

function selectableDescriptiveColumns(columns: DatasetColumnResponse[]): DatasetColumnResponse[] {
  return columns.filter(
    (column) =>
      numericDataTypes.has(column.data_type) &&
      column.role !== "id" &&
      column.measurement_level !== "id",
  );
}

function defaultDescriptiveColumnIds(columns: DatasetColumnResponse[]): string[] {
  return selectableDescriptiveColumns(columns).map((column) => column.column_id);
}

function isDescriptiveStatisticsResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is DescriptiveStatisticsResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "descriptive_statistics" &&
    Array.isArray(candidate.columns)
  );
}

function shortHash(value: string): string {
  return value.slice(0, 12);
}

function formatNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}

function formatPercent(value: number): string {
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 1,
    style: "percent",
  }).format(value);
}

function formatBytes(value: number): string {
  const units = ["bytes", "KB", "MB", "GB"] as const;
  let currentValue = value;
  let unitIndex = 0;
  while (currentValue >= 1024 && unitIndex < units.length - 1) {
    currentValue /= 1024;
    unitIndex += 1;
  }
  return `${new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: unitIndex === 0 ? 0 : 1,
  }).format(currentValue)} ${units[unitIndex]}`;
}

function formatProfileSummary(column: DatasetColumnProfile): string {
  const summaries: string[] = [];
  if (column.n_numeric > 0) {
    summaries.push(
      `평균 ${formatNumber(column.numeric_mean)} · 범위 ${formatNumber(
        column.numeric_min,
      )}-${formatNumber(column.numeric_max)}`,
    );
  }
  if (column.datetime_profile !== null && column.datetime_profile.n_datetime > 0) {
    summaries.push(formatDateTimeProfile(column.datetime_profile));
  }
  return summaries.length > 0 ? summaries.join(" · ") : "-";
}

function formatDateTimeProfile(profile: DatasetColumnProfile["datetime_profile"]): string {
  if (profile === null || profile.n_datetime === 0) {
    return "-";
  }
  const formatCandidates = profile.format_candidates
    .slice(0, 2)
    .map((candidate) => `${candidate.format} ${candidate.n_matched.toLocaleString()}개`)
    .join(", ");
  const timezoneSummary =
    profile.timezone_aware_count > 0
      ? ` · TZ ${profile.timezone_aware_count.toLocaleString()}개`
      : "";
  const formatSummary = formatCandidates.length > 0 ? ` · ${formatCandidates}` : "";
  return `날짜 ${profile.n_datetime.toLocaleString()}개 · ${profile.datetime_min ?? "?"}-${
    profile.datetime_max ?? "?"
  }${formatSummary}${timezoneSummary}`;
}

function measurementLevelLabel(value: DatasetMeasurementLevel): string {
  return measurementLevels.find((level) => level.value === value)?.label ?? value;
}

function roleLabel(value: DatasetColumnRole): string {
  return columnRoles.find((role) => role.value === value)?.label ?? value;
}

function filterValidationMessage(code: string): string {
  if (code === "filter_column_not_found") {
    return "필터 컬럼을 찾을 수 없습니다.";
  }
  if (code === "filter_operator_not_supported_for_column") {
    return "선택한 컬럼에는 해당 필터 조건을 사용할 수 없습니다.";
  }
  if (code === "filter_value_required") {
    return "필터 조건 값을 입력하세요.";
  }
  return code;
}

function initialAnalysisSelectionFromLocation(): {
  moduleId: AnalysisModuleId;
  methodId: string | null;
} {
  if (typeof window === "undefined") {
    return {
      moduleId: defaultAnalysisModuleId,
      methodId: null,
    };
  }

  const parsed = parseAnalysisLocation(window.location.pathname, window.location.hash);
  return {
    moduleId: parsed?.moduleId ?? defaultAnalysisModuleId,
    methodId: parsed?.methodId ?? null,
  };
}

function replaceAnalysisRoute(moduleId: AnalysisModuleId, methodId: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.history.replaceState(null, "", buildAnalysisPath(moduleId, methodId));
}

function delimiterLabel(delimiter: string): string {
  if (delimiter === "\t") {
    return "tab";
  }
  if (delimiter === ",") {
    return "comma";
  }
  if (delimiter === ";") {
    return "semicolon";
  }
  if (delimiter === "|") {
    return "pipe";
  }
  return delimiter;
}
