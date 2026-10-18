import * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AnalysisMethodListResponse,
  AnalysisReportCapability,
  AnalysisResultEnvelope,
  AnalysisRunDeleteResponse,
  AnalysisRunDeletionPreflightResponse,
  AnalysisResultExportDeleteResponse,
  AnalysisResultExportDeletionPreflightResponse,
  AnalysisResultExportListResponse,
  AnalysisRunComparisonResponse,
  AnalysisRunListResponse,
  AnalysisRunStatusResponse,
  AnalysisRunRequest,
  AttributeControlLimitSetListResponse,
  AttributeControlLimitSetDeletionPreflightResponse,
  AttributeControlLimitSetResponse,
  BayesianRecommendationResponse,
  BayesianRecommendationBatchCreateRequest,
  BayesianRecommendationBatchResponse,
  BayesianStudyDeletionPreflightResponse,
  BayesianStudyListResponse,
  BayesianStudyResponse,
  DatasetVersionCatalogItem,
  DatasetVersionCatalogResponse,
  DatasetVersionDeleteResponse,
  DatasetVersionDeletionPreflightResponse,
  DatasetVersionResponse,
  DatasetUploadResponse,
  DatasetCellCorrectionResponse,
  DatasetSchemaResponse,
  DatasetRowsPreviewResponse,
  DatasetProfileResponse,
  RegressionPredictionCsvExportResponse,
  RegressionPredictionPreflightResponse,
  RegressionPredictionResponse,
  RegressionPredictionRowsPageResponse,
  RegressionModelDeleteResponse,
  RegressionModelDeletionPreflightResponse,
  RuntimeInfoResponse,
} from "./api";
import { useAnalysisComparisonState } from "./useAnalysisComparisonState";
import { useAnalysisExportState } from "./useAnalysisExportState";
import { useAnalysisHistoryState } from "./useAnalysisHistoryState";
import { useAnalysisRunDeletionState } from "./useAnalysisRunDeletionState";
import { useAttributeControlPhase2State } from "./useAttributeControlPhase2State";
import { useRegressionPredictionExportState } from "./useRegressionPredictionExportState";
import { useRegressionPredictionRowsState } from "./useRegressionPredictionRowsState";
import { useRegressionPredictionState } from "./useRegressionPredictionState";
import { useRegressionPredictionTargetState } from "./useRegressionPredictionTargetState";
import { useRegressionModelRetentionState } from "./useRegressionModelRetentionState";
import { useRestoredAnalysisResultState } from "./useRestoredAnalysisResultState";
import { useBayesianStudyCatalogState } from "./features/bayesian/hooks/useBayesianStudyCatalogState";
import { useBayesianStudyDraftState } from "./features/bayesian/hooks/useBayesianStudyDraftState";
import { useBayesianStudyLifecycleState } from "./features/bayesian/hooks/useBayesianStudyLifecycleState";
import { useBayesianRecommendationState } from "./features/bayesian/hooks/useBayesianRecommendationState";
import { useBayesianRetentionState } from "./features/bayesian/hooks/useBayesianRetentionState";
import { useDatasetVersionCatalogState } from "./useDatasetVersionCatalogState";
import { useDatasetWorkflow } from "./useDatasetWorkflow";
import { usePastedDatasetDraft } from "./usePastedDatasetDraft";
import { usePastedDatasetSubmission } from "./usePastedDatasetSubmission";
import { useDatasetVersionRetentionState } from "./useDatasetVersionRetentionState";
import { useRuntimeCompatibilityState } from "./useRuntimeCompatibilityState";
import { useReportCenterState } from "./useReportCenterState";
import { useManagedReports } from "./useManagedReports";
import { useCurrentAnalysisExecution } from "./useCurrentAnalysisExecution";
import type { AnalysisExecutionSource } from "./analysisExecutionContext";
import { PrincipalComponentsPanel } from "./PrincipalComponentsPanel";
import { PlsRegressionPanel } from "./PlsRegressionPanel";
import { GaussianProcessRegressionPanel } from "./GaussianProcessRegressionPanel";
import { TwoVariancesPanel } from "./TwoVariancesPanel";
import type { ManagedReportDescriptor, ManagedReportList, ReportSourceDescriptor, StoredReportCapability, StoredSourceSnapshot } from "./api/types/reports";
import { useAssetManagementState } from "./useAssetManagementState";
import { useProjectOverviewState } from "./useProjectOverviewState";
import type { AnalysisRunsRouteParams } from "./api/routes";

function reportCapability(analysisId: string, locale: "en" | "ko", hash = "a"): AnalysisReportCapability {
  return {
    capability_schema_version: 1, analysis_id: analysisId, method_id: "eda.descriptive",
    summary_type: "descriptive_statistics", result_schema_version: 1,
    source_result_sha256: hash.repeat(64), stale: false, locale,
    renderer_id: "descriptive", renderer_version: "1", variant_id: "default",
    report_level: "full", sections: [], reason: null, html_available: true,
    source_validation: "stored_dependencies_only",
  };
}

const managedReportMocks = vi.hoisted(() => ({ fetchReportSources: vi.fn(), fetchStoredReportCapability: vi.fn(), fetchStoredSourceSnapshot: vi.fn(), fetchManagedReports: vi.fn(), fetchManagedReport: vi.fn(), createManagedReport: vi.fn(), deleteManagedReport: vi.fn(), fetchManagedReportDownload: vi.fn() }));
vi.mock("./api/reports", () => managedReportMocks);

const apiMocks = vi.hoisted(() => ({
  createAnalysisRun: vi.fn(),
  abandonBayesianTrial: vi.fn(),
  closeBayesianStudy: vi.fn(),
  createBayesianRecommendation: vi.fn(),
  createBayesianRecommendationBatch: vi.fn(),
  createBayesianStudy: vi.fn(),
  confirmDatasetParsing: vi.fn(),
  createDatasetCellCorrection: vi.fn(),
  createDatasetFromPastedText: vi.fn(),
  createAnalysisResultCsvExport: vi.fn(),
  createAnalysisResultHtmlReport: vi.fn(),
  createAnalysisResultJsonExport: vi.fn(),
  createRegressionPredictionCsvExport: vi.fn(),
  deleteAnalysisResultExport: vi.fn(),
  deleteAttributeControlLimitSet: vi.fn(),
  deleteBayesianStudy: vi.fn(),
  deleteDatasetVersion: vi.fn(),
  deleteRegressionModel: vi.fn(),
  deleteStoredAnalysisRun: vi.fn(),
  downloadAnalysisResultExport: vi.fn(),
  fetchAnalysisResultExportDeletionPreflight: vi.fn(),
  fetchAnalysisResultExports: vi.fn(),
  fetchAnalysisReportCapability: vi.fn(),
  fetchAnalysisRunComparison: vi.fn(),
  fetchAnalysisRunDeletionPreflight: vi.fn(),
  fetchAnalysisRunResult: vi.fn(),
  fetchAnalysisRunStatus: vi.fn(),
  fetchAnalysisRuns: vi.fn(),
  fetchAttributeControlLimitSets: vi.fn(),
  fetchAttributeControlLimitSetDeletionPreflight: vi.fn(),
  fetchAttributeControlMonitoringPreflight: vi.fn(),
  fetchBayesianRecommendation: vi.fn(),
  fetchBayesianRecommendationBatch: vi.fn(),
  fetchBayesianStudy: vi.fn(),
  fetchBayesianStudyDeletionPreflight: vi.fn(),
  fetchBayesianStudies: vi.fn(),
  fetchLatestBayesianRecommendation: vi.fn(),
  fetchLatestBayesianRecommendationBatch: vi.fn(),
  fetchDatasetProfile: vi.fn(),
  fetchDatasetVersion: vi.fn(),
  fetchDatasetVersionDeletionPreflight: vi.fn(),
  fetchDatasetVersions: vi.fn(),
  fetchRowsPreview: vi.fn(),
  fetchRuntimeInfo: vi.fn(),
  fetchWorkspaceSummary: vi.fn(),
  fetchRegressionPredictionPreflight: vi.fn(),
  fetchRegressionPredictions: vi.fn(),
  fetchRegressionPredictionRows: vi.fn(),
  fetchRegressionModelDeletionPreflight: vi.fn(),
  fetchRegressionModelManifest: vi.fn(),
  fetchRegressionModels: vi.fn(),
  recordBayesianObservation: vi.fn(),
  updateDatasetSchema: vi.fn(),
  uploadDataset: vi.fn(),
}));

vi.mock("./api", () => apiMocks);

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve: (value: T) => void = () => undefined;
  let reject: (error: unknown) => void = () => undefined;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

interface StateSlot<T> {
  setValue: React.Dispatch<React.SetStateAction<T>>;
  value: T;
}

interface RefSlot<T> {
  current: T;
}

interface MemoSlot<T> {
  deps: React.DependencyList | undefined;
  value: T;
}

interface EffectSlot {
  create?: React.EffectCallback;
  cleanup: (() => void) | undefined;
  deps: React.DependencyList | undefined;
}

interface PendingEffect {
  create: React.EffectCallback;
  deps: React.DependencyList | undefined;
  slot: EffectSlot;
}

interface ReactInternals {
  ReactCurrentDispatcher: {
    current: unknown;
  };
}

const reactInternals = (
  React as unknown as {
    __SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED: ReactInternals;
  }
).__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;

function depsChanged(
  previous: React.DependencyList | undefined,
  next: React.DependencyList | undefined,
): boolean {
  if (previous === undefined || next === undefined || previous.length !== next.length) {
    return true;
  }
  return next.some((value, index) => !Object.is(value, previous[index]));
}

class HookRunner<Props, Result> {
  private cursor = 0;
  private readonly dispatcher: Record<string, unknown>;
  private outputValue: Result | undefined;
  private pending = true;
  private pendingEffects: PendingEffect[] = [];
  private props: Props;
  private readonly slots: unknown[] = [];

  constructor(
    private readonly hook: (props: Props) => Result,
    initialProps: Props,
  ) {
    this.props = initialProps;
    this.dispatcher = {
      useContext: (context: { _currentValue: unknown }) => context._currentValue,
      useCallback: <T extends (...args: never[]) => unknown>(
        callback: T,
        deps: React.DependencyList,
      ) => this.useMemo(() => callback, deps),
      useEffect: (create: React.EffectCallback, deps?: React.DependencyList) =>
        this.useEffect(create, deps),
      useMemo: <T>(factory: () => T, deps: React.DependencyList | undefined) =>
        this.useMemo(factory, deps),
      useRef: <T>(initialValue: T) => this.useRef(initialValue),
      useState: <T>(initialValue: T | (() => T)) => this.useState(initialValue),
    };
    this.flushSync();
  }

  get output(): Result {
    if (this.outputValue === undefined) {
      throw new Error("hook_test_output_unavailable");
    }
    return this.outputValue;
  }

  async act(action: () => void): Promise<void> {
    action();
    this.flushSync();
    await this.flush();
  }

  async flush(): Promise<void> {
    for (let index = 0; index < 8; index += 1) {
      await Promise.resolve();
      this.flushSync();
    }
  }

  update(props: Props): void {
    this.props = props;
    this.pending = true;
    this.flushSync();
  }

  unmount(): void {
    for (const slot of this.slots) {
      if (this.isEffectSlot(slot)) {
        slot.cleanup?.();
      }
    }
  }

  replayEffects(): void {
    for (const slot of this.slots) {
      if (this.isEffectSlot(slot)) {
        slot.cleanup?.();
        const cleanup = slot.create?.();
        slot.cleanup = typeof cleanup === "function" ? cleanup : undefined;
      }
    }
    this.flushSync();
  }

  private flushSync(): void {
    while (this.pending) {
      this.pending = false;
      this.cursor = 0;
      this.pendingEffects = [];
      const previousDispatcher = reactInternals.ReactCurrentDispatcher.current;
      reactInternals.ReactCurrentDispatcher.current = this.dispatcher;
      try {
        this.outputValue = this.hook(this.props);
      } finally {
        reactInternals.ReactCurrentDispatcher.current = previousDispatcher;
      }
      for (const pendingEffect of this.pendingEffects) {
        pendingEffect.slot.cleanup?.();
        const cleanup = pendingEffect.create();
        pendingEffect.slot.cleanup = typeof cleanup === "function" ? cleanup : undefined;
        pendingEffect.slot.create = pendingEffect.create;
        pendingEffect.slot.deps = pendingEffect.deps;
      }
    }
  }

  private isEffectSlot(value: unknown): value is EffectSlot {
    return typeof value === "object" && value !== null && "cleanup" in value;
  }

  private useEffect(create: React.EffectCallback, deps: React.DependencyList | undefined): void {
    const slotIndex = this.cursor;
    this.cursor += 1;
    let slot = this.slots[slotIndex] as EffectSlot | undefined;
    if (slot === undefined) {
      slot = { cleanup: undefined, deps: undefined };
      this.slots[slotIndex] = slot;
    }
    if (depsChanged(slot.deps, deps)) {
      this.pendingEffects.push({ create, deps, slot });
    }
  }

  private useMemo<T>(factory: () => T, deps: React.DependencyList | undefined): T {
    const slotIndex = this.cursor;
    this.cursor += 1;
    const existing = this.slots[slotIndex] as MemoSlot<T> | undefined;
    if (existing !== undefined && !depsChanged(existing.deps, deps)) {
      return existing.value;
    }
    const value = factory();
    this.slots[slotIndex] = { deps, value } satisfies MemoSlot<T>;
    return value;
  }

  private useRef<T>(initialValue: T): React.MutableRefObject<T> {
    const slotIndex = this.cursor;
    this.cursor += 1;
    let slot = this.slots[slotIndex] as RefSlot<T> | undefined;
    if (slot === undefined) {
      slot = { current: initialValue };
      this.slots[slotIndex] = slot;
    }
    return slot;
  }

  private useState<T>(
    initialValue: T | (() => T),
  ): [T, React.Dispatch<React.SetStateAction<T>>] {
    const slotIndex = this.cursor;
    this.cursor += 1;
    let slot = this.slots[slotIndex] as StateSlot<T> | undefined;
    if (slot === undefined) {
      const value = typeof initialValue === "function"
        ? (initialValue as () => T)()
        : initialValue;
      slot = {
        value,
        setValue: (nextValue) => {
          const currentSlot = this.slots[slotIndex] as StateSlot<T>;
          const resolved = typeof nextValue === "function"
            ? (nextValue as (previous: T) => T)(currentSlot.value)
            : nextValue;
          if (!Object.is(resolved, currentSlot.value)) {
            currentSlot.value = resolved;
            this.pending = true;
          }
        },
      };
      this.slots[slotIndex] = slot;
    }
    return [slot.value, slot.setValue];
  }
}

function historyResponse(datasetVersionId: string): AnalysisRunListResponse {
  return {
    dataset_version_id: datasetVersionId,
    method_id: null,
    status: null,
    stale: null,
    result_available: null,
    limit: 20,
    offset: 0,
    returned_count: 0,
    has_more: false,
    runs: [],
  };
}

const reportIdA = "10000000-0000-4000-8000-000000000001";
const reportIdB = "10000000-0000-4000-8000-000000000002";

function reportResult(analysisId: string): AnalysisResultEnvelope {
  return {
    analysis_id: analysisId,
    method_id: "eda.descriptive",
    method_version: "0.1.0",
    dataset_version_id: "dataset-a",
  } as AnalysisResultEnvelope;
}

describe("current analysis completion ownership", () => {
  const source: AnalysisExecutionSource = { datasetVersionId: "dataset-a", schemaHash: "a".repeat(64), methodId: "eda.descriptive", methodVersion: "0.1.0", workspace: "analysis" };
  const request = () => ({ dataset_version_id: source.datasetVersionId, method_id: source.methodId!, method_version: source.methodVersion!, roles: {}, options: { columns: ["x"] }, filter_snapshot: { expression_version: 1, conditions: [] } });
  function result(id = reportIdA): AnalysisResultEnvelope {
    return { ...reportResult(id), status: "succeeded", warnings: [], result: {}, provenance: {
      dataset_version_id: source.datasetVersionId, source_schema_hash: source.schemaHash,
      method_id: source.methodId!, method_version: source.methodVersion!, app_version: "test",
    } };
  }
  function status(id = reportIdA): AnalysisRunStatusResponse {
    return { analysis_id: id, dataset_version_id: source.datasetVersionId, method_id: source.methodId!, method_version: source.methodVersion!,
      status: "succeeded", stale: false, result_available: true, failure_code: null, config_schema_version: 1, artifact_count: 1,
      created_at: "2026-10-18", updated_at: "2026-10-18", completed_at: "2026-10-18" };
  }
  function runner() {
    apiMocks.fetchAnalysisRunStatus.mockResolvedValue(status());
    return new HookRunner(useCurrentAnalysisExecution, source);
  }
  it("holds the result until live completion status succeeds and clones request arrays", async () => {
    const held = deferred<AnalysisRunStatusResponse>();
    const run = runner();
    apiMocks.createAnalysisRun.mockResolvedValue(result());
    apiMocks.fetchAnalysisRunStatus.mockReturnValue(held.promise);
    const input = request();
    await run.act(() => { void run.output.execute(input); input.options.columns.push("later"); });
    expect((apiMocks.createAnalysisRun.mock.calls[0][0] as AnalysisRunRequest).options.columns).toEqual(["x"]);
    expect(run.output.result).toBeNull(); expect(run.output.isRunning).toBe(true);
    held.resolve(status()); await run.flush();
    expect(run.output.result?.analysis_id).toBe(reportIdA); expect(run.output.isRunning).toBe(false);
    run.unmount();
  });
  it.each(["dataset", "schema", "method", "workspace", "configuration", "aba"])("rejects late success after %s intent", async (change) => {
    const held = deferred<AnalysisResultEnvelope>(); const run = runner();
    apiMocks.createAnalysisRun.mockReturnValue(held.promise);
    await run.act(() => { void run.output.execute(request()); });
    if (change === "configuration") await run.act(() => run.output.invalidate());
    else {
      run.update({ ...source, ...(change === "schema" ? { schemaHash: "b".repeat(64) } : change === "method" ? { methodId: "eda.normality" } : change === "workspace" ? { workspace: "home" } : { datasetVersionId: "dataset-b" }) });
      if (change === "aba") run.update(source);
    }
    held.resolve(result()); await run.flush();
    expect(run.output.result).toBeNull(); expect(run.output.error).toBeNull(); expect(run.output.isRunning).toBe(false);
    expect(apiMocks.fetchAnalysisRunStatus).not.toHaveBeenCalled(); run.unmount();
  });
  it("does not let old catch/finally clear a newer running request", async () => {
    const old = deferred<AnalysisResultEnvelope>(), next = deferred<AnalysisResultEnvelope>(); const run = runner();
    apiMocks.createAnalysisRun.mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
    await run.act(() => { void run.output.execute(request()); });
    await run.act(() => { void run.output.execute(request()); });
    old.reject(new Error("obsolete_failure")); await run.flush();
    expect(run.output.isRunning).toBe(true); expect(run.output.error).toBeNull();
    next.resolve(result()); await run.flush(); expect(run.output.result?.analysis_id).toBe(reportIdA); run.unmount();
  });
  it("does not publish stale cross-tab completion even when immutable provenance matches", async () => {
    const run = runner(); apiMocks.createAnalysisRun.mockResolvedValue(result());
    apiMocks.fetchAnalysisRunStatus.mockResolvedValue({ ...status(), stale: true });
    await run.act(() => { void run.output.execute(request()); });
    expect(run.output.result).toBeNull(); expect(run.output.error).toBe("analysis_completion_source_changed");
    expect(run.output.savedAnalysisId).toBe(reportIdA); expect(run.output.canRetryVerification).toBe(false); run.unmount();
  });
  it("retries failed status verification without repeating analysis creation", async () => {
    const run = runner(); apiMocks.createAnalysisRun.mockResolvedValue(result());
    apiMocks.fetchAnalysisRunStatus.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(status());
    await run.act(() => { void run.output.execute(request()); });
    expect(run.output.error).toBe("analysis_completion_verification_failed"); expect(run.output.canRetryVerification).toBe(true);
    await run.act(() => { void run.output.retryVerification(); });
    expect(run.output.result?.analysis_id).toBe(reportIdA);
    expect(apiMocks.createAnalysisRun).toHaveBeenCalledTimes(1); expect(apiMocks.fetchAnalysisRunStatus).toHaveBeenCalledTimes(2); run.unmount();
  });
  it.each(["dataset_version_id", "method_id", "method_version", "schema", "missing"])("rejects returned %s mismatch before status lookup", async (field) => {
    const run = runner(); const payload = result();
    if (field === "schema") payload.provenance.source_schema_hash = "b".repeat(64);
    else if (field === "missing") payload.provenance.source_schema_hash = null;
    else Object.assign(payload, { [field]: "wrong" });
    apiMocks.createAnalysisRun.mockResolvedValue(payload);
    await run.act(() => { void run.output.execute(request()); });
    expect(run.output.result).toBeNull(); expect(run.output.error).toBe("analysis_completion_source_changed");
    expect(apiMocks.fetchAnalysisRunStatus).not.toHaveBeenCalled(); run.unmount();
  });
  it.each(["owner", "unavailable", "failed"])("rejects %s stored status", async (field) => {
    const run = runner(); apiMocks.createAnalysisRun.mockResolvedValue(result());
    apiMocks.fetchAnalysisRunStatus.mockResolvedValue({ ...status(), ...(field === "owner" ? { analysis_id: reportIdB } : field === "unavailable" ? { result_available: false } : { status: "failed" }) });
    await run.act(() => { void run.output.execute(request()); });
    expect(run.output.result).toBeNull(); expect(run.output.error).toBe("analysis_completion_verification_failed"); run.unmount();
  });
  it("ignores a status success after same-turn invalidation and preserves same-source rerenders", async () => {
    const held = deferred<AnalysisRunStatusResponse>(); const run = runner();
    apiMocks.createAnalysisRun.mockResolvedValue(result()); apiMocks.fetchAnalysisRunStatus.mockReturnValue(held.promise);
    await run.act(() => { void run.output.execute(request()); });
    run.update({ ...source }); expect(run.output.isRunning).toBe(true);
    run.output.invalidate(); held.resolve(status()); await run.flush();
    expect(run.output.result).toBeNull(); expect(run.output.error).toBeNull(); run.unmount();
  });
  it("does not perform status requests or writes after unmount", async () => {
    const held = deferred<AnalysisResultEnvelope>(); const run = runner();
    apiMocks.createAnalysisRun.mockReturnValue(held.promise);
    await run.act(() => { void run.output.execute(request()); }); run.unmount();
    held.resolve(result()); await run.flush(); expect(apiMocks.fetchAnalysisRunStatus).not.toHaveBeenCalled();
  });
  it("re-arms StrictMode effects without creating an execution automatically", async () => {
    const run = runner(); run.replayEffects();
    expect(apiMocks.createAnalysisRun).not.toHaveBeenCalled();
    apiMocks.createAnalysisRun.mockResolvedValue(result());
    await run.act(() => { void run.output.execute(request()); });
    expect(run.output.result?.analysis_id).toBe(reportIdA); run.unmount();
  });
  it("retains original API cause and rejects raw exception text as an error code", async () => {
    const run = runner(); const cause = new Error("Private user value or internal exception text");
    apiMocks.createAnalysisRun.mockRejectedValue(cause);
    await run.act(() => { void run.output.execute(request()); });
    expect(run.output.error).toBe("analysis_run_failed"); expect(run.output.errorCause).toBe(cause); run.unmount();
  });
  it("blocks new execution while an accepted dataset switch is pending", async () => {
    const run = runner(); run.update({ ...source, sourceChanging: true });
    await run.act(() => { void run.output.execute(request()); });
    expect(apiMocks.createAnalysisRun).not.toHaveBeenCalled();
    expect(run.output.error).toBe("analysis_completion_source_changed"); run.unmount();
  });
  it.each(["activation", "parsing"])("preserves completed A when accepted %s fails, but discards A's pending rerun", async (kind) => {
    const h = datasetWorkflowHarness(); await h.select(1);
    const id = h.versions[0].version_id;
    const run = new HookRunner(useCurrentAnalysisExecution, { ...source, datasetVersionId: id });
    const payload = { ...result(), dataset_version_id: id, provenance: { ...result().provenance, dataset_version_id: id } };
    apiMocks.createAnalysisRun.mockResolvedValueOnce(payload);
    apiMocks.fetchAnalysisRunStatus.mockResolvedValue({ ...status(), dataset_version_id: id });
    await run.act(() => { void run.output.execute({ ...request(), dataset_version_id: id }); });
    expect(run.output.result?.analysis_id).toBe(reportIdA);
    h.callbacks.onCommittedSourceIntent.mockImplementation(() => run.output.invalidate(false));
    h.callbacks.onDatasetReset.mockImplementation(() => run.output.invalidate());
    const pending = deferred<AnalysisResultEnvelope>(); apiMocks.createAnalysisRun.mockReturnValueOnce(pending.promise);
    await run.act(() => { void run.output.execute({ ...request(), dataset_version_id: id }); });
    if (kind === "activation") {
      apiMocks.fetchDatasetVersion.mockRejectedValueOnce(new Error("api_unreachable")); await h.select(2);
    } else {
      apiMocks.uploadDataset.mockResolvedValueOnce(workflowUpload(2));
      await h.file("replacement.csv"); await h.upload();
      apiMocks.confirmDatasetParsing.mockRejectedValueOnce(new Error("parsing_confirmation_failed"));
      await h.runner.act(() => h.runner.output.datasetPageProps.onConfirmParsing());
    }
    pending.reject(new Error("obsolete_failure")); await run.flush();
    expect(h.runner.output.version?.version_id).toBe(id);
    expect(run.output.result?.analysis_id).toBe(reportIdA); expect(run.output.error).toBeNull(); expect(run.output.isRunning).toBe(false);
    await run.act(() => run.output.invalidate()); expect(run.output.result).toBeNull();
    h.runner.unmount(); run.unmount();
  });
  it("preserves completed current results on failed history restore and retires them only on restore commit", async () => {
    const restore = deferred<AnalysisResultEnvelope>();
    apiMocks.createAnalysisRun.mockResolvedValue(result());
    apiMocks.fetchAnalysisRunStatus.mockResolvedValue(status());
    apiMocks.fetchAnalysisRunResult.mockReturnValueOnce(restore.promise);
    const exports = vi.fn(() => Promise.resolve());
    const run = new HookRunner(() => {
      const current = useCurrentAnalysisExecution(source);
      const history = useRestoredAnalysisResultState({
        analysisCatalog: null, currentAnalysisId: current.result?.analysis_id ?? null,
        currentDatasetVersionId: source.datasetVersionId, resetKey: 0,
        onRestoreIntent: () => current.invalidate(false), onRestoreCommitted: () => current.invalidate(),
        onSelectMethod: vi.fn(), onRefreshAnalysisResultExports: exports,
      });
      return { current, history };
    }, undefined);
    await run.act(() => { void run.output.current.execute(request()); });
    const pending = deferred<AnalysisResultEnvelope>();
    apiMocks.createAnalysisRun.mockReturnValueOnce(pending.promise);
    await run.act(() => { void run.output.current.execute(request()); });
    await run.act(() => run.output.history.onRestoreAnalysisRun(reportIdB));
    expect(run.output.current.result?.analysis_id).toBe(reportIdA);
    restore.reject(new Error("analysis_result_fetch_failed"));
    pending.resolve(result(reportIdB)); await run.flush();
    expect(run.output.current.result?.analysis_id).toBe(reportIdA);
    expect(run.output.current.isRunning).toBe(false);
    expect(run.output.history.restoredAnalysisResultError).toBe("analysis_result_fetch_failed");
    expect(exports).not.toHaveBeenCalled();
    apiMocks.fetchAnalysisRunResult.mockResolvedValueOnce(result(reportIdB));
    await run.act(() => run.output.history.onRestoreAnalysisRun(reportIdB));
    expect(run.output.current.result).toBeNull();
    expect(run.output.history.restoredAnalysisResult?.analysis_id).toBe(reportIdB);
    expect(exports).toHaveBeenCalledWith(reportIdB);
    run.unmount();
  });
  it("preserves completed results after unrelated dataset deletion but clears them when the active owner is deleted", async () => {
    const h = datasetWorkflowHarness(); await h.select(1);
    const id = h.versions[0].version_id;
    const run = new HookRunner(useCurrentAnalysisExecution, { ...source, datasetVersionId: id });
    apiMocks.createAnalysisRun.mockResolvedValue({ ...result(), dataset_version_id: id, provenance: { ...result().provenance, dataset_version_id: id } });
    apiMocks.fetchAnalysisRunStatus.mockResolvedValue({ ...status(), dataset_version_id: id });
    await run.act(() => { void run.output.execute({ ...request(), dataset_version_id: id }); });
    h.callbacks.onDatasetReset.mockImplementation(() => run.output.invalidate());
    await h.runner.act(() => h.runner.output.onDatasetDeleted(workflowDeletion(h.versions[1])));
    await run.flush();
    expect(run.output.result?.analysis_id).toBe(reportIdA);
    expect(h.runner.output.version?.version_id).toBe(id);
    await h.runner.act(() => h.runner.output.onDatasetDeleted(workflowDeletion(h.versions[0])));
    await run.flush();
    expect(run.output.result).toBeNull();
    expect(h.runner.output.version).toBeNull();
    h.runner.unmount(); run.unmount();
  });
  it("keeps a successful historical result when later export refresh or replacement restore fails", async () => {
    apiMocks.fetchAnalysisRunResult.mockResolvedValueOnce(result(reportIdB)).mockRejectedValueOnce(new Error("analysis_result_fetch_failed"));
    const run = new HookRunner(() => useRestoredAnalysisResultState({
      analysisCatalog: null, currentAnalysisId: null, currentDatasetVersionId: source.datasetVersionId, resetKey: 0,
      onSelectMethod: vi.fn(), onRefreshAnalysisResultExports: vi.fn(() => Promise.reject(new Error("export unavailable"))),
    }), undefined);
    await run.act(() => run.output.onRestoreAnalysisRun(reportIdB));
    expect(run.output.restoredAnalysisResult?.analysis_id).toBe(reportIdB);
    expect(run.output.restoredAnalysisResultError).toBe("analysis_export_list_fetch_failed");
    await run.act(() => run.output.onRestoreAnalysisRun(reportIdA));
    expect(run.output.restoredAnalysisResult?.analysis_id).toBe(reportIdB);
    expect(run.output.restoredAnalysisResultError).toBe("analysis_result_fetch_failed");
    run.unmount();
  });
  it.each(["method-navigation", "source-aba"])("cancels late history restore after %s without clearing an accepted payload", async (kind) => {
    const held = deferred<AnalysisResultEnvelope>();
    const selection = vi.fn(), exports = vi.fn(() => Promise.resolve());
    apiMocks.fetchAnalysisRunResult.mockResolvedValueOnce(result(reportIdA)).mockReturnValueOnce(held.promise);
    const run = new HookRunner(() => useRestoredAnalysisResultState({
      analysisCatalog: null, currentAnalysisId: null, currentDatasetVersionId: source.datasetVersionId,
      resetKey: 0, onSelectMethod: selection, onRefreshAnalysisResultExports: exports,
    }), undefined);
    await run.act(() => run.output.onRestoreAnalysisRun(reportIdA));
    await run.act(() => run.output.onRestoreAnalysisRun(reportIdB));
    expect(run.output.isRestoringAnalysisResult).toBe(true);
    await run.act(() => run.output.cancelPendingRestore());
    if (kind === "source-aba") await run.act(() => run.output.cancelPendingRestore());
    held.resolve(result(reportIdB)); await run.flush();
    expect(run.output.restoredAnalysisResult?.analysis_id).toBe(reportIdA);
    expect(run.output.isRestoringAnalysisResult).toBe(false);
    expect(run.output.restoredAnalysisResultError).toBeNull();
    expect(exports).toHaveBeenCalledTimes(1);
    expect(selection).not.toHaveBeenCalled();
    run.unmount();
  });
  it("keeps a committed history payload and refreshes its exports when its own method navigation cancels pending restore", async () => {
    const exports = vi.fn(() => Promise.resolve());
    let cancel: () => void = vi.fn();
    apiMocks.fetchAnalysisRunResult.mockResolvedValue(result(reportIdA));
    const run = new HookRunner(() => useRestoredAnalysisResultState({
      analysisCatalog: { methods: [{ method_id: source.methodId, module_id: "exploration" }] } as AnalysisMethodListResponse,
      currentAnalysisId: null, currentDatasetVersionId: source.datasetVersionId,
      resetKey: 0, onSelectMethod: () => cancel(), onRefreshAnalysisResultExports: exports,
    }), undefined);
    cancel = () => run.output.cancelPendingRestore();
    await run.act(() => run.output.onRestoreAnalysisRun(reportIdA));
    expect(run.output.restoredAnalysisResult?.analysis_id).toBe(reportIdA);
    expect(run.output.isRestoringAnalysisResult).toBe(false);
    expect(exports).toHaveBeenCalledWith(reportIdA);
    run.unmount();
  });
  it("does not let a cancelled restore error/finally clear a newer pending restore", async () => {
    const old = deferred<AnalysisResultEnvelope>(), next = deferred<AnalysisResultEnvelope>();
    apiMocks.fetchAnalysisRunResult.mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
    const run = new HookRunner(() => useRestoredAnalysisResultState({
      analysisCatalog: null, currentAnalysisId: null, currentDatasetVersionId: source.datasetVersionId,
      resetKey: 0, onSelectMethod: vi.fn(), onRefreshAnalysisResultExports: vi.fn(() => Promise.resolve()),
    }), undefined);
    await run.act(() => run.output.onRestoreAnalysisRun(reportIdA));
    await run.act(() => run.output.cancelPendingRestore());
    await run.act(() => run.output.onRestoreAnalysisRun(reportIdB));
    old.reject(new Error("analysis_result_fetch_failed")); await run.flush();
    expect(run.output.isRestoringAnalysisResult).toBe(true);
    expect(run.output.restoredAnalysisResultError).toBeNull();
    next.resolve(result(reportIdB)); await run.flush();
    expect(run.output.restoredAnalysisResult?.analysis_id).toBe(reportIdB);
    run.unmount();
  });
});

describe("local analysis input notifications", () => {
  function elements(node: unknown): React.ReactElement<Record<string, unknown>>[] {
    if (Array.isArray(node)) return node.flatMap(elements);
    if (React.isValidElement<Record<string, unknown>>(node)) return [node, ...Object.values(node.props).flatMap(elements)];
    return typeof node === "object" && node !== null ? Object.values(node).flatMap(elements) : [];
  }
  it.each(["pca", "pls", "gp", "two_variances"])("notifies synchronously for %s native run inputs, not mounting/rerendering", (kind) => {
    vi.stubGlobal("window", { confirm: vi.fn(() => true) });
    const changed = vi.fn(), execute = vi.fn();
    const props = { analysisResult: null, filterValidationError: null, isRunningAnalysis: false, methodId: kind,
      onRun: execute, result: null, version: workflowVersion(1), onAnalysisInputChange: changed };
    const run = new HookRunner(() => kind === "pca" ? PrincipalComponentsPanel(props) : kind === "pls" ? PlsRegressionPanel(props) :
      kind === "gp" ? GaussianProcessRegressionPanel(props) : TwoVariancesPanel({ ...props, filterDrafts: [] }), undefined);
    expect(changed).not.toHaveBeenCalled();
    run.update(undefined); expect(changed).not.toHaveBeenCalled();
    const inputs = elements(run.output).filter((item) => typeof item.type === "string" && typeof item.props.onChange === "function");
    expect(inputs.length).toBeGreaterThan(1);
    for (const input of inputs) {
      const before = changed.mock.calls.length;
      const current = input.props.value;
      const value = { value: typeof current === "number" || typeof current === "string" ? String(current) : "", checked: Boolean(input.props.checked) };
      (input.props.onChange as (event: unknown) => void)({ currentTarget: value, target: value });
      expect(changed).toHaveBeenCalledTimes(before + 1);
    }
    expect(execute).not.toHaveBeenCalled(); run.unmount();
  });
  it("does not invalidate a run when GP coordinate reset is cancelled", () => {
    vi.stubGlobal("window", { confirm: vi.fn(() => false) });
    const changed = vi.fn();
    const run = new HookRunner(() => GaussianProcessRegressionPanel({ analysisResult: null, filterValidationError: null,
      isRunningAnalysis: false, methodId: "regression.gaussian_process", onRun: vi.fn(), result: null,
      version: workflowVersion(1), onAnalysisInputChange: changed }), undefined);
    const reset = elements(run.output).find((item) => typeof item.props.onChange === "function" && String(item.props.onChange).includes("window.confirm"));
    expect(reset).toBeDefined();
    (reset!.props.onChange as (event: unknown) => void)({ currentTarget: { checked: false } });
    expect(changed).not.toHaveBeenCalled(); run.unmount();
  });
});

function reportWindow(query = "") {
  const events = new EventTarget();
  const location = { href: `http://127.0.0.1:8600/reports?tab=reports${query}#saved` };
  const history = {
    state: { navigation: "preserved" },
    replaceState: vi.fn((_state: unknown, _title: string, next: string) => {
      location.href = new URL(next, location.href).href;
    }),
  };
  vi.stubGlobal("window", {
    location,
    history,
    addEventListener: events.addEventListener.bind(events),
    removeEventListener: events.removeEventListener.bind(events),
  });
  return { location, history, events };
}

function exportListResponse(analysisId: string): AnalysisResultExportListResponse {
  return { analysis_id: analysisId, exports: [] };
}

function managedSource(index = 1): ReportSourceDescriptor {
  return { source: { kind: "analysis_run", analysis_id: `10000000-0000-4000-8000-${String(index).padStart(12, "0")}`, expected_source_sha256: String(index).repeat(64) }, source_ref_sha256: String(index).repeat(64), title: `Synthetic \uE000source-${index}\uE001`, created_at: "2026-10-18T00:00:00Z", stale: false, open_target: "/analysis/exploration/eda.descriptive" };
}
function managedArtifact(source = managedSource(), locale: "en" | "ko" = "en"): ManagedReportDescriptor {
  return { export_id: "20000000-0000-4000-8000-000000000001", source: source.source, source_ref_sha256: source.source_ref_sha256, locale, report_level: "summary", renderer_version: "1", sha256: "b".repeat(64), size_bytes: 100, created_at: source.created_at, stale: true, media_type: "text/html" };
}
function managedCapability(source = managedSource(), locale: "en" | "ko" = "en"): StoredReportCapability {
  return { capability_schema_version: 1, source: source.source, source_ref_sha256: source.source_ref_sha256, title: source.title, locale, stale: true, report_level: "summary", renderer_id: "synthetic", renderer_version: "1", sections: [{ section_id: "saved", title: source.title, status: "rendered", reason: null }], reason: null, html_available: true };
}
function managedSnapshot(source = managedSource(), locale: "en" | "ko" = "en"): StoredSourceSnapshot {
  return { schema_version: 1, source: source.source, source_ref_sha256: source.source_ref_sha256, locale, title: source.title, created_at: source.created_at, stale: true, payload: { stored_name: "<literal>\uE000name\uE001", value: .125 } };
}
function managedWindow(query = "?source_kind=analysis_run") {
  const events = new EventTarget();
  const location = { href: `http://127.0.0.1:8600/reports${query}`, get search() { return new URL(this.href).search; } };
  const set = (_state: unknown, _title: string, next: string) => { location.href = new URL(next, location.href).href; };
  vi.stubGlobal("window", { location, history: { state: {}, pushState: set, replaceState: set }, addEventListener: events.addEventListener.bind(events), removeEventListener: events.removeEventListener.bind(events), dispatchEvent: events.dispatchEvent.bind(events) });
  return { location, events };
}

describe("managed report independent owner lanes", () => {
  beforeEach(() => {
    Object.values(managedReportMocks).forEach((mock) => mock.mockReset());
    managedWindow();
    managedReportMocks.fetchReportSources.mockResolvedValue({ items: [managedSource()], limit: 20, offset: 0, has_more: false });
    managedReportMocks.fetchStoredReportCapability.mockImplementation((source: ReportSourceDescriptor["source"], locale: "en" | "ko") => Promise.resolve(managedCapability({ ...managedSource(), source, source_ref_sha256: source.kind === "analysis_run" ? source.expected_source_sha256 : "1".repeat(64) }, locale)));
    managedReportMocks.fetchManagedReports.mockResolvedValue({ items: [] });
  });

  it("preserves pending capability and artifact requests when the same source row is selected again", async () => {
    const source = managedSource();
    const heldCapability = deferred<StoredReportCapability>();
    const heldArtifacts = deferred<ManagedReportList>();
    managedReportMocks.fetchStoredReportCapability.mockReturnValueOnce(heldCapability.promise);
    managedReportMocks.fetchManagedReports.mockReturnValueOnce(heldArtifacts.promise);
    const runner = new HookRunner(() => useManagedReports("en", 0), undefined);
    await runner.flush();
    await runner.act(() => runner.output.select(source));
    await runner.act(() => runner.output.select(source));
    expect(managedReportMocks.fetchStoredReportCapability).toHaveBeenCalledTimes(1);
    expect(managedReportMocks.fetchManagedReports).toHaveBeenCalledTimes(1);
    heldCapability.resolve(managedCapability(source));
    heldArtifacts.resolve({ items: [managedArtifact(source)] });
    await runner.flush();
    expect(runner.output.capability.loading).toBe(false);
    expect(runner.output.capability.value?.source_ref_sha256).toBe(source.source_ref_sha256);
    expect(runner.output.artifacts.loading).toBe(false);
    expect(runner.output.artifacts.value?.items).toHaveLength(1);
    runner.unmount();
  });

  it("changes only the list lane on kind/page filters and keeps exact selected source and stale capability", async () => {
    const runner = new HookRunner(() => useManagedReports("en", 0), undefined);
    await runner.flush();
    await runner.act(() => runner.output.select(managedSource()));
    const capability = runner.output.capability.value;
    expect(capability?.stale).toBe(true);
    managedReportMocks.fetchReportSources.mockResolvedValue({ items: [], limit: 20, offset: 0, has_more: false });
    await runner.act(() => runner.output.changeKind("doe_analysis"));
    await runner.act(() => runner.output.changeOffset(20));
    expect(runner.output.selected?.source).toEqual(managedSource().source);
    expect(runner.output.capability.value).toBe(capability);
    expect(managedReportMocks.fetchStoredReportCapability).toHaveBeenCalledTimes(1);
    expect(managedReportMocks.fetchManagedReports).toHaveBeenCalledTimes(1);
    expect(managedReportMocks.fetchReportSources).toHaveBeenLastCalledWith("doe_analysis", 20);
    runner.unmount();
  });

  it("ignores late capability and creation after owner/locale/revision changes", async () => {
    const runner = new HookRunner((props: { locale: "en" | "ko"; revision: number }) => useManagedReports(props.locale, props.revision), { locale: "en", revision: 0 });
    await runner.flush();
    const lateCap = deferred<StoredReportCapability>();
    managedReportMocks.fetchStoredReportCapability.mockReturnValueOnce(lateCap.promise);
    await runner.act(() => runner.output.select(managedSource()));
    runner.update({ locale: "ko", revision: 0 }); await runner.flush();
    lateCap.resolve(managedCapability()); await runner.flush();
    expect(runner.output.capability.value?.locale).toBe("ko");
    const lateCreate = deferred<ManagedReportDescriptor>();
    managedReportMocks.createManagedReport.mockReturnValueOnce(lateCreate.promise);
    await runner.act(() => runner.output.createReport());
    expect(managedReportMocks.createManagedReport).toHaveBeenCalledWith(managedSource().source, "ko", "1".repeat(64));
    await runner.act(() => runner.output.select(managedSource(2)));
    lateCreate.resolve(managedArtifact(managedSource(), "ko")); await runner.flush();
    expect(runner.output.selected?.source_ref_sha256).toBe("2".repeat(64));
    expect(runner.output.linkedReport).toBeNull();
    expect(runner.output.action.busy).toBe(false);
    runner.update({ locale: "ko", revision: 1 }); await runner.flush();
    expect(managedReportMocks.fetchStoredReportCapability).toHaveBeenCalledTimes(4);
    runner.unmount();
  });

  it("validates direct report IDs before HTTP and restores an exact source without parsing navigation targets", async () => {
    managedWindow("?report_id=invalid");
    const invalid = new HookRunner(() => useManagedReports("en", 0), undefined); await invalid.flush();
    expect(invalid.output.routeError).toBe("managed_report_query_invalid");
    expect(managedReportMocks.fetchManagedReport).not.toHaveBeenCalled();
    expect(managedReportMocks.fetchReportSources).not.toHaveBeenCalled();
    invalid.unmount();
    const artifact = managedArtifact();
    managedWindow(`?report_id=${artifact.export_id}`);
    managedReportMocks.fetchReportSources.mockResolvedValue({ items: [], limit: 20, offset: 0, has_more: false });
    managedReportMocks.fetchManagedReport.mockResolvedValue(artifact);
    const restored = new HookRunner(() => useManagedReports("en", 0), undefined); await restored.flush();
    expect(restored.output.selected?.source).toEqual(artifact.source);
    expect(restored.output.linkedReport).toEqual(artifact);
    expect(restored.output.capability.value?.source_ref_sha256).toBe(artifact.source_ref_sha256);
    await restored.act(() => restored.output.select(managedSource()));
    const restoredQuery = new URL(window.location.href).searchParams;
    expect(restoredQuery.has("report_id")).toBe(false);
    expect(restoredQuery.get("source_kind")).toBe("regression_prediction");
    restored.unmount();
  });

  it("never lets a held direct-link read or deletion replace a newer selection", async () => {
    const artifact = managedArtifact(); managedWindow(`?report_id=${artifact.export_id}&source_kind=analysis_run`);
    const held = deferred<ManagedReportDescriptor>(); managedReportMocks.fetchManagedReport.mockReturnValueOnce(held.promise);
    const runner = new HookRunner(() => useManagedReports("en", 0), undefined); await runner.flush();
    await runner.act(() => runner.output.select(managedSource(2)));
    held.resolve(artifact); await runner.flush();
    expect(runner.output.selected?.source_ref_sha256).toBe("2".repeat(64));
    const lateDelete = deferred<{ deleted: true }>(); managedReportMocks.deleteManagedReport.mockReturnValueOnce(lateDelete.promise);
    await runner.act(() => runner.output.deleteReport(managedArtifact(managedSource(2))));
    await runner.act(() => runner.output.select(managedSource()));
    lateDelete.resolve({ deleted: true }); await runner.flush();
    expect(runner.output.selected?.source_ref_sha256).toBe("1".repeat(64));
    expect(runner.output.action.completed).toBeNull();
    runner.unmount();
  });

  it("keeps source discovery available when a valid report link was deleted", async () => {
    managedWindow(`?report_id=${managedArtifact().export_id}&source_kind=analysis_run`);
    managedReportMocks.fetchManagedReport.mockRejectedValue(new Error("managed_report_not_found"));
    const runner = new HookRunner(() => useManagedReports("en", 0), undefined); await runner.flush();
    expect(runner.output.routeError).toBe("managed_report_not_found");
    expect(runner.output.selected).toBeNull();
    expect(runner.output.list.value?.items).toHaveLength(1);
    await runner.act(() => runner.output.select(managedSource()));
    expect(runner.output.routeError).toBeNull();
    expect(runner.output.capability.value?.source_ref_sha256).toBe("1".repeat(64));
    runner.unmount();
  });

  it.each(["source", "locale"] as const)("does not resurrect cancelled busy state after %s A-B-A", async (change) => {
    const runner = new HookRunner<"en" | "ko", ReturnType<typeof useManagedReports>>((locale) => useManagedReports(locale, 0), "en");
    await runner.flush();
    await runner.act(() => runner.output.select(managedSource()));
    const held = deferred<ManagedReportDescriptor>();
    managedReportMocks.createManagedReport.mockReturnValueOnce(held.promise);
    await runner.act(() => runner.output.createReport());
    expect(runner.output.action.busy).toBe(true);
    if (change === "source") {
      await runner.act(() => runner.output.select(managedSource(2)));
      await runner.act(() => runner.output.select(managedSource()));
    } else {
      runner.update("ko"); await runner.flush();
      runner.update("en"); await runner.flush();
    }
    expect(runner.output.action.busy).toBe(false);
    held.resolve(managedArtifact()); await runner.flush();
    expect(runner.output.linkedReport).toBeNull();
    expect(runner.output.action.completed).toBeNull();
    runner.unmount();
  });

  it("does not turn a failed creation into an automatic retry or accept a foreign response", async () => {
    const runner = new HookRunner(() => useManagedReports("en", 0), undefined); await runner.flush();
    await runner.act(() => runner.output.select(managedSource()));
    managedReportMocks.createManagedReport.mockResolvedValueOnce(managedArtifact(managedSource(2)));
    await runner.act(() => runner.output.createReport());
    expect(runner.output.action.error).toBe("managed_report_source_invalid");
    expect(runner.output.linkedReport).toBeNull();
    expect(managedReportMocks.createManagedReport).toHaveBeenCalledTimes(1);
    runner.unmount();
  });

  it("loads exact snapshots only on intent, preserves list-only filters and rejects obsolete or foreign responses", async () => {
    const runner = new HookRunner<"en" | "ko", ReturnType<typeof useManagedReports>>((locale) => useManagedReports(locale, 0), "en"); await runner.flush();
    await runner.act(() => runner.output.select(managedSource()));
    expect(managedReportMocks.fetchStoredSourceSnapshot).not.toHaveBeenCalled();
    managedReportMocks.fetchStoredSourceSnapshot.mockResolvedValueOnce(managedSnapshot());
    await runner.act(() => { void runner.output.loadSnapshot(); });
    const saved = runner.output.snapshot.value;
    expect(saved?.payload).toEqual(managedSnapshot().payload);
    await runner.act(() => runner.output.changeOffset(20));
    expect(runner.output.snapshot.value).toBe(saved);
    expect(managedReportMocks.fetchStoredSourceSnapshot).toHaveBeenCalledTimes(1);
    const held = deferred<StoredSourceSnapshot>();
    managedReportMocks.fetchStoredSourceSnapshot.mockReturnValueOnce(held.promise);
    await runner.act(() => { void runner.output.loadSnapshot(); });
    runner.update("ko"); await runner.flush();
    expect(runner.output.snapshot.loading).toBe(false);
    expect(runner.output.snapshot.value).toBeNull();
    held.resolve(managedSnapshot()); await runner.flush();
    expect(runner.output.snapshot.value).toBeNull();
    managedReportMocks.fetchStoredSourceSnapshot.mockResolvedValueOnce(managedSnapshot(managedSource(2), "ko"));
    await runner.act(() => { void runner.output.loadSnapshot(); });
    expect(runner.output.snapshot.error).toBe("managed_report_source_invalid");
    expect(runner.output.snapshot.value).toBeNull();
    expect(managedReportMocks.fetchStoredSourceSnapshot).toHaveBeenLastCalledWith(managedSource().source, "ko");
    runner.unmount();
  });
});

function exportDeletionPreflight(
  analysisId: string,
  exportId: string,
): AnalysisResultExportDeletionPreflightResponse {
  return {
    preflight_schema_version: 1,
    analysis_id: analysisId,
    export_id: exportId,
    artifact_kind: "analysis_result_json_export",
    media_type: "application/json",
    sha256: "a".repeat(64),
    counts: { metadata_record_count: 1, file_count: 1, file_bytes: 128 },
    deletion_manifest_sha256: "b".repeat(64),
  };
}

function analysisDeletionPreflight(analysisId: string): AnalysisRunDeletionPreflightResponse {
  return {
    preflight_schema_version: 1,
    analysis_id: analysisId,
    method_id: "eda.descriptive",
    method_version: "0.1.0",
    status: "succeeded",
    stale: false,
    deletion_ready: true,
    blockers: [],
    counts: {
      analysis_run_count: 1,
      analysis_artifact_count: 1,
      result_file_count: 1,
      artifact_file_count: 1,
      export_file_count: 0,
      total_file_count: 2,
      file_bytes: 256,
      metadata_record_count: 2,
      regression_model_count: 0,
      regression_prediction_count: 0,
      attribute_control_limit_set_count: 0,
      job_reference_count: 0,
    },
    deletion_manifest_sha256: "c".repeat(64),
  };
}

function rowsPage(predictionId: string, offset: number): RegressionPredictionRowsPageResponse {
  return {
    prediction_id: predictionId,
    model_id: `model-${predictionId}`,
    offset,
    limit: 25,
    total: 50,
    returned: 0,
    has_previous: offset > 0,
    has_next: offset === 0,
    rows: [],
  };
}

function readyPreflight(
  modelId: string,
  targetDatasetVersionId: string,
): RegressionPredictionPreflightResponse {
  return {
    model_id: modelId,
    target_dataset_version_id: targetDatasetVersionId,
    prediction_ready: true,
  } as RegressionPredictionPreflightResponse;
}

function bayesianStudy(
  studyId: string,
  status: "active" | "completed" | "abandoned" = "active",
): BayesianStudyResponse {
  return {
    study_id: studyId,
    study_version_id: `${studyId}-version`,
    version_number: 1,
    study_schema_version: 1,
    method_id: "doe.bayesian_optimization",
    method_version: "0.2.2",
    name: `Study ${studyId}`,
    status,
    predecessor_study_id: null,
    created_at: "2026-07-19T00:00:00Z",
    updated_at: "2026-07-19T00:00:00Z",
    app_version: "0.1.0",
    definition_sha256: "a".repeat(64),
    factors: [
      {
        factor_id: "x",
        name: "X",
        low: 0,
        high: 1,
        unit: null,
        order: 1,
        scaling_rule: "linear_0_1",
      },
    ],
    objective: {
      name: "Y",
      unit: null,
      goal_type: "maximize",
      target_value: null,
      target_tolerance: null,
      direction: "maximize",
      observation_policy: "manual_single_observation",
    },
    constraints: [],
    initial_design: {
      policy: "sha256_counter_uniform_feasible_v1",
      seed: 20260719,
      requested_size: 2,
      generated_size: 2,
      attempt_limit: 2000,
      attempts_consumed: 2,
    },
    trial_count: 2,
    pending_trial_count: status === "active" ? 2 : 0,
    completed_trial_count: 0,
    abandoned_trial_count: status === "active" ? 0 : 2,
    observation_history: {
      history_revision_id: `${studyId}-history`,
      study_version_id: `${studyId}-version`,
      revision_number: 1,
      schema_version: 1,
      completed_trial_ids: [],
      completed_trial_count: 0,
      observation_history_sha256: "b".repeat(64),
      previous_history_sha256: null,
      created_at: "2026-07-19T00:00:00Z",
    },
    trials: [1, 2].map((trialNumber) => ({
      trial_id: `${studyId}-trial-${trialNumber}`,
      study_version_id: `${studyId}-version`,
      trial_number: trialNumber,
      origin: "initial_design" as const,
      state: status === "active" ? ("pending" as const) : ("abandoned" as const),
      actual_coordinates: { x: trialNumber / 3 },
      normalized_coordinates: { x: trialNumber / 3 },
      coordinates_sha256: `${trialNumber}`.repeat(64),
      objective_value: null,
      created_at: "2026-07-19T00:00:00Z",
      closed_at: status === "active" ? null : "2026-07-19T00:01:00Z",
    })),
    surrogate_available: false,
    recommendation_available: false,
    recommendation_minimum_completed_observations: 2,
    recommendation_hard_trial_limit: 200,
    recommendation_blockers: ["bayesian_optimization_history_incomplete"],
    lifecycle_event: null,
  };
}

function bayesianRecommendation(
  studyId: string,
  recommendationId: string,
  budget = 50,
): BayesianRecommendationResponse {
  return {
    recommendation_id: recommendationId,
    study_id: studyId,
    requested_total_trial_budget: budget,
  } as BayesianRecommendationResponse;
}

function bayesianRecommendationBatch(
  studyId: string,
  batchId: string,
): BayesianRecommendationBatchResponse {
  return {
    batch_id: batchId,
    study_id: studyId,
    execution_mode: "parallel_batch",
    batch_size: 4,
    acquisition: {
      kind: "expected_improvement",
      exploration_profile: "exploration",
      xi_standardized: 0.1,
    },
    requested_total_trial_budget: 50,
  } as BayesianRecommendationBatchResponse;
}

function bayesianDeletionPreflight(
  studyId: string,
  blockers: BayesianStudyDeletionPreflightResponse["blockers"] = [],
): BayesianStudyDeletionPreflightResponse {
  return {
    preflight_schema_version: 1,
    study_id: studyId,
    study_version_id: `${studyId}-version`,
    status: "abandoned",
    eligible: blockers.length === 0,
    blockers,
    successor_study_count: blockers.includes("bayesian_study_deletion_referenced") ? 1 : 0,
    counts: {
      study_count: 1,
      study_version_count: 1,
      trial_count: 2,
      history_revision_count: 1,
      history_head_count: 1,
      recommendation_count: 0,
      recommendation_batch_count: 0,
      recommendation_batch_item_count: 0,
      lifecycle_event_count: 1,
      metadata_record_count: 7,
      file_count: 0,
      file_bytes: 0,
    },
    deletion_manifest_sha256: "d".repeat(64),
  };
}

function datasetCatalogItem(index: number): DatasetVersionCatalogItem {
  return {
    version_id: `00000000-0000-4000-8000-${index.toString().padStart(12, "0")}`,
    dataset_id: `10000000-0000-4000-8000-${index.toString().padStart(12, "0")}`,
    original_filename: `synthetic-${index}.csv`,
    version_number: 1,
    row_count: index,
    column_count: 8,
    created_at: "2026-07-21T00:00:00Z",
    user_label: null,
    note: null,
    pinned: false,
    metadata_updated_at: null,
    archived: false,
    archived_at: null,
  };
}

function runtimeInfo(
  overrides: Partial<RuntimeInfoResponse> = {},
): RuntimeInfoResponse {
  return {
    service: "datalab-studio-api",
    app_version: "0.1.0",
    api_contract_version: 23,
    metadata_schema_version: 22,
    build_commit: "unknown",
    capabilities: {
      asset_management: true,
      dataset_version_metadata: true,
      dataset_version_deletion: true,
      dataset_version_archiving: true,
      dataset_version_cascade_deletion: true,
      dataset_version_preserve_unverified_cleanup: true,
      regression_model_metadata: true,
      regression_model_deletion: true,
      dedicated_predict: true,
      dedicated_response_optimizer: true,
      bayesian_optimization: true,
      graph_builder_preview: true,
      dataset_cell_correction: true,
      lhs_design: true,
      bayesian_lhs_initial_design: true,
      bayesian_batch_recommendation: true,
      bayesian_objective_goal_modes: true,
      gaussian_process_regression: true,
    },
    ...overrides,
  };
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.fetchRegressionModelManifest.mockResolvedValue({});
  apiMocks.fetchAnalysisRunStatus.mockImplementation((analysisId: string) => Promise.resolve({
    ...reportResult(analysisId), status: "succeeded", stale: false, result_available: true,
  }));
  apiMocks.fetchLatestBayesianRecommendationBatch.mockResolvedValue({
    study_id: "default-study",
    study_version_id: "default-study-version",
    item: null,
  });
  apiMocks.fetchDatasetVersions.mockResolvedValue({
    total: 0,
    offset: 0,
    limit: 20,
    returned: 0,
    has_previous: false,
    has_next: false,
    versions: [],
  });
  apiMocks.fetchRegressionModels.mockResolvedValue({
    models: [],
    total: 0,
    returned: 0,
    limit: 20,
    offset: 0,
    has_previous: false,
    has_next: false,
  });
});

afterEach(() => {
  Reflect.deleteProperty(globalThis, "window");
});

function workflowUpload(index: number): DatasetUploadResponse {
  return {
    dataset_id: datasetCatalogItem(index).dataset_id,
    original_filename: `synthetic-${index}.csv`,
    size_bytes: 6,
    sha256: "a".repeat(64),
    detected_format: "csv",
    parsing: {
      kind: "delimited_text", encoding_candidates: ["utf-8"],
      suggested_encoding: "utf-8", delimiter_candidates: [],
      suggested_delimiter: ",", quote_char: '"', decimal: ".", thousands: null,
      has_header: true, header_row: 1, data_start_row: 2,
      xlsx_requires_sheet_selection: false,
    },
    warnings: [], next_step: "confirm_schema",
  };
}

function workflowVersion(index: number): DatasetVersionResponse {
  const item = datasetCatalogItem(index);
  return {
    version_id: item.version_id, dataset_id: item.dataset_id,
    version_number: 1, row_count: 2, column_count: 1,
    schema_hash: index.toString(16).padStart(64, "0"), created_at: item.created_at,
    source_sha256: "a".repeat(64), canonical_artifact: null,
    parsing: {
      kind: "delimited_text", encoding: "utf-8", delimiter: ",", quote_char: '"',
      decimal: ".", thousands: null, has_header: true, header_row: 1,
      data_start_row: 2, missing_tokens: [], xlsx_sheet_name: null,
    },
    columns: [{
      column_id: `column-${index}`, version_id: item.version_id, column_index: 0,
      original_name: `value-${index}`, display_name: `value-${index}`,
      data_type: "decimal", measurement_level: "continuous", role: "feature", unit: null,
    }],
  };
}

function workflowPreview(version: DatasetVersionResponse): DatasetRowsPreviewResponse {
  return {
    version_id: version.version_id, offset: 0, limit: 10, total_rows: 2,
    returned_rows: 2, columns: version.columns,
    rows: [{ row_index: 0, values: ["1"] }, { row_index: 1, values: ["2"] }],
  };
}

function workflowProfile(version: DatasetVersionResponse): DatasetProfileResponse {
  return {
    profile_schema_version: 1, version_id: version.version_id,
    dataset_id: version.dataset_id, row_count: 2, column_count: 1,
    schema_hash: version.schema_hash, computed_at: version.created_at,
    unique_count_limit: 100, canonical_artifact: null, profile_artifact: null,
    preflight: {
      estimated_memory_bytes: 16, duplicate_row_count: 0,
      duplicate_row_count_capped: false, duplicate_row_check_limit: 100,
    },
    columns: [], warnings: [],
  };
}

function workflowSchema(version: DatasetVersionResponse): DatasetSchemaResponse {
  return { version_id: version.version_id, dataset_id: version.dataset_id, schema_hash: "a".repeat(64), columns: version.columns };
}

function workflowDeletion(version: DatasetVersionResponse): DatasetVersionDeleteResponse {
  return {
    deletion_schema_version: 3, version_id: version.version_id, dataset_id: version.dataset_id,
    deletion_scope: "version_only", deletion_manifest_sha256: "d".repeat(64), deleted_at: version.created_at,
    deletion_mode: "verified_files_and_metadata", operation_id: "delete_dataset_verified",
    preserved_unverified_file_count: 0, deleted_dependency_count: 0, cleanup_status: "deleted",
    deleted_counts: {
      dataset_version_count: 1, dataset_root_count: 0, dataset_column_count: 1,
      dataset_artifact_count: 1, artifact_file_count: 1, artifact_file_bytes: 16,
      raw_upload_file_count: 0, raw_upload_file_bytes: 0, sibling_version_count: 1,
      analysis_run_count: 0, regression_model_count: 0, prediction_source_count: 0,
      prediction_target_count: 0, analysis_export_count: 0, job_count: 0,
      attribute_control_limit_set_count: 0, phase_2_analysis_count: 0,
    },
  };
}

function datasetWorkflowHarness() {
  let href = "http://127.0.0.1/datasets?section=dataset-version";
  const storage = new Map<string, string>();
  const events = new EventTarget();
  const confirm = vi.fn(() => true);
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      get location() { return new URL(href); },
      history: {
        state: null,
        replaceState: (_state: unknown, _title: string, url: string) => {
          href = new URL(url, href).href;
        },
      },
      sessionStorage: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => storage.set(key, value),
        removeItem: (key: string) => storage.delete(key),
      },
      confirm,
      addEventListener: events.addEventListener.bind(events),
      removeEventListener: events.removeEventListener.bind(events),
      dispatchEvent: events.dispatchEvent.bind(events),
    },
  });
  const versions = [workflowVersion(1), workflowVersion(2), workflowVersion(3)];
  const versionFor = (id: string) => {
    const found = versions.find((item) => item.version_id === id);
    if (found === undefined) throw new Error("unexpected_test_version");
    return found;
  };
  apiMocks.fetchDatasetVersion.mockImplementation((id: string) => Promise.resolve(versionFor(id)));
  apiMocks.fetchRowsPreview.mockImplementation((id: string) => Promise.resolve(workflowPreview(versionFor(id))));
  apiMocks.fetchDatasetProfile.mockImplementation((id: string) => Promise.resolve(workflowProfile(versionFor(id))));
  const callbacks = {
    onCommittedSourceIntent: vi.fn(),
    onDatasetReset: vi.fn(), onDatasetColumnsChanged: vi.fn(),
    onDatasetVersionCreated: vi.fn(), onSchemaChanged: vi.fn(),
  };
  const runner = new HookRunner(useDatasetWorkflow, callbacks);
  const select = (index: number) => runner.act(() => {
    runner.output.activeDatasetSelectorProps.onSelect(versions[index - 1].version_id);
  });
  const file = (name: string) => runner.act(() => {
    runner.output.datasetPageProps.onFileChange({
      currentTarget: { files: [new File(["x\n1"], name)] },
    } as unknown as React.ChangeEvent<HTMLInputElement>);
  });
  const upload = () => runner.act(() => {
    runner.output.datasetPageProps.onUpload({ preventDefault: vi.fn() } as unknown as React.FormEvent<HTMLFormElement>);
  });
  const navigate = (id: string) => {
    const url = new URL(href);
    url.searchParams.set("dataset_version_id", id);
    href = url.href;
    events.dispatchEvent(new Event("popstate"));
  };
  return { runner, callbacks, versions, select, file, upload, storage, confirm, navigate, href: () => href };
}

describe("A05 dataset source isolation", () => {
  it("notifies accepted source intent synchronously but not cancelled navigation or intake drafts", async () => {
    const h = datasetWorkflowHarness(); await h.select(1); h.callbacks.onCommittedSourceIntent.mockClear();
    await h.file("draft.csv"); expect(h.callbacks.onCommittedSourceIntent).not.toHaveBeenCalled();
    h.confirm.mockReturnValueOnce(false); await h.select(2);
    expect(h.callbacks.onCommittedSourceIntent).not.toHaveBeenCalled();
    const held = deferred<DatasetVersionResponse>(); apiMocks.fetchDatasetVersion.mockReturnValueOnce(held.promise);
    h.runner.output.activeDatasetSelectorProps.onSelect(h.versions[1].version_id);
    expect(h.callbacks.onCommittedSourceIntent).toHaveBeenCalledTimes(1);
    held.resolve(h.versions[1]); await h.runner.flush(); h.runner.unmount();
  });
  it.each([false, true])("preserves failed-upload context unless replacement is approved: %s", async (approved) => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    await h.file("failed-upload.csv");
    apiMocks.uploadDataset.mockRejectedValueOnce(Object.assign(new Error("empty_file"), { code: "empty_file" }));
    await h.upload();
    expect(h.runner.output.flowError).toBe("empty_file");
    h.confirm.mockReturnValueOnce(approved);
    await h.file("replacement.csv");
    expect(h.confirm).toHaveBeenCalledOnce();
    expect(h.runner.output.datasetPageProps.selectedFile?.name).toBe(approved ? "replacement.csv" : "failed-upload.csv");
    expect(h.runner.output.flowError).toBe(approved ? null : "empty_file");
    expect(h.runner.output.version).toEqual(h.versions[0]);
    h.runner.unmount();
  });

  it("does not resurrect an upload error after an approved newer file selection", async () => {
    const h = datasetWorkflowHarness();
    await h.file("old-upload.csv");
    const old = deferred<DatasetUploadResponse>();
    apiMocks.uploadDataset.mockReturnValueOnce(old.promise);
    await h.upload();
    await h.file("new-upload.csv");
    old.reject(Object.assign(new Error("empty_file"), { code: "empty_file" }));
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.selectedFile?.name).toBe("new-upload.csv");
    expect(h.runner.output.flowError).toBeNull();
    expect(h.runner.output.datasetPageProps.isUploading).toBe(false);
    h.runner.unmount();
  });

  it("preserves the committed dataset when only a new file draft is selected", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const resets = h.callbacks.onDatasetReset.mock.calls.length;
    await h.file("replacement.csv");
    expect(h.runner.output.version?.version_id).toBe(h.versions[0].version_id);
    expect(h.storage.get("datalab.current_dataset_version_id")).toBe(h.versions[0].version_id);
    expect(new URL(h.href()).searchParams.get("dataset_version_id")).toBe(h.versions[0].version_id);
    expect(h.callbacks.onDatasetReset).toHaveBeenCalledTimes(resets);
    h.runner.unmount();
  });

  it("does not publish a late upload for an obsolete selected file", async () => {
    const h = datasetWorkflowHarness();
    const old = deferred<DatasetUploadResponse>();
    apiMocks.uploadDataset.mockReturnValueOnce(old.promise);
    await h.file("old.csv");
    await h.upload();
    await h.file("new.csv");
    old.resolve(workflowUpload(1));
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.selectedFile?.name).toBe("new.csv");
    expect(h.runner.output.datasetPageProps.upload).toBeNull();
    expect(h.runner.output.datasetPageProps.isUploading).toBe(false);
    h.runner.unmount();
  });

  it("restores the visible file selection when replacement is rejected", async () => {
    const h = datasetWorkflowHarness();
    await h.file("accepted.csv");
    h.confirm.mockReturnValue(false);
    const input = { files: [new File(["replacement"], "rejected.csv")], value: "rejected.csv" };
    await h.runner.act(() => h.runner.output.datasetPageProps.onFileChange({ currentTarget: input } as unknown as React.ChangeEvent<HTMLInputElement>));
    expect(h.runner.output.datasetPageProps.selectedFile?.name).toBe("accepted.csv");
    expect(input.files[0].name).toBe("accepted.csv");
    apiMocks.uploadDataset.mockResolvedValueOnce(workflowUpload(1));
    await h.upload();
    expect((apiMocks.uploadDataset.mock.calls[0][0] as File).name).toBe("accepted.csv");
    h.runner.unmount();
  });

  it("invalidates a pending paste when the user clears it, while reset acknowledgement preserves completed staging", async () => {
    const h = datasetWorkflowHarness();
    const old = deferred<DatasetUploadResponse>();
    apiMocks.createDatasetFromPastedText.mockReturnValueOnce(old.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onPasteDraftChange?.(true, "user"));
    const oldCompletion = h.runner.output.datasetPageProps.onPasteDataset("x\n1", true);
    await h.runner.flush();
    await h.runner.act(() => h.runner.output.datasetPageProps.onPasteDraftChange?.(false, "user"));
    old.resolve(workflowUpload(1));
    expect(await oldCompletion).toBe(false);
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.upload).toBeNull();
    expect(h.runner.output.datasetPageProps.isPastingDataset).toBe(false);
    apiMocks.createDatasetFromPastedText.mockResolvedValueOnce(workflowUpload(2));
    expect(await h.runner.output.datasetPageProps.onPasteDataset("x\n2", true)).toBe(true);
    await h.runner.flush();
    await h.runner.act(() => h.runner.output.datasetPageProps.onPasteDraftChange?.(false, "reset"));
    expect(h.runner.output.datasetPageProps.upload?.dataset_id).toBe(h.versions[1].dataset_id);
    h.runner.unmount();
  });

  it("does not accept an old paste after a dataset selection", async () => {
    const h = datasetWorkflowHarness();
    const old = deferred<DatasetUploadResponse>();
    apiMocks.createDatasetFromPastedText.mockReturnValueOnce(old.promise);
    const completion = h.runner.output.datasetPageProps.onPasteDataset("x\n1", true);
    await h.runner.flush();
    await h.select(2);
    old.resolve(workflowUpload(1));
    expect(await completion).toBe(false);
    await h.runner.flush();
    expect(h.runner.output.version?.version_id).toBe(h.versions[1].version_id);
    expect(h.runner.output.datasetPageProps.upload).toBeNull();
    h.runner.unmount();
  });

  it("does not activate a late parsing confirmation over the newer selection", async () => {
    const h = datasetWorkflowHarness();
    apiMocks.uploadDataset.mockResolvedValueOnce(workflowUpload(1));
    await h.file("old.csv");
    await h.upload();
    const old = deferred<DatasetVersionResponse>();
    apiMocks.confirmDatasetParsing.mockReturnValueOnce(old.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onConfirmParsing());
    await h.select(2);
    const readCount = apiMocks.fetchRowsPreview.mock.calls.length;
    old.resolve(h.versions[0]);
    await h.runner.flush();
    expect(h.runner.output.version?.version_id).toBe(h.versions[1].version_id);
    expect(apiMocks.fetchRowsPreview).toHaveBeenCalledTimes(readCount);
    expect(h.storage.get("datalab.current_dataset_version_id")).toBe(h.versions[1].version_id);
    h.runner.unmount();
  });

  it("does not publish an old schema write after switching versions", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const old = deferred<DatasetSchemaResponse>();
    apiMocks.updateDatasetSchema.mockReturnValueOnce(old.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    await h.select(2);
    old.resolve(workflowSchema(h.versions[0]));
    await h.runner.flush();
    expect(h.runner.output.version?.version_id).toBe(h.versions[1].version_id);
    expect(h.callbacks.onSchemaChanged).not.toHaveBeenCalled();
    h.runner.unmount();
  });

  it("preserves schema draft edits made after the submitted snapshot", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const old = deferred<DatasetSchemaResponse>();
    apiMocks.updateDatasetSchema.mockReturnValueOnce(old.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { display_name: "new unsaved label" }));
    old.resolve(workflowSchema(h.versions[0]));
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].display_name).toBe("new unsaved label");
    expect(h.runner.output.version?.schema_hash).toBe("a".repeat(64));
    expect(h.callbacks.onSchemaChanged).toHaveBeenCalledOnce();
    h.runner.unmount();
  });

  it("reconciles a saved active schema after intake intent changes without cancelling the newer upload", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const schemaSave = deferred<DatasetSchemaResponse>();
    const intake = deferred<DatasetUploadResponse>();
    apiMocks.updateDatasetSchema.mockReturnValueOnce(schemaSave.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    await h.file("new-intake.csv");
    apiMocks.uploadDataset.mockReturnValueOnce(intake.promise);
    await h.upload();
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { display_name: "still unsaved" }));
    const updated = { ...h.versions[0], schema_hash: "a".repeat(64), columns: [{ ...h.versions[0].columns[0], display_name: "saved label" }] };
    apiMocks.fetchDatasetProfile.mockResolvedValueOnce(workflowProfile(updated));
    schemaSave.resolve({ ...workflowSchema(updated), columns: updated.columns });
    await h.runner.flush();
    expect(h.runner.output.version?.schema_hash).toBe("a".repeat(64));
    expect(apiMocks.fetchDatasetVersion).toHaveBeenCalledOnce();
    expect(h.runner.output.version?.columns[0].display_name).toBe("saved label");
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].display_name).toBe("still unsaved");
    expect(h.callbacks.onSchemaChanged).toHaveBeenCalledWith(updated.columns);
    expect(h.runner.output.datasetPageProps.selectedFile?.name).toBe("new-intake.csv");
    expect(h.runner.output.datasetPageProps.isUploading).toBe(true);
    intake.resolve(workflowUpload(2));
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.upload?.dataset_id).toBe(h.versions[1].dataset_id);
    expect(h.runner.output.version?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.profile?.schema_hash).toBe("a".repeat(64));
    h.runner.unmount();
  });

  it("does not reconcile an old schema save over a newer save on the same active version", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const oldSave = deferred<DatasetSchemaResponse>();
    const newSave = deferred<DatasetSchemaResponse>();
    apiMocks.updateDatasetSchema.mockReturnValueOnce(oldSave.promise).mockReturnValueOnce(newSave.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    await h.file("new-intake.csv");
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { display_name: "newer label" }));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    const columns = [{ ...h.versions[0].columns[0], display_name: "newer label" }];
    newSave.resolve({ ...workflowSchema(h.versions[0]), schema_hash: "c".repeat(64), columns });
    await h.runner.flush();
    const versionReads = apiMocks.fetchDatasetVersion.mock.calls.length;
    oldSave.resolve(workflowSchema(h.versions[0]));
    await h.runner.flush();
    expect(h.runner.output.version?.schema_hash).toBe("c".repeat(64));
    expect(h.runner.output.version?.columns[0].display_name).toBe("newer label");
    expect(apiMocks.fetchDatasetVersion).toHaveBeenCalledTimes(versionReads);
    h.runner.unmount();
  });

  it("does not activate a completed old cell correction over a newer dataset", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const old = deferred<DatasetCellCorrectionResponse>();
    apiMocks.createDatasetCellCorrection.mockReturnValueOnce(old.promise);
    const completion = h.runner.output.datasetPageProps.onCreateCellCorrection!({
      confirmation_parent_version_id: h.versions[0].version_id,
      expected_parent_schema_hash: h.versions[0].schema_hash,
      expected_parent_canonical_sha256: "a".repeat(64),
      edits: [{ row_index: 0, column_id: "column-1", operation: "set_value", value: "3" }],
    });
    await h.runner.flush();
    await h.select(2);
    old.resolve({
      correction_schema_version: 1, parent_version_id: h.versions[0].version_id,
      new_version: { ...h.versions[2], dataset_id: h.versions[0].dataset_id, parent_version_id: h.versions[0].version_id }, changed_cell_count: 1, lineage_sha256: "b".repeat(64),
      created_at: h.versions[0].created_at,
    });
    await completion;
    await h.runner.flush();
    expect(h.runner.output.version?.version_id).toBe(h.versions[1].version_id);
    expect(h.storage.get("datalab.current_dataset_version_id")).toBe(h.versions[1].version_id);
    h.runner.unmount();
  });

  it("keeps a successfully restored version when only its profile fails", async () => {
    const h = datasetWorkflowHarness();
    apiMocks.fetchDatasetProfile.mockRejectedValueOnce(new Error("dataset_profile_failed"));
    await h.select(1);
    expect(h.runner.output.version?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.datasetPageProps.preview?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.profile).toBeNull();
    expect(h.storage.get("datalab.current_dataset_version_id")).toBe(h.versions[0].version_id);
    h.runner.unmount();
  });

  it("does not persist a selection response after unmount without bootstrap selection", async () => {
    const h = datasetWorkflowHarness();
    const old = deferred<DatasetVersionResponse>();
    apiMocks.fetchDatasetVersion.mockReturnValueOnce(old.promise);
    await h.select(1);
    h.runner.unmount();
    old.resolve(h.versions[0]);
    await h.runner.flush();
    expect(h.storage.size).toBe(0);
    expect(h.callbacks.onDatasetColumnsChanged).not.toHaveBeenCalled();
    expect(new URL(h.href()).searchParams.get("dataset_version_id")).toBeNull();
  });

  it("keeps the newer intake busy and error state when an old request fails", async () => {
    const h = datasetWorkflowHarness();
    const first = deferred<DatasetUploadResponse>();
    const second = deferred<DatasetUploadResponse>();
    apiMocks.uploadDataset.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    await h.file("first.csv");
    await h.upload();
    await h.file("second.csv");
    await h.upload();
    first.reject(new Error("obsolete raw failure"));
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.isUploading).toBe(true);
    expect(h.runner.output.flowError).toBeNull();
    second.resolve(workflowUpload(2));
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.upload?.dataset_id).toBe(h.versions[1].dataset_id);
    expect(h.runner.output.datasetPageProps.isUploading).toBe(false);
    h.runner.unmount();
  });

  it("retries a failed profile without refetching or losing the committed version", async () => {
    const h = datasetWorkflowHarness();
    apiMocks.fetchDatasetProfile.mockRejectedValueOnce(new Error("profile failed"));
    await h.select(1);
    expect(h.runner.output.datasetPageProps.profileError).toBe("dataset_profile_failed");
    await h.runner.act(() => h.runner.output.datasetPageProps.onLoadDatasetProfile(h.versions[0].version_id));
    expect(h.runner.output.profile?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.datasetPageProps.profileError).toBeNull();
    expect(apiMocks.fetchDatasetVersion).toHaveBeenCalledOnce();
    h.runner.unmount();
  });

  it("does not couple a preview failure to profile loading or active identity", async () => {
    const h = datasetWorkflowHarness();
    apiMocks.fetchRowsPreview.mockRejectedValueOnce(new Error("preview failed"));
    await h.select(1);
    expect(h.runner.output.profile?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.datasetPageProps.previewError).toBe("rows_preview_failed");
    expect(h.runner.output.datasetPageProps.profileError).toBeNull();
    await h.runner.act(() => h.runner.output.datasetPageProps.onLoadRowsPreview(h.versions[0].version_id, 0));
    expect(h.runner.output.datasetPageProps.preview?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.datasetPageProps.previewError).toBeNull();
    h.runner.unmount();
  });

  it("preserves the last good dataset when the replacement version cannot be loaded", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    apiMocks.fetchDatasetVersion.mockRejectedValueOnce(new Error("not found"));
    await h.select(2);
    expect(h.runner.output.version?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.activeDatasetSelectorProps.pendingVersionId).toBe(h.versions[1].version_id);
    expect(h.runner.output.activeDatasetSelectorProps.activationError).toBe("dataset_version_restore_failed");
    expect(h.storage.get("datalab.current_dataset_version_id")).toBe(h.versions[0].version_id);
    await h.runner.act(() => h.runner.output.activeDatasetSelectorProps.onRetrySwitch());
    expect(h.runner.output.version?.version_id).toBe(h.versions[1].version_id);
    expect(h.runner.output.activeDatasetSelectorProps.activationError).toBeNull();
    h.runner.unmount();
  });

  it("rejects an obsolete same-ID schema write after A-B-A selection", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const old = deferred<DatasetSchemaResponse>();
    apiMocks.updateDatasetSchema.mockReturnValueOnce(old.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    await h.select(2);
    await h.select(1);
    old.resolve(workflowSchema(h.versions[0]));
    await h.runner.flush();
    expect(h.runner.output.version?.schema_hash).toBe(h.versions[0].schema_hash);
    expect(h.callbacks.onSchemaChanged).not.toHaveBeenCalled();
    h.runner.unmount();
  });

  it.each(["service_unavailable", "network_error", "dataset_version_not_found"])("retains initial restore identity except confirmed missing version: %s", async (code) => {
    const h = datasetWorkflowHarness();
    h.runner.unmount();
    const id = h.versions[0].version_id;
    h.storage.set("datalab.current_dataset_version_id", id);
    window.history.replaceState(null, "", `/datasets?section=dataset-version&dataset_version_id=${id}`);
    apiMocks.fetchDatasetVersion.mockRejectedValueOnce(Object.assign(new Error("private server error"), { code }));
    const runner = new HookRunner(useDatasetWorkflow, h.callbacks);
    await runner.flush();
    expect(runner.output.version).toBeNull();
    expect(runner.output.activeDatasetSelectorProps.activationError).toBe(code);
    expect(h.storage.get("datalab.current_dataset_version_id")).toBe(code === "dataset_version_not_found" ? undefined : id);
    expect(new URL(h.href()).searchParams.get("dataset_version_id")).toBe(code === "dataset_version_not_found" ? null : id);
    expect(new URL(h.href()).searchParams.get("section")).toBe("dataset-version");
    await runner.act(() => runner.output.activeDatasetSelectorProps.onRetrySwitch());
    expect(runner.output.version?.version_id).toBe(id);
    expect(runner.output.activeDatasetSelectorProps.activationError).toBeNull();
    runner.unmount();
  });

  it("makes interrupted auxiliary reads retryable while a new intake draft preserves the active dataset", async () => {
    const h = datasetWorkflowHarness();
    const oldPreview = deferred<DatasetRowsPreviewResponse>();
    const oldProfile = deferred<DatasetProfileResponse>();
    apiMocks.fetchRowsPreview.mockReturnValueOnce(oldPreview.promise);
    apiMocks.fetchDatasetProfile.mockReturnValueOnce(oldProfile.promise);
    await h.select(1);
    expect(h.runner.output.datasetPageProps.isLoadingPreview).toBe(true);
    expect(h.runner.output.datasetPageProps.isLoadingProfile).toBe(true);
    await h.file("new-draft.csv");
    expect(h.runner.output.version?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.datasetPageProps.previewError).toBe("dataset_request_interrupted");
    expect(h.runner.output.datasetPageProps.profileError).toBe("dataset_request_interrupted");
    oldPreview.resolve(workflowPreview(h.versions[0]));
    oldProfile.resolve(workflowProfile(h.versions[0]));
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.preview).toBeNull();
    expect(h.runner.output.profile).toBeNull();
    await h.runner.act(() => h.runner.output.datasetPageProps.onLoadRowsPreview(h.versions[0].version_id, 0));
    await h.runner.act(() => h.runner.output.datasetPageProps.onLoadDatasetProfile(h.versions[0].version_id));
    expect(h.runner.output.datasetPageProps.preview?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.profile?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.datasetPageProps.previewError).toBeNull();
    expect(h.runner.output.datasetPageProps.profileError).toBeNull();
    expect(h.runner.output.datasetPageProps.selectedFile?.name).toBe("new-draft.csv");
    expect(h.storage.get("datalab.current_dataset_version_id")).toBe(h.versions[0].version_id);
    expect(apiMocks.fetchDatasetVersion).toHaveBeenCalledOnce();
    h.runner.unmount();
  });

  it("preserves schema edits, URL and requests when dirty selection is rejected", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { unit: "unsaved unit" }));
    h.confirm.mockReturnValue(false);
    await h.select(2);
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].unit).toBe("unsaved unit");
    expect(h.runner.output.version?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.activeDatasetSelectorProps.pendingVersionId).toBeNull();
    expect(apiMocks.fetchDatasetVersion).toHaveBeenCalledOnce();
    expect(new URL(h.href()).searchParams.get("dataset_version_id")).toBe(h.versions[0].version_id);
    h.runner.unmount();
  });

  it("reacts to same-mount dataset query navigation without changing unrelated query values", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    await h.runner.act(() => h.navigate(h.versions[1].version_id));
    expect(h.runner.output.version?.version_id).toBe(h.versions[1].version_id);
    expect(new URL(h.href()).searchParams.get("section")).toBe("dataset-version");
    h.runner.unmount();
  });

  it("rejects a mismatched preview and never renders a mismatched profile schema", async () => {
    const h = datasetWorkflowHarness();
    apiMocks.fetchRowsPreview.mockResolvedValueOnce(workflowPreview(h.versions[1]));
    apiMocks.fetchDatasetProfile.mockResolvedValueOnce({ ...workflowProfile(h.versions[0]), schema_hash: "wrong-schema" });
    await h.select(1);
    expect(h.runner.output.version?.version_id).toBe(h.versions[0].version_id);
    expect(h.runner.output.datasetPageProps.preview).toBeNull();
    expect(h.runner.output.profile).toBeNull();
    expect(h.runner.output.datasetPageProps.previewError).toBe("dataset_response_context_mismatch");
    expect(h.runner.output.datasetPageProps.profileError).toBe("dataset_response_context_mismatch");
    h.runner.unmount();
  });

  it("clears a deleted active source and rejects its pending write", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const old = deferred<DatasetSchemaResponse>();
    apiMocks.updateDatasetSchema.mockReturnValueOnce(old.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    await h.runner.act(() => h.runner.output.onDatasetDeleted(workflowDeletion(h.versions[0])));
    old.resolve(workflowSchema(h.versions[0]));
    await h.runner.flush();
    expect(h.runner.output.version).toBeNull();
    expect(h.storage.size).toBe(0);
    expect(h.callbacks.onSchemaChanged).not.toHaveBeenCalled();
    h.runner.unmount();
  });

  it("does not cancel a current source write when an unrelated dataset is deleted", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const old = deferred<DatasetSchemaResponse>();
    apiMocks.updateDatasetSchema.mockReturnValueOnce(old.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    await h.runner.act(() => h.runner.output.onDatasetDeleted(workflowDeletion(h.versions[1])));
    old.resolve(workflowSchema(h.versions[0]));
    await h.runner.flush();
    expect(h.runner.output.version?.schema_hash).toBe("a".repeat(64));
    expect(h.callbacks.onSchemaChanged).toHaveBeenCalledOnce();
    h.runner.unmount();
  });

  it("does not let old preview failure replace the new source read state", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const old = deferred<DatasetRowsPreviewResponse>();
    apiMocks.fetchRowsPreview.mockReturnValueOnce(old.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onLoadRowsPreview(h.versions[0].version_id, 0));
    await h.select(2);
    old.reject(new Error("late failed preview"));
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.preview?.version_id).toBe(h.versions[1].version_id);
    expect(h.runner.output.datasetPageProps.previewError).toBeNull();
    expect(h.runner.output.datasetPageProps.isLoadingPreview).toBe(false);
    h.runner.unmount();
  });

  it("keeps a newer raw paste draft when an older submission is cleared", async () => {
    const changed = vi.fn();
    const runner = new HookRunner(usePastedDatasetDraft, changed);
    const change = (value: string) => runner.act(() => runner.output.onRawTextChange({ currentTarget: { value } } as React.ChangeEvent<HTMLTextAreaElement>));
    await change("name\nold");
    const submitted = runner.output.getRevision();
    const literal = "name\n\uE000user-token\uE001";
    await change(literal);
    await runner.act(() => runner.output.clear(submitted));
    expect(runner.output.getRawText()).toBe(literal);
    expect(changed).toHaveBeenLastCalledWith(true, "user");
    await runner.act(() => runner.output.clear(runner.output.getRevision()));
    expect(runner.output.getRawText()).toBe("");
    expect(changed).toHaveBeenLastCalledWith(false, "user");
    runner.unmount();
  });

  it.each(["before", "after"] as const)("lets a newer paste complete when obsolete completion arrives %s it", async (completionOrder) => {
    const old = deferred<boolean>();
    const next = deferred<boolean>();
    const register = vi.fn().mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
    const runner = new HookRunner(usePastedDatasetSubmission, { isSubmitting: false, onRegister: register });
    const edit = (value: string) => runner.act(() => runner.output.draft.onRawTextChange({ currentTarget: { value } } as React.ChangeEvent<HTMLTextAreaElement>));
    const submit = () => runner.output.submit({ preventDefault: vi.fn() } as unknown as React.FormEvent<HTMLFormElement>);
    await edit("x\n1");
    const firstCompletion = submit();
    await runner.flush();
    expect(runner.output.isAwaitingSubmit).toBe(true);
    await edit("x\n2");
    expect(runner.output.isAwaitingSubmit).toBe(false);
    const secondCompletion = submit();
    await runner.flush();
    expect(register).toHaveBeenNthCalledWith(2, "x\n2", true);
    expect(runner.output.isAwaitingSubmit).toBe(true);
    if (completionOrder === "before") {
      old.resolve(true);
      await firstCompletion;
      await runner.flush();
      expect(runner.output.isAwaitingSubmit).toBe(true);
      expect(runner.output.draft.getRawText()).toBe("x\n2");
    }
    next.resolve(true);
    await secondCompletion;
    await runner.flush();
    expect(runner.output.isAwaitingSubmit).toBe(false);
    expect(runner.output.draft.getRawText()).toBe("");
    if (completionOrder === "after") {
      await edit("x\n\uE000new-unsaved\uE001");
      old.resolve(true);
      await firstCompletion;
      await runner.flush();
      expect(runner.output.draft.getRawText()).toBe("x\n\uE000new-unsaved\uE001");
      expect(runner.output.isAwaitingSubmit).toBe(false);
    }
    runner.unmount();
  });
});

describe("A07 schema compare-and-swap", () => {
  const conflictError = () => Object.assign(new Error("private conflict"), { code: "dataset_schema_conflict", status: 409 });

  it("preserves committed state and existing analysis callbacks after a successful schema no-op", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const before = h.runner.output;
    apiMocks.updateDatasetSchema.mockResolvedValueOnce({ ...workflowSchema(h.versions[0]), schema_hash: h.versions[0].schema_hash });
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { unit: " " }));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(h.callbacks.onSchemaChanged).not.toHaveBeenCalled();
    expect(h.runner.output.version).toBe(before.version);
    expect(h.runner.output.profile).toBe(before.profile);
    expect(h.runner.output.datasetPageProps.preview).toBe(before.datasetPageProps.preview);
    expect(apiMocks.fetchDatasetProfile).toHaveBeenCalledOnce();
    expect(apiMocks.fetchRowsPreview).toHaveBeenCalledOnce();
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].unit).toBe("");
    expect(h.runner.output.datasetPageProps.isSavingSchema).toBe(false);
    h.runner.unmount();
  });

  it("allows pending auxiliary reads and newer draft edits to survive a schema no-op", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const profile = deferred<DatasetProfileResponse>();
    const preview = deferred<DatasetRowsPreviewResponse>();
    const save = deferred<DatasetSchemaResponse>();
    apiMocks.fetchDatasetProfile.mockReturnValueOnce(profile.promise);
    apiMocks.fetchRowsPreview.mockReturnValueOnce(preview.promise);
    apiMocks.updateDatasetSchema.mockReturnValueOnce(save.promise);
    await h.runner.act(() => {
      h.runner.output.datasetPageProps.onLoadDatasetProfile(h.versions[0].version_id);
      h.runner.output.datasetPageProps.onLoadRowsPreview(h.versions[0].version_id, 0);
      h.runner.output.datasetPageProps.onSaveSchema();
    });
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { display_name: "new draft" }));
    save.resolve({ ...workflowSchema(h.versions[0]), schema_hash: h.versions[0].schema_hash });
    await h.runner.flush();
    expect(apiMocks.fetchDatasetProfile).toHaveBeenCalledTimes(2);
    expect(apiMocks.fetchRowsPreview).toHaveBeenCalledTimes(2);
    expect(h.runner.output.datasetPageProps.isLoadingProfile).toBe(true);
    expect(h.runner.output.datasetPageProps.isLoadingPreview).toBe(true);
    expect(h.callbacks.onSchemaChanged).not.toHaveBeenCalled();
    const nextProfile = workflowProfile(h.versions[0]);
    const nextPreview = workflowPreview(h.versions[0]);
    profile.resolve(nextProfile);
    preview.resolve(nextPreview);
    await h.runner.flush();
    expect(h.runner.output.profile).toBe(nextProfile);
    expect(h.runner.output.datasetPageProps.preview).toBe(nextPreview);
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].display_name).toBe("new draft");
    apiMocks.updateDatasetSchema.mockRejectedValueOnce(conflictError());
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(apiMocks.updateDatasetSchema.mock.calls[1][1]).toMatchObject({ expected_schema_hash: h.versions[0].schema_hash });
    expect(h.runner.output.datasetPageProps.schemaConflict?.status).toBe("ready");
    h.runner.unmount();
  });

  async function conflictHarness() {
    const h = datasetWorkflowHarness();
    await h.select(1);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { display_name: "local \uE000user\uE001" }));
    const latest = { ...h.versions[0], schema_hash: "b".repeat(64), columns: [{ ...h.versions[0].columns[0], unit: "mg", role: "response" as const }] };
    apiMocks.fetchDatasetVersion.mockResolvedValueOnce(latest);
    apiMocks.fetchDatasetProfile.mockResolvedValueOnce(workflowProfile(latest));
    apiMocks.updateDatasetSchema.mockRejectedValueOnce(conflictError());
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    return { ...h, latest };
  }

  it("stages only local field changes on the displayed latest base without issuing a write", async () => {
    const h = await conflictHarness();
    const calls = apiMocks.updateDatasetSchema.mock.calls.length;
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaConflictApply?.());
    expect(apiMocks.updateDatasetSchema).toHaveBeenCalledTimes(calls);
    expect(h.runner.output.datasetPageProps.schemaDrafts[0]).toMatchObject({ display_name: "local \uE000user\uE001", unit: "mg", role: "response" });
    expect(h.runner.output.datasetPageProps.schemaStaged).toBe(true);
    expect(h.runner.output.datasetPageProps.schemaConflict).toBeNull();
    apiMocks.updateDatasetSchema.mockResolvedValueOnce({ ...workflowSchema(h.latest), columns: [{ ...h.latest.columns[0], display_name: "local \uE000user\uE001" }] });
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(apiMocks.updateDatasetSchema.mock.calls[1][1]).toMatchObject({ expected_schema_hash: h.latest.schema_hash });
    h.runner.unmount();
  });

  it("preserves a re-edited draft and original base with no request until explicit Save", async () => {
    const h = await conflictHarness();
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaConflictEdit?.());
    expect(apiMocks.updateDatasetSchema).toHaveBeenCalledOnce();
    expect(apiMocks.fetchDatasetVersion).toHaveBeenCalledTimes(2);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { unit: "local second unit" }));
    expect(h.runner.output.datasetPageProps.schemaConflict?.baseHash).toBe(h.versions[0].schema_hash);
    expect(h.runner.output.datasetPageProps.schemaComparison?.find((item) => item.field === "unit")).toMatchObject({ draft: "local second unit", latest: "mg", conflicting: true });
    h.runner.unmount();
  });

  it("requires confirmation to discard and never writes when loading the latest draft", async () => {
    const h = await conflictHarness();
    h.confirm.mockReturnValueOnce(false);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaConflictDiscard?.());
    expect(h.runner.output.datasetPageProps.schemaConflict?.status).toBe("ready");
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].display_name).toContain("local");
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaConflictDiscard?.());
    expect(h.runner.output.datasetPageProps.schemaConflict).toBeNull();
    expect(h.runner.output.datasetPageProps.schemaDrafts[0]).toMatchObject({ display_name: h.latest.columns[0].display_name, unit: "mg", role: "response" });
    expect(apiMocks.updateDatasetSchema).toHaveBeenCalledOnce();
    apiMocks.updateDatasetSchema.mockResolvedValueOnce(workflowSchema(h.latest));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(apiMocks.updateDatasetSchema.mock.calls[1][1]).toMatchObject({ expected_schema_hash: h.latest.schema_hash });
    h.runner.unmount();
  });

  it("handles a second conflict after explicit Apply without silently rebasing again", async () => {
    const h = await conflictHarness();
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaConflictApply?.());
    const newer = { ...h.latest, schema_hash: "c".repeat(64), columns: [{ ...h.latest.columns[0], unit: "g" }] };
    apiMocks.fetchDatasetVersion.mockResolvedValueOnce(newer);
    apiMocks.updateDatasetSchema.mockRejectedValueOnce(conflictError());
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(h.runner.output.datasetPageProps.schemaConflict).toMatchObject({ status: "ready", baseHash: h.latest.schema_hash, latest: newer });
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].unit).toBe("mg");
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaConflictApply?.());
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].unit).toBe("g");
    expect(apiMocks.updateDatasetSchema).toHaveBeenCalledTimes(2);
    h.runner.unmount();
  });

  it("retries only the failed latest read while preserving edits and the original base", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    apiMocks.fetchDatasetVersion.mockRejectedValueOnce(Object.assign(new Error("sensitive"), { code: "network_error" }));
    apiMocks.updateDatasetSchema.mockRejectedValueOnce(conflictError());
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(h.runner.output.datasetPageProps.schemaConflict).toMatchObject({ status: "failed", errorCode: "network_error" });
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { unit: "keep" }));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaConflictRetry?.());
    expect(apiMocks.updateDatasetSchema).toHaveBeenCalledOnce();
    expect(h.runner.output.datasetPageProps.schemaConflict?.status).toBe("ready");
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].unit).toBe("keep");
    h.runner.unmount();
  });

  it.each(["switch", "aba", "delete", "unmount"] as const)("ignores a late comparison after %s", async (action) => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const held = deferred<DatasetVersionResponse>();
    apiMocks.fetchDatasetVersion.mockReturnValueOnce(held.promise);
    apiMocks.updateDatasetSchema.mockRejectedValueOnce(conflictError());
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    if (action === "switch" || action === "aba") await h.select(2);
    if (action === "aba") await h.select(1);
    if (action === "delete") await h.runner.act(() => h.runner.output.onDatasetDeleted(workflowDeletion(h.versions[0])));
    if (action === "unmount") h.runner.unmount();
    const previous = h.runner.output.version;
    held.resolve({ ...h.versions[0], schema_hash: "b".repeat(64) });
    await h.runner.flush();
    expect(h.runner.output.version).toBe(previous);
    expect(h.callbacks.onSchemaChanged).not.toHaveBeenCalled();
    h.runner.unmount();
  });

  it("does not cancel newer intake when comparison publishes known committed metadata", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const held = deferred<DatasetVersionResponse>();
    apiMocks.fetchDatasetVersion.mockReturnValueOnce(held.promise);
    apiMocks.updateDatasetSchema.mockRejectedValueOnce(conflictError());
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    await h.file("new.csv");
    const intake = deferred<DatasetUploadResponse>();
    apiMocks.uploadDataset.mockReturnValueOnce(intake.promise);
    await h.upload();
    held.resolve({ ...h.versions[0], schema_hash: "b".repeat(64) });
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.isUploading).toBe(true);
    intake.resolve(workflowUpload(2));
    await h.runner.flush();
    expect(h.runner.output.datasetPageProps.upload?.dataset_id).toBe(h.versions[1].dataset_id);
    expect(h.runner.output.datasetPageProps.schemaConflict?.status).toBe("ready");
    h.runner.unmount();
  });

  it("submits the draft base hash with schema changes", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    apiMocks.updateDatasetSchema.mockResolvedValueOnce(workflowSchema(h.versions[0]));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { unit: "kg" }));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(apiMocks.updateDatasetSchema.mock.calls[0][1]).toMatchObject({ expected_schema_hash: h.versions[0].schema_hash });
    h.runner.unmount();
  });

  it("advances the base only for a clean acknowledged draft and rejects malformed bases before PATCH", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    apiMocks.updateDatasetSchema.mockResolvedValueOnce(workflowSchema(h.versions[0]));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    apiMocks.updateDatasetSchema.mockResolvedValueOnce(workflowSchema(h.versions[0]));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(apiMocks.updateDatasetSchema.mock.calls[1][1]).toMatchObject({ expected_schema_hash: "a".repeat(64) });
    h.versions[1].schema_hash = "invalid-short-hash";
    await h.select(2);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(apiMocks.updateDatasetSchema).toHaveBeenCalledTimes(2);
    expect(h.runner.output.flowError).toBe("dataset_schema_base_invalid");
    h.runner.unmount();
  });

  it("does not publish a latest response with mismatched column identity", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    apiMocks.fetchDatasetVersion.mockResolvedValueOnce({ ...h.versions[0], schema_hash: "b".repeat(64), columns: [{ ...h.versions[0].columns[0], column_id: "other-column" }] });
    apiMocks.updateDatasetSchema.mockRejectedValueOnce(conflictError());
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(h.runner.output.datasetPageProps.schemaConflict).toMatchObject({ status: "failed", errorCode: "dataset_schema_comparison_mismatch" });
    expect(h.runner.output.version).toEqual(h.versions[0]);
    expect(h.callbacks.onSchemaChanged).not.toHaveBeenCalled();
    h.runner.unmount();
  });

  it("does not silently rebase newer edits onto an acknowledged earlier save", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    const first = deferred<DatasetSchemaResponse>();
    apiMocks.updateDatasetSchema.mockReturnValueOnce(first.promise);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { unit: "new unit" }));
    first.resolve(workflowSchema(h.versions[0]));
    await h.runner.flush();
    apiMocks.updateDatasetSchema.mockRejectedValueOnce(Object.assign(new Error("conflict"), { code: "dataset_schema_conflict", status: 409 }));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(apiMocks.updateDatasetSchema.mock.calls[1][1]).toMatchObject({ expected_schema_hash: h.versions[0].schema_hash });
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].unit).toBe("new unit");
    h.runner.unmount();
  });

  it("loads latest metadata for conflict comparison without replacing the user's draft or retrying the write", async () => {
    const h = datasetWorkflowHarness();
    await h.select(1);
    await h.runner.act(() => h.runner.output.datasetPageProps.onSchemaDraftChange("column-1", { unit: "local unit" }));
    const latest = { ...h.versions[0], schema_hash: "b".repeat(64), columns: [{ ...h.versions[0].columns[0], role: "response" as const }] };
    apiMocks.fetchDatasetVersion.mockResolvedValueOnce(latest);
    apiMocks.fetchDatasetProfile.mockResolvedValueOnce(workflowProfile(latest));
    apiMocks.updateDatasetSchema.mockRejectedValueOnce(Object.assign(new Error("private conflict message"), { code: "dataset_schema_conflict", status: 409 }));
    await h.runner.act(() => h.runner.output.datasetPageProps.onSaveSchema());
    expect(apiMocks.fetchDatasetVersion).toHaveBeenCalledTimes(2);
    expect(apiMocks.updateDatasetSchema).toHaveBeenCalledOnce();
    expect(h.runner.output.datasetPageProps.schemaDrafts[0].unit).toBe("local unit");
    expect(h.runner.output.version?.schema_hash).toBe(latest.schema_hash);
    expect(h.callbacks.onSchemaChanged).toHaveBeenCalledWith(latest.columns);
    h.runner.unmount();
  });
});

describe("async workbench hooks", () => {
  it("keeps successful project cards when one overview request fails", async () => {
    apiMocks.fetchWorkspaceSummary.mockRejectedValueOnce(
      new Error("workspace_summary_fetch_failed"),
    );
    apiMocks.fetchDatasetVersions.mockResolvedValueOnce({
      total: 1,
      offset: 0,
      limit: 3,
      returned: 1,
      has_previous: false,
      has_next: false,
      versions: [datasetCatalogItem(1)],
    });
    apiMocks.fetchAnalysisRuns.mockResolvedValueOnce(historyResponse("version-1"));

    const runner = new HookRunner<
      number,
      ReturnType<typeof useProjectOverviewState>
    >(useProjectOverviewState, 0);
    await runner.flush();

    expect(runner.output.summary.error).toBe("workspace_summary_fetch_failed");
    expect(runner.output.recentDatasets.data?.versions).toHaveLength(1);
    expect(runner.output.recentAnalyses.data?.runs).toEqual([]);
    expect(runner.output.recentModels.data?.models).toEqual([]);
    runner.unmount();
  });

  it("refreshes both management catalogs after a workspace mutation", async () => {
    const runner = new HookRunner<
      number,
      ReturnType<typeof useAssetManagementState>
    >(useAssetManagementState, 0);
    await runner.flush();

    expect(apiMocks.fetchDatasetVersions).toHaveBeenCalledTimes(1);
    expect(apiMocks.fetchRegressionModels).toHaveBeenCalledTimes(1);

    runner.update(1);
    await runner.flush();

    expect(apiMocks.fetchDatasetVersions).toHaveBeenCalledTimes(2);
    expect(apiMocks.fetchRegressionModels).toHaveBeenCalledTimes(2);
    runner.unmount();
  });

  it("blocks an old runtime and retries into the compatible contract", async () => {
    const oldRuntime = runtimeInfo({ api_contract_version: 1 });
    apiMocks.fetchRuntimeInfo.mockResolvedValueOnce(oldRuntime);
    const runner = new HookRunner<void, ReturnType<typeof useRuntimeCompatibilityState>>(
      useRuntimeCompatibilityState,
      undefined,
    );
    await runner.flush();

    expect(runner.output.state.kind).toBe("blocked");
    expect(runner.output.state.error).toBe("api_contract_version_mismatch");

    apiMocks.fetchRuntimeInfo.mockResolvedValueOnce(runtimeInfo());
    await runner.act(() => runner.output.retry());

    expect(runner.output.state.kind).toBe("compatible");
    runner.unmount();
  });

  it("ignores an old dataset deletion preflight after the managed version changes", async () => {
    const first = deferred<DatasetVersionDeletionPreflightResponse>();
    const second = deferred<DatasetVersionDeletionPreflightResponse>();
    apiMocks.fetchDatasetVersionDeletionPreflight
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const onDeleted = vi.fn();
    const useTestDatasetRetention = (props: {
      versionId: string;
      onDeleted: typeof onDeleted;
    }) =>
      useDatasetVersionRetentionState(props.versionId, props.onDeleted);
    const runner = new HookRunner(useTestDatasetRetention, {
      versionId: "version-a",
      onDeleted,
    });
    await runner.act(() => runner.output.onLoadPreflight());
    runner.update({ versionId: "version-b", onDeleted });
    await runner.act(() => runner.output.onLoadPreflight());
    second.resolve({
      version_id: "version-b",
      deletion_ready: true,
    } as DatasetVersionDeletionPreflightResponse);
    await runner.flush();
    first.resolve({
      version_id: "version-a",
      deletion_ready: true,
    } as DatasetVersionDeletionPreflightResponse);
    await runner.flush();

    expect(runner.output.preflight?.version_id).toBe("version-b");
    expect(runner.output.isLoadingPreflight).toBe(false);
    runner.unmount();
  });

  it("deletes only a matching ready dataset version and reports completion", async () => {
    const preflight = {
      version_id: "version-a",
      deletion_ready: true,
      verified_delete_ready: true,
      metadata_only_cleanup_ready: false,
      deletion_manifest_sha256: "a".repeat(64),
      verified_deletion_manifest_sha256: "a".repeat(64),
      metadata_only_deletion_manifest_sha256: null,
      available_operations: [
        {
          affected_asset_count: 1,
          blockers: [],
          dependency_policy: "block",
          manifest_sha256: "a".repeat(64),
          operation_id: "delete_dataset_verified",
          preserved_unverified_file_count: 0,
          ready: true,
          unverified_file_policy: "block",
          verified_file_bytes: 100,
          verified_file_count: 1,
        },
      ],
    } as unknown as DatasetVersionDeletionPreflightResponse;
    const response = {
      version_id: "version-a",
      cleanup_status: "deleted",
    } as DatasetVersionDeleteResponse;
    apiMocks.fetchDatasetVersionDeletionPreflight.mockResolvedValue(preflight);
    apiMocks.deleteDatasetVersion.mockResolvedValue(response);
    const onDeleted = vi.fn();
    const runner = new HookRunner(
      (versionId: string) => useDatasetVersionRetentionState(versionId, onDeleted),
      "version-a",
    );
    await runner.act(() => runner.output.onLoadPreflight());
    await runner.act(() => runner.output.onDelete(runner.output.preflight!));

    expect(apiMocks.deleteDatasetVersion).toHaveBeenCalledWith(
      preflight,
      "delete_dataset_verified",
    );
    expect(runner.output.deletion).toEqual(response);
    expect(onDeleted).toHaveBeenCalledWith(response);
    runner.unmount();
  });

  it("keeps the latest active-dataset catalog page when an older response arrives late", async () => {
    const first = deferred<DatasetVersionCatalogResponse>();
    const second = deferred<DatasetVersionCatalogResponse>();
    apiMocks.fetchDatasetVersions.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const runner = new HookRunner<
      string | null,
      ReturnType<typeof useDatasetVersionCatalogState>
    >(useDatasetVersionCatalogState, null);

    await runner.act(() => runner.output.onPageChange(20));
    second.resolve({
      total: 21,
      offset: 20,
      limit: 20,
      returned: 1,
      has_previous: true,
      has_next: false,
      versions: [datasetCatalogItem(21)],
    });
    await runner.flush();
    first.resolve({
      total: 21,
      offset: 0,
      limit: 20,
      returned: 0,
      has_previous: false,
      has_next: true,
      versions: [],
    });
    await runner.flush();

    expect(apiMocks.fetchDatasetVersions).toHaveBeenNthCalledWith(1, 20, 0);
    expect(apiMocks.fetchDatasetVersions).toHaveBeenNthCalledWith(2, 20, 20);
    expect(runner.output.catalog?.offset).toBe(20);
    expect(runner.output.catalog?.versions[0]?.row_count).toBe(21);
    expect(runner.output.isLoading).toBe(false);
    runner.unmount();
  });

  it("resolves an active dataset version outside the current catalog page by exact ID", async () => {
    const activeItem = datasetCatalogItem(21);
    apiMocks.fetchDatasetVersions
      .mockResolvedValueOnce({
        total: 21,
        offset: 0,
        limit: 20,
        returned: 20,
        has_previous: false,
        has_next: true,
        versions: Array.from({ length: 20 }, (_, index) => datasetCatalogItem(index + 1)),
      })
      .mockResolvedValueOnce({
        total: 21,
        offset: 20,
        limit: 20,
        returned: 1,
        has_previous: true,
        has_next: false,
        versions: [activeItem],
      });
    const runner = new HookRunner<
      string | null,
      ReturnType<typeof useDatasetVersionCatalogState>
    >(useDatasetVersionCatalogState, activeItem.version_id);
    await runner.flush();

    expect(apiMocks.fetchDatasetVersions).toHaveBeenNthCalledWith(1, 20, 0);
    expect(apiMocks.fetchDatasetVersions).toHaveBeenNthCalledWith(2, 20, 20);
    expect(runner.output.catalog?.offset).toBe(0);
    expect(runner.output.activeItem).toEqual(activeItem);
    expect(runner.output.isResolvingActiveItem).toBe(false);
    runner.unmount();
  });

  it("publishes only the latest selected dataset version, preview, and profile", async () => {
    const versionA = deferred<DatasetVersionResponse>();
    const versionB = deferred<DatasetVersionResponse>();
    const previewA = deferred<DatasetRowsPreviewResponse>();
    const previewB = deferred<DatasetRowsPreviewResponse>();
    const profileA = deferred<DatasetProfileResponse>();
    const profileB = deferred<DatasetProfileResponse>();
    apiMocks.fetchDatasetVersion.mockReturnValueOnce(versionA.promise).mockReturnValueOnce(versionB.promise);
    apiMocks.fetchRowsPreview.mockImplementation((id: string) => id === workflowVersion(1).version_id ? previewA.promise : previewB.promise);
    apiMocks.fetchDatasetProfile.mockImplementation((id: string) => id === workflowVersion(1).version_id ? profileA.promise : profileB.promise);

    let currentHref = "http://127.0.0.1/analysis/regression/regression.linear_model";
    const storage = new Map<string, string>();
    const windowStub = {
      get location() {
        const url = new URL(currentHref);
        return { href: currentHref, search: url.search };
      },
      history: {
        replaceState: (_state: unknown, _title: string, nextUrl: string) => {
          currentHref = new URL(nextUrl, currentHref).href;
        },
      },
      sessionStorage: {
        getItem: (key: string) => storage.get(key) ?? null,
        removeItem: (key: string) => storage.delete(key),
        setItem: (key: string, value: string) => storage.set(key, value),
      },
    } as unknown as Window & typeof globalThis;
    Object.defineProperty(globalThis, "window", { configurable: true, value: windowStub });

    const callbacks = {
      onDatasetColumnsChanged: vi.fn(),
      onDatasetReset: vi.fn(),
      onSchemaChanged: vi.fn(),
    };
    const runner = new HookRunner<
      Parameters<typeof useDatasetWorkflow>[0],
      ReturnType<typeof useDatasetWorkflow>
    >(useDatasetWorkflow, callbacks);
    const idA = "00000000-0000-4000-8000-000000000001";
    const idB = "00000000-0000-4000-8000-000000000002";
    await runner.act(() => runner.output.activeDatasetSelectorProps.onSelect(idA));
    await runner.act(() => runner.output.activeDatasetSelectorProps.onSelect(idB));

    const columnsB = workflowVersion(2).columns;
    versionB.resolve(workflowVersion(2));
    previewB.resolve(workflowPreview(workflowVersion(2)));
    profileB.resolve(workflowProfile(workflowVersion(2)));
    await runner.flush();

    versionA.resolve(workflowVersion(1));
    previewA.resolve(workflowPreview(workflowVersion(1)));
    profileA.resolve(workflowProfile(workflowVersion(1)));
    await runner.flush();

    expect(runner.output.version?.version_id).toBe(idB);
    expect(runner.output.datasetPageProps.preview?.version_id).toBe(idB);
    expect(runner.output.profile?.version_id).toBe(idB);
    expect(storage.get("datalab.current_dataset_version_id")).toBe(idB);
    expect(new URL(currentHref).searchParams.get("dataset_version_id")).toBe(idB);
    expect(callbacks.onDatasetColumnsChanged).toHaveBeenLastCalledWith(columnsB);
    expect(callbacks.onDatasetReset).toHaveBeenCalledTimes(1);
    runner.unmount();
  });

  it("keeps the latest Phase II limit-set catalog when the target changes", async () => {
    const first = deferred<AttributeControlLimitSetListResponse>();
    const second = deferred<AttributeControlLimitSetListResponse>();
    apiMocks.fetchAttributeControlLimitSets
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const initialProps = {
      chartType: "p" as const,
      constantOpportunityConfirmed: false,
      countColumnId: "count-a",
      denominatorColumnId: "denominator-a",
      phase: "phase_2" as const,
      targetDatasetVersionId: "dataset-a",
    };
    const runner = new HookRunner(useAttributeControlPhase2State, initialProps);

    runner.update({ ...initialProps, targetDatasetVersionId: "dataset-b" });
    second.resolve({
      total: 1,
      offset: 0,
      limit: 100,
      items: [{ limit_set_id: "limit-b" } as AttributeControlLimitSetResponse],
    });
    await runner.flush();
    first.resolve({
      total: 1,
      offset: 0,
      limit: 100,
      items: [{ limit_set_id: "limit-a" } as AttributeControlLimitSetResponse],
    });
    await runner.flush();

    expect(apiMocks.fetchAttributeControlLimitSets).toHaveBeenCalledTimes(2);
    expect(runner.output.limitSets[0]?.limit_set_id).toBe("limit-b");
    expect(runner.output.isLoading).toBe(false);
    runner.unmount();
  });

  it("ignores old limit-set deletion state after the selection changes", async () => {
    const firstLimitSet = {
      limit_set_id: "limit-a",
    } as AttributeControlLimitSetResponse;
    const secondLimitSet = {
      limit_set_id: "limit-b",
    } as AttributeControlLimitSetResponse;
    apiMocks.fetchAttributeControlLimitSets.mockResolvedValue({
      total: 2,
      offset: 0,
      limit: 100,
      items: [firstLimitSet, secondLimitSet],
    });
    apiMocks.fetchAttributeControlMonitoringPreflight.mockResolvedValue({
      ready: true,
      issues: [],
    });
    const oldPreflight = deferred<AttributeControlLimitSetDeletionPreflightResponse>();
    apiMocks.fetchAttributeControlLimitSetDeletionPreflight.mockReturnValueOnce(
      oldPreflight.promise,
    );
    const runner = new HookRunner(useAttributeControlPhase2State, {
      chartType: "p" as const,
      constantOpportunityConfirmed: false,
      countColumnId: "count-a",
      denominatorColumnId: "denominator-a",
      phase: "phase_2" as const,
      targetDatasetVersionId: "dataset-a",
    });
    await runner.flush();
    await runner.act(() => runner.output.onSelectLimitSet("limit-a"));
    await runner.act(() => runner.output.onLoadDeletionPreflight());
    expect(runner.output.isLoadingDeletionPreflight).toBe(true);
    await runner.act(() => runner.output.onSelectLimitSet("limit-b"));
    oldPreflight.resolve({
      limit_set_id: "limit-a",
      deletion_ready: true,
    } as AttributeControlLimitSetDeletionPreflightResponse);
    await runner.flush();

    expect(runner.output.selectedLimitSetId).toBe("limit-b");
    expect(runner.output.deletionPreflight).toBeNull();
    expect(runner.output.isLoadingDeletionPreflight).toBe(false);
    runner.unmount();
  });

  it("ignores an old model deletion after the active model changes", async () => {
    apiMocks.fetchRegressionModelDeletionPreflight.mockResolvedValue({
      model_id: "model-a",
      deletion_ready: true,
      deletion_manifest_sha256: "a".repeat(64),
    });
    const deletion = deferred<RegressionModelDeleteResponse>();
    apiMocks.deleteRegressionModel.mockReturnValueOnce(deletion.promise);
    const runner = new HookRunner<
      Parameters<typeof useRegressionModelRetentionState>[0],
      ReturnType<typeof useRegressionModelRetentionState>
    >(useRegressionModelRetentionState, "model-a");
    await runner.act(() => runner.output.onLoadPreflight());
    await runner.act(() => runner.output.onDelete(runner.output.preflight!));
    expect(runner.output.isDeleting).toBe(true);
    runner.update("model-b");
    deletion.resolve({ model_id: "model-a" } as RegressionModelDeleteResponse);
    await runner.flush();

    expect(runner.output.deletedModelId).toBeNull();
    expect(runner.output.deletion).toBeNull();
    expect(runner.output.isDeleting).toBe(false);
    runner.unmount();
  });

  it("restores regression model availability from the checksum-validated asset", async () => {
    const runner = new HookRunner<
      Parameters<typeof useRegressionModelRetentionState>[0],
      ReturnType<typeof useRegressionModelRetentionState>
    >(useRegressionModelRetentionState, "model-a");
    await runner.flush();

    expect(apiMocks.fetchRegressionModelManifest).toHaveBeenCalledWith("model-a");
    expect(runner.output.availability).toBe("available");
    expect(runner.output.isCheckingAvailability).toBe(false);
    runner.unmount();
  });

  it("distinguishes an unavailable model from an integrity failure after restore", async () => {
    apiMocks.fetchRegressionModelManifest.mockRejectedValueOnce(
      new Error("regression_model_not_found"),
    );
    const missingRunner = new HookRunner<
      Parameters<typeof useRegressionModelRetentionState>[0],
      ReturnType<typeof useRegressionModelRetentionState>
    >(useRegressionModelRetentionState, "model-missing");
    await missingRunner.flush();
    expect(missingRunner.output.availability).toBe("unavailable_or_deleted");
    expect(missingRunner.output.availabilityError).toBe("regression_model_not_found");
    missingRunner.unmount();

    apiMocks.fetchRegressionModelManifest.mockRejectedValueOnce(
      new Error("regression_model_manifest_checksum_mismatch"),
    );
    const corruptRunner = new HookRunner<
      Parameters<typeof useRegressionModelRetentionState>[0],
      ReturnType<typeof useRegressionModelRetentionState>
    >(useRegressionModelRetentionState, "model-corrupt");
    await corruptRunner.flush();
    expect(corruptRunner.output.availability).toBe("integrity_error");
    expect(corruptRunner.output.availabilityError).toBe(
      "regression_model_manifest_checksum_mismatch",
    );
    corruptRunner.unmount();
  });

  it("notifies a mounted catalog when a stale model row resolves as deleted", async () => {
    apiMocks.fetchRegressionModelManifest.mockRejectedValueOnce(
      new Error("regression_model_not_found"),
    );
    const onStaleAsset = vi.fn();
    const useRetentionWithCatalogRecovery = (modelId: string | null) =>
      useRegressionModelRetentionState(modelId, onStaleAsset);
    const runner = new HookRunner<
      string | null,
      ReturnType<typeof useRegressionModelRetentionState>
    >(useRetentionWithCatalogRecovery, "model-stale");
    await runner.flush();

    expect(onStaleAsset).toHaveBeenCalledTimes(1);
    expect(runner.output.availability).toBe("unavailable_or_deleted");
    runner.unmount();
  });

  it("keeps transient model availability errors visible and retries explicitly", async () => {
    apiMocks.fetchRegressionModelManifest
      .mockRejectedValueOnce(new Error("api_unreachable"))
      .mockResolvedValueOnce({});
    const runner = new HookRunner<
      Parameters<typeof useRegressionModelRetentionState>[0],
      ReturnType<typeof useRegressionModelRetentionState>
    >(useRegressionModelRetentionState, "model-transient");
    await runner.flush();

    expect(runner.output.availability).toBeNull();
    expect(runner.output.availabilityError).toBe("api_unreachable");
    expect(runner.output.isCheckingAvailability).toBe(false);

    await runner.act(() => runner.output.onRetryAvailability());

    expect(apiMocks.fetchRegressionModelManifest).toHaveBeenCalledTimes(2);
    expect(runner.output.availability).toBe("available");
    expect(runner.output.availabilityError).toBeNull();
    runner.unmount();
  });

  it("disables the current model immediately after successful asset deletion", async () => {
    apiMocks.fetchRegressionModelDeletionPreflight.mockResolvedValue({
      model_id: "model-a",
      deletion_ready: true,
      deletion_manifest_sha256: "a".repeat(64),
    });
    apiMocks.deleteRegressionModel.mockResolvedValue({
      model_id: "model-a",
    });
    const runner = new HookRunner<
      Parameters<typeof useRegressionModelRetentionState>[0],
      ReturnType<typeof useRegressionModelRetentionState>
    >(useRegressionModelRetentionState, "model-a");
    await runner.flush();
    await runner.act(() => runner.output.onLoadPreflight());
    await runner.act(() => runner.output.onDelete(runner.output.preflight!));

    expect(runner.output.deletedModelId).toBe("model-a");
    expect(runner.output.availability).toBe("unavailable_or_deleted");
    expect(runner.output.availabilityError).toBe("regression_model_not_found");
    runner.unmount();
  });

  it("binds an explicit model cascade to the cascade manifest", async () => {
    const preflight = {
      model_id: "model-a",
      deletion_ready: false,
      cascade_deletion_ready: true,
      deletion_manifest_sha256: "a".repeat(64),
      cascade_deletion_manifest_sha256: "b".repeat(64),
    } as RegressionModelDeletionPreflightResponse;
    apiMocks.fetchRegressionModelDeletionPreflight.mockResolvedValue(preflight);
    apiMocks.deleteRegressionModel.mockResolvedValue({
      model_id: "model-a",
      deletion_mode: "model_and_predictions",
    });
    const runner = new HookRunner<
      Parameters<typeof useRegressionModelRetentionState>[0],
      ReturnType<typeof useRegressionModelRetentionState>
    >(useRegressionModelRetentionState, "model-a");
    await runner.flush();
    await runner.act(() => runner.output.onLoadPreflight());
    await runner.act(() =>
      runner.output.onDelete(runner.output.preflight!, "model_and_predictions"),
    );

    expect(apiMocks.deleteRegressionModel).toHaveBeenCalledWith("model-a", {
      confirmation_model_id: "model-a",
      expected_deletion_manifest_sha256: "b".repeat(64),
      mode: "model_and_predictions",
    });
    runner.unmount();
  });

  it("keeps dataset B history when dataset A resolves late", async () => {
    const first = deferred<AnalysisRunListResponse>();
    const second = deferred<AnalysisRunListResponse>();
    apiMocks.fetchAnalysisRuns.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const runner = new HookRunner(useAnalysisHistoryState, {
      currentDatasetVersionId: "dataset-a",
      refreshKey: null,
      resetKey: 0,
    });

    runner.update({ currentDatasetVersionId: "dataset-b", refreshKey: null, resetKey: 0 });
    second.resolve(historyResponse("dataset-b"));
    await runner.flush();
    first.resolve(historyResponse("dataset-a"));
    await runner.flush();

    expect(runner.output.analysisHistory?.dataset_version_id).toBe("dataset-b");
    expect(runner.output.isLoadingAnalysisHistory).toBe(false);
    runner.unmount();
  });

  it("does not request full analysis history until the Report Center enables it", async () => {
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    const runner = new HookRunner(useAnalysisHistoryState, {
      currentDatasetVersionId: "dataset-a",
      enabled: false,
      refreshKey: null,
      resetKey: 0,
    });
    await runner.flush();

    expect(apiMocks.fetchAnalysisRuns).not.toHaveBeenCalled();
    expect(runner.output.analysisHistory).toBeNull();

    runner.update({
      currentDatasetVersionId: "dataset-a",
      enabled: true,
      refreshKey: null,
      resetKey: 0,
    });
    await runner.flush();

    expect(apiMocks.fetchAnalysisRuns).toHaveBeenCalledOnce();
    expect(runner.output.analysisHistory?.dataset_version_id).toBe("dataset-a");
    runner.unmount();
  });

  it("keeps Report Center detail independent of list filter changes", async () => {
    const browser = reportWindow(`&analysis_id=${reportIdA}`);
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockResolvedValueOnce(reportResult(reportIdA));
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.flush();
    const pending = deferred<AnalysisResultEnvelope>();
    apiMocks.fetchAnalysisRunResult.mockReturnValueOnce(pending.promise);
    await runner.act(() => runner.output.onSelectAnalysis(reportIdB));
    expect(new URL(browser.location.href).searchParams.get("analysis_id")).toBe(reportIdB);
    await runner.act(() => runner.output.onChangeMethodId("regression.pls"));
    expect(apiMocks.fetchAnalysisRunResult).toHaveBeenCalledTimes(2);
    expect(runner.output.selectedAnalysisId).toBe(reportIdB);
    expect(runner.output.isLoadingResult).toBe(true);
    pending.resolve(reportResult(reportIdB));
    await runner.flush();
    expect(runner.output.selectedResult?.analysis_id).toBe(reportIdB);
    runner.unmount();
  });

  it("blocks a dataset-only Report Center list when the dataset is cleared", async () => {
    reportWindow();
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockResolvedValue(reportResult(reportIdA));
    const runner = new HookRunner<string | null, ReturnType<typeof useReportCenterState>>(useReportCenterState, "dataset-a");
    await runner.act(() => runner.output.onChangeCurrentDatasetOnly(true));
    await runner.act(() => runner.output.onSelectAnalysis(reportIdA));
    apiMocks.fetchAnalysisRuns.mockClear();
    runner.update(null);
    await runner.flush();
    expect(apiMocks.fetchAnalysisRuns).not.toHaveBeenCalled();
    expect(runner.output.list).toBeNull();
    expect(runner.output.currentDatasetOnly).toBe(true);
    expect(runner.output.selectedResult?.analysis_id).toBe(reportIdA);
    runner.unmount();
  });

  it("does not refetch Report Center when an unused current dataset changes", async () => {
    reportWindow();
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    const runner = new HookRunner<string, ReturnType<typeof useReportCenterState>>(useReportCenterState, "dataset-a");
    await runner.flush();
    runner.update("dataset-b");
    await runner.flush();
    expect(apiMocks.fetchAnalysisRuns).toHaveBeenCalledOnce();
    runner.unmount();
  });

  it.each(["", "not-a-uuid", `${reportIdA}&analysis_id=${reportIdB}`])(
    "rejects invalid or ambiguous Report Center query %s without HTTP", async (id) => {
      reportWindow(`&analysis_id=${id}`);
      apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
      const runner = new HookRunner(useReportCenterState, "dataset-a");
      await runner.flush();
      expect(apiMocks.fetchAnalysisRunResult).not.toHaveBeenCalled();
      expect(runner.output.selectedAnalysisId).toBeNull();
      expect(runner.output.selectedResultError).toBe("report_center_analysis_id_invalid");
      runner.unmount();
    },
  );

  it("observes Report Center popstate without accepting mismatched response owners", async () => {
    const browser = reportWindow(`&analysis_id=${reportIdA}`);
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockResolvedValue(reportResult(reportIdA));
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.flush();
    browser.location.href = `http://127.0.0.1:8600/reports?analysis_id=${reportIdB}`;
    await runner.act(() => browser.events.dispatchEvent(new Event("popstate")));
    expect(apiMocks.fetchAnalysisRunResult).toHaveBeenLastCalledWith(reportIdB);
    expect(runner.output.selectedResult).toBeNull();
    expect(runner.output.selectedResultError).toBe("report_center_result_identity_mismatch");
    runner.unmount();
  });

  it("does not publish an analysis deletion after its view unmounts", async () => {
    const pending = deferred<AnalysisRunDeleteResponse>();
    apiMocks.deleteStoredAnalysisRun.mockReturnValueOnce(pending.promise);
    const onDeleted = vi.fn();
    const runner = new HookRunner(
      (id: string) => useAnalysisRunDeletionState(id, onDeleted), reportIdA,
    );
    await runner.act(() => runner.output.onDelete(analysisDeletionPreflight(reportIdA)));
    runner.unmount();
    pending.resolve({ analysis_id: reportIdA } as AnalysisRunDeleteResponse);
    await runner.flush();
    expect(onDeleted).not.toHaveBeenCalled();
  });

  it("restores a Report Center result from the analysis_id query", async () => {
    const browser = reportWindow(`&analysis_id=${reportIdA}`);
    const result = reportResult(reportIdA);
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockResolvedValue(result);
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.flush();

    expect(apiMocks.fetchAnalysisRunResult).toHaveBeenCalledWith(reportIdA);
    expect(runner.output.selectedAnalysisId).toBe(reportIdA);
    expect(runner.output.selectedResult).toEqual(result);
    expect(browser.history.replaceState).not.toHaveBeenCalled();
    runner.unmount();
  });

  it.each(["resolve", "reject"] as const)("ignores late Report Center list %s and finally", async (outcome) => {
    reportWindow();
    const old = deferred<AnalysisRunListResponse>();
    const latest = deferred<AnalysisRunListResponse>();
    apiMocks.fetchAnalysisRuns.mockReturnValueOnce(old.promise).mockReturnValueOnce(latest.promise);
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.act(() => runner.output.onChangeMethodId("regression.pls"));
    if (outcome === "resolve") old.resolve(historyResponse("obsolete"));
    else old.reject(new Error("obsolete_failed"));
    await runner.flush();
    expect(runner.output.isLoadingList).toBe(true);
    expect(runner.output.listError).toBeNull();
    expect(runner.output.list).toBeNull();
    latest.resolve(historyResponse("current"));
    await runner.flush();
    expect(runner.output.list?.dataset_version_id).toBe("current");
    runner.unmount();
  });

  it.each(["resolve", "reject"] as const)("ignores late Report Center detail %s and finally", async (outcome) => {
    const browser = reportWindow();
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    const old = deferred<AnalysisResultEnvelope>();
    const latest = deferred<AnalysisResultEnvelope>();
    apiMocks.fetchAnalysisRunResult.mockReturnValueOnce(old.promise).mockReturnValueOnce(latest.promise);
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.act(() => runner.output.onSelectAnalysis(reportIdA));
    await runner.act(() => runner.output.onSelectAnalysis(reportIdB));
    if (outcome === "resolve") old.resolve(reportResult(reportIdA));
    else old.reject(new Error("analysis_run_not_found"));
    await runner.flush();
    expect(runner.output.isLoadingResult).toBe(true);
    expect(runner.output.selectedResultError).toBeNull();
    expect(runner.output.selectedAnalysisId).toBe(reportIdB);
    expect(new URL(browser.location.href).searchParams.get("analysis_id")).toBe(reportIdB);
    latest.resolve(reportResult(reportIdB));
    await runner.flush();
    expect(runner.output.selectedResult?.analysis_id).toBe(reportIdB);
    expect(browser.location.href).toContain("#saved");
    expect(browser.history.replaceState).toHaveBeenLastCalledWith(
      browser.history.state, "", `/reports?tab=reports&analysis_id=${reportIdB}#saved`,
    );
    runner.unmount();
  });

  it("retries Report Center detail independently and keeps transient-failure URL", async () => {
    const browser = reportWindow(`&analysis_id=${reportIdA}`);
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockRejectedValueOnce(new Error("api_unreachable"));
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.flush();
    expect(runner.output.selectedAnalysisId).toBe(reportIdA);
    expect(runner.output.selectedResultError).toBe("api_unreachable");
    expect(browser.history.replaceState).not.toHaveBeenCalled();
    apiMocks.fetchAnalysisRunResult.mockResolvedValueOnce(reportResult(reportIdA));
    await runner.act(() => runner.output.onRetrySelectedResult());
    expect(apiMocks.fetchAnalysisRuns).toHaveBeenCalledOnce();
    expect(runner.output.selectedResult?.analysis_id).toBe(reportIdA);
    runner.unmount();
  });

  it("resets Report Center pagination on dataset scope changes, never broadening null", async () => {
    reportWindow();
    apiMocks.fetchAnalysisRuns.mockImplementation((query: AnalysisRunsRouteParams) => Promise.resolve({
      ...historyResponse(query.datasetVersionId ?? "all"), offset: query.offset, returned_count: 1,
    }));
    const runner = new HookRunner<string | null, ReturnType<typeof useReportCenterState>>(useReportCenterState, "dataset-a");
    await runner.act(() => runner.output.onChangeCurrentDatasetOnly(true));
    await runner.act(() => runner.output.onChangeOffset(20));
    expect(runner.output.offset).toBe(20);
    apiMocks.fetchAnalysisRuns.mockClear();
    runner.update(null);
    await runner.flush();
    expect(runner.output.listBlocked).toBe(true);
    expect(apiMocks.fetchAnalysisRuns).not.toHaveBeenCalled();
    runner.update("dataset-b");
    await runner.flush();
    expect(apiMocks.fetchAnalysisRuns).toHaveBeenCalledOnce();
    expect(apiMocks.fetchAnalysisRuns).toHaveBeenLastCalledWith(expect.objectContaining({
      datasetVersionId: "dataset-b", offset: 0,
    }));
    runner.update(null);
    await runner.flush();
    await runner.act(() => runner.output.onChangeCurrentDatasetOnly(false));
    expect(runner.output.listBlocked).toBe(false);
    expect(apiMocks.fetchAnalysisRuns).toHaveBeenLastCalledWith(expect.objectContaining({
      datasetVersionId: null, offset: 0,
    }));
    runner.unmount();
  });

  it("keeps Report Center B selected when deletion of A completes", async () => {
    const browser = reportWindow(`&analysis_id=${reportIdB}`);
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockResolvedValue(reportResult(reportIdB));
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.flush();
    await runner.act(() => runner.output.onSelectedAnalysisDeleted(reportIdA));
    expect(runner.output.selectedResult?.analysis_id).toBe(reportIdB);
    expect(browser.history.replaceState).not.toHaveBeenCalled();
    expect(apiMocks.fetchAnalysisRunResult).toHaveBeenCalledOnce();
    expect(apiMocks.fetchAnalysisRuns).toHaveBeenCalledTimes(2);
    runner.unmount();
  });

  it.each([true, false])("backs out of a deleted last Report Center page without refetching detail (selected owner deleted: %s)", async (selectedDeleted) => {
    const selectedId = selectedDeleted ? reportIdA : reportIdB;
    const browser = reportWindow(`&analysis_id=${selectedId}`);
    const item = {
      analysis_id: reportIdA, method_id: "eda.descriptive", method_version: "0.1.0",
      dataset_version_id: "dataset-a", status: "succeeded" as const, stale: false,
      result_available: true, artifact_count: 1, failure_code: null,
      created_at: "2026-10-18T00:00:00Z", updated_at: "2026-10-18T00:00:00Z",
      completed_at: "2026-10-18T00:00:00Z",
    };
    let deleted = false;
    apiMocks.fetchAnalysisRuns.mockImplementation((query: AnalysisRunsRouteParams) => {
      const runs = query.offset === 20 && deleted ? [] : [{ ...item, analysis_id: query.offset === 20 ? reportIdA : reportIdB }];
      return Promise.resolve({ ...historyResponse("dataset-a"), offset: query.offset,
        returned_count: runs.length, runs, has_more: query.offset === 0 && !deleted });
    });
    apiMocks.fetchAnalysisRunResult.mockResolvedValue(reportResult(selectedId));
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.flush();
    await runner.act(() => runner.output.onChangeOffset(20));
    expect(runner.output.offset).toBe(20);
    apiMocks.fetchAnalysisRuns.mockClear();
    deleted = true;
    await runner.act(() => runner.output.onSelectedAnalysisDeleted(reportIdA));
    expect(apiMocks.fetchAnalysisRuns.mock.calls.map(([query]) => query.offset)).toEqual([20, 0]);
    expect(runner.output.offset).toBe(0);
    expect(runner.output.list?.runs.map((row) => row.analysis_id)).toEqual([reportIdB]);
    expect(runner.output.selectedAnalysisId).toBe(selectedDeleted ? null : reportIdB);
    expect(runner.output.selectedResult?.analysis_id ?? null).toBe(selectedDeleted ? null : reportIdB);
    expect(apiMocks.fetchAnalysisRunResult).toHaveBeenCalledOnce();
    expect(new URL(browser.location.href).searchParams.get("analysis_id")).toBe(selectedDeleted ? null : reportIdB);
    expect(browser.location.href).toContain("tab=reports");
    expect(browser.location.href).toContain("#saved");
    runner.unmount();
  });

  it("preserves independently loaded stale Report Center status across list filters", async () => {
    reportWindow(`&analysis_id=${reportIdA}`);
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockResolvedValue(reportResult(reportIdA));
    apiMocks.fetchAnalysisRunStatus.mockResolvedValue({ analysis_id: reportIdA, stale: true });
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.flush();
    await runner.act(() => runner.output.onChangeStaleFilter("fresh"));
    expect(runner.output.selectedStatus?.stale).toBe(true);
    expect(runner.output.selectedResult?.analysis_id).toBe(reportIdA);
    expect(apiMocks.fetchAnalysisRunStatus).toHaveBeenCalledOnce();
    expect(apiMocks.fetchAnalysisRunResult).toHaveBeenCalledOnce();
    runner.unmount();
  });

  it("guards Report Center status independently and retries without rereading result", async () => {
    reportWindow();
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockImplementation((id: string) => Promise.resolve(reportResult(id)));
    const old = deferred<AnalysisRunStatusResponse>();
    apiMocks.fetchAnalysisRunStatus.mockReturnValueOnce(old.promise)
      .mockRejectedValueOnce(new Error("api_unreachable"));
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.act(() => runner.output.onSelectAnalysis(reportIdA));
    await runner.act(() => runner.output.onSelectAnalysis(reportIdB));
    old.resolve({ analysis_id: reportIdA, stale: false } as AnalysisRunStatusResponse);
    await runner.flush();
    expect(runner.output.selectedStatus).toBeNull();
    expect(runner.output.selectedStatusError).toBe("api_unreachable");
    expect(runner.output.selectedResult?.analysis_id).toBe(reportIdB);
    apiMocks.fetchAnalysisRunStatus.mockResolvedValueOnce({ analysis_id: reportIdB, stale: true });
    await runner.act(() => runner.output.onRetrySelectedStatus());
    expect(runner.output.selectedStatus?.stale).toBe(true);
    expect(apiMocks.fetchAnalysisRunResult).toHaveBeenCalledTimes(2);
    runner.unmount();
  });

  it("clears Report Center selection on invalid and removed same-mount URL, including held replies", async () => {
    const browser = reportWindow(`&analysis_id=${reportIdA}`);
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    const pending = deferred<AnalysisResultEnvelope>();
    apiMocks.fetchAnalysisRunResult.mockReturnValueOnce(pending.promise);
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    await runner.flush();
    browser.location.href = "http://127.0.0.1:8600/reports?analysis_id=invalid";
    await runner.act(() => browser.events.dispatchEvent(new Event("datalab:location-change")));
    pending.resolve(reportResult(reportIdA));
    await runner.flush();
    expect(runner.output.selectedResult).toBeNull();
    expect(runner.output.selectedAnalysisId).toBeNull();
    expect(runner.output.selectedResultError).toBe("report_center_analysis_id_invalid");
    expect(apiMocks.fetchAnalysisRunResult).toHaveBeenCalledOnce();
    browser.location.href = "http://127.0.0.1:8600/reports?tab=reports#saved";
    await runner.act(() => browser.events.dispatchEvent(new Event("popstate")));
    expect(runner.output.selectedResultError).toBeNull();
    expect(browser.history.replaceState).not.toHaveBeenCalled();
    runner.unmount();
  });

  it("does not apply Report Center replies or callbacks after unmount", async () => {
    const browser = reportWindow(`&analysis_id=${reportIdA}`);
    const pending = deferred<AnalysisResultEnvelope>();
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockReturnValueOnce(pending.promise);
    const runner = new HookRunner(useReportCenterState, "dataset-a");
    runner.unmount();
    pending.reject(new Error("analysis_run_not_found"));
    await runner.flush();
    runner.output.onSelectedAnalysisDeleted(reportIdA);
    expect(browser.history.replaceState).not.toHaveBeenCalled();
    expect(apiMocks.fetchAnalysisRuns).toHaveBeenCalledOnce();
  });

  it("clears a selected Report Center result after mutation revalidation returns not found", async () => {
    const browser = reportWindow(`&analysis_id=${reportIdA}`);
    const result = reportResult(reportIdA);
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunResult.mockResolvedValueOnce(result);
    const runner = new HookRunner(
      (props: { datasetVersionId: string; revision: number }) =>
        useReportCenterState(props.datasetVersionId, props.revision),
      { datasetVersionId: "dataset-a", revision: 0 },
    );
    await runner.flush();
    expect(runner.output.selectedAnalysisId).toBe(reportIdA);

    apiMocks.fetchAnalysisRunResult.mockRejectedValueOnce(
      new Error("analysis_run_not_found"),
    );
    runner.update({ datasetVersionId: "dataset-a", revision: 1 });
    await runner.flush();

    expect(runner.output.selectedAnalysisId).toBeNull();
    expect(runner.output.selectedResult).toBeNull();
    expect(runner.output.notice).toBe("report_center_result_removed");
    expect(browser.history.replaceState).toHaveBeenLastCalledWith(
      browser.history.state,
      "",
      "/reports?tab=reports#saved",
    );
    runner.unmount();
  });

  it("deletes a selected analysis through the reusable deletion state", async () => {
    const preflight = analysisDeletionPreflight("analysis-a");
    const response = {
      analysis_id: "analysis-a",
      cleanup_status: "deleted",
    } as AnalysisRunDeleteResponse;
    apiMocks.fetchAnalysisRunDeletionPreflight.mockResolvedValue(preflight);
    apiMocks.deleteStoredAnalysisRun.mockResolvedValue(response);
    const onDeleted = vi.fn();
    const runner = new HookRunner(
      (analysisId: string | null) =>
        useAnalysisRunDeletionState(analysisId, onDeleted),
      "analysis-a",
    );
    await runner.act(() => runner.output.onLoadPreflight());
    await runner.act(() => runner.output.onDelete(runner.output.preflight!));

    expect(apiMocks.deleteStoredAnalysisRun).toHaveBeenCalledWith("analysis-a", {
      confirmation_analysis_id: "analysis-a",
      expected_deletion_manifest_sha256:
        preflight.deletion_manifest_sha256,
    });
    expect(onDeleted).toHaveBeenCalledWith(response);
    runner.unmount();
  });

  it("keeps analysis deletion reset after old preflight and delete responses", async () => {
    apiMocks.fetchAnalysisRuns.mockResolvedValue(historyResponse("dataset-a"));
    const preflight = deferred<AnalysisRunDeletionPreflightResponse>();
    apiMocks.fetchAnalysisRunDeletionPreflight.mockReturnValueOnce(preflight.promise);
    const initialProps = {
      currentDatasetVersionId: "dataset-a",
      refreshKey: null,
      resetKey: 0,
    };
    const runner = new HookRunner(useAnalysisHistoryState, initialProps);

    await runner.act(() => runner.output.onLoadAnalysisRunDeletionPreflight("analysis-a"));
    expect(runner.output.isLoadingAnalysisRunDeletionPreflight).toBe(true);
    runner.update({ ...initialProps, currentDatasetVersionId: "dataset-b" });
    preflight.resolve(analysisDeletionPreflight("analysis-a"));
    await runner.flush();

    expect(runner.output.analysisRunDeletionPreflight).toBeNull();
    expect(runner.output.isLoadingAnalysisRunDeletionPreflight).toBe(false);

    runner.update({ ...initialProps, resetKey: 1 });
    await runner.flush();
    apiMocks.fetchAnalysisRunDeletionPreflight.mockResolvedValueOnce(
      analysisDeletionPreflight("analysis-a"),
    );
    await runner.act(() => runner.output.onLoadAnalysisRunDeletionPreflight("analysis-a"));
    const deletion = deferred<AnalysisRunDeleteResponse>();
    apiMocks.deleteStoredAnalysisRun.mockReturnValueOnce(deletion.promise);
    await runner.act(() =>
      runner.output.onDeleteAnalysisRun(analysisDeletionPreflight("analysis-a")),
    );
    expect(runner.output.isDeletingAnalysisRun).toBe(true);
    runner.update({ ...initialProps, currentDatasetVersionId: "dataset-b", resetKey: 2 });
    deletion.resolve({
      deletion_schema_version: 1,
      analysis_id: "analysis-a",
      deletion_manifest_sha256: "c".repeat(64),
      deleted_at: "2026-07-17T00:00:00Z",
      deleted_counts: analysisDeletionPreflight("analysis-a").counts,
      cleanup_status: "deleted",
    });
    await runner.flush();

    expect(runner.output.analysisRunDeletion).toBeNull();
    expect(runner.output.analysisRunDeletionPreflight).toBeNull();
    expect(runner.output.isDeletingAnalysisRun).toBe(false);
    runner.unmount();
  });

  it("refreshes history after the current analysis run is deleted", async () => {
    apiMocks.fetchAnalysisRuns
      .mockResolvedValueOnce(historyResponse("dataset-a"))
      .mockResolvedValueOnce(historyResponse("dataset-a"));
    apiMocks.fetchAnalysisRunDeletionPreflight.mockResolvedValueOnce(
      analysisDeletionPreflight("analysis-a"),
    );
    apiMocks.deleteStoredAnalysisRun.mockResolvedValueOnce({
      deletion_schema_version: 1,
      analysis_id: "analysis-a",
      deletion_manifest_sha256: "c".repeat(64),
      deleted_at: "2026-07-17T00:00:00Z",
      deleted_counts: analysisDeletionPreflight("analysis-a").counts,
      cleanup_status: "deleted",
    });
    const runner = new HookRunner(useAnalysisHistoryState, {
      currentDatasetVersionId: "dataset-a",
      refreshKey: null,
      resetKey: 0,
    });
    await runner.flush();
    await runner.act(() => runner.output.onLoadAnalysisRunDeletionPreflight("analysis-a"));
    await runner.act(() =>
      runner.output.onDeleteAnalysisRun(analysisDeletionPreflight("analysis-a")),
    );

    expect(apiMocks.deleteStoredAnalysisRun).toHaveBeenCalledWith("analysis-a", {
      confirmation_analysis_id: "analysis-a",
      expected_deletion_manifest_sha256: "c".repeat(64),
    });
    expect(apiMocks.fetchAnalysisRuns).toHaveBeenCalledTimes(2);
    expect(runner.output.analysisRunDeletion?.analysis_id).toBe("analysis-a");
    expect(runner.output.isDeletingAnalysisRun).toBe(false);
    runner.unmount();
  });

  it("keeps analysis B export list when analysis A resolves late", async () => {
    const first = deferred<AnalysisResultExportListResponse>();
    const second = deferred<AnalysisResultExportListResponse>();
    apiMocks.fetchAnalysisResultExports
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const runner = new HookRunner(useAnalysisExportState, {
      currentAnalysisId: "analysis-a",
      currentDatasetVersionId: "dataset-a",
      resetKey: 0,
    });

    runner.update({
      currentAnalysisId: "analysis-b",
      currentDatasetVersionId: "dataset-a",
      resetKey: 0,
    });
    second.resolve(exportListResponse("analysis-b"));
    await runner.flush();
    first.resolve(exportListResponse("analysis-a"));
    await runner.flush();

    expect(runner.output.analysisResultExportList?.analysis_id).toBe("analysis-b");
    expect(runner.output.isLoadingAnalysisResultExportList).toBe(false);
    runner.unmount();
  });

  it("binds HTML creation to the restored owner, explicit locale and capability hash", async () => {
    apiMocks.fetchAnalysisResultExports.mockImplementation((id: string) => Promise.resolve(exportListResponse(id)));
    apiMocks.fetchAnalysisReportCapability.mockImplementation((id: string, locale: "en" | "ko") => Promise.resolve(reportCapability(id, locale)));
    apiMocks.createAnalysisResultHtmlReport.mockResolvedValue({ analysis_id: "restored-b", report_locale: "en", source_result_sha256: "a".repeat(64) });
    const runner = new HookRunner(useAnalysisExportState, {
      currentAnalysisId: null, currentDatasetVersionId: "dataset-a", resetKey: 0, locale: "en" as const,
    });
    await runner.act(() => { void runner.output.onRefreshAnalysisResultExports("restored-b"); });
    expect(runner.output.analysisReportCapability?.analysis_id).toBe("restored-b");
    await runner.act(() => runner.output.onCreateAnalysisResultHtmlReport("restored-b"));
    expect(apiMocks.createAnalysisResultHtmlReport).toHaveBeenCalledWith("restored-b", {
      locale: "en", expected_source_result_sha256: "a".repeat(64),
    });
    expect(runner.output.analysisResultHtmlReport?.analysis_id).toBe("restored-b");
    runner.unmount();
  });

  it("does not create HTML when capability is unknown or unsupported", async () => {
    const pending = deferred<AnalysisReportCapability>();
    apiMocks.fetchAnalysisReportCapability.mockReturnValue(pending.promise);
    apiMocks.fetchAnalysisResultExports.mockResolvedValue(exportListResponse("analysis-a"));
    const runner = new HookRunner(useAnalysisExportState, {
      currentAnalysisId: "analysis-a", currentDatasetVersionId: "dataset-a", resetKey: 0,
    });
    await runner.act(() => runner.output.onCreateAnalysisResultHtmlReport("analysis-a"));
    expect(apiMocks.createAnalysisResultHtmlReport).not.toHaveBeenCalled();
    pending.resolve({ ...reportCapability("analysis-a", "en"), report_level: "unsupported", html_available: false });
    await runner.flush();
    await runner.act(() => runner.output.onCreateAnalysisResultHtmlReport("analysis-a"));
    expect(apiMocks.createAnalysisResultHtmlReport).not.toHaveBeenCalled();
    runner.unmount();
  });

  it("ignores late capability success and HTML completion after a locale or mutation change", async () => {
    const oldCapability = deferred<AnalysisReportCapability>();
    const oldHtml = deferred<unknown>();
    apiMocks.fetchAnalysisResultExports.mockResolvedValue(exportListResponse("analysis-a"));
    apiMocks.fetchAnalysisReportCapability.mockReturnValueOnce(oldCapability.promise)
      .mockResolvedValueOnce(reportCapability("analysis-a", "ko"))
      .mockResolvedValueOnce(reportCapability("analysis-a", "ko", "b"));
    const initial: Parameters<typeof useAnalysisExportState>[0] = {
      currentAnalysisId: "analysis-a", currentDatasetVersionId: "dataset-a", resetKey: 0, locale: "en", workspaceRevision: 0,
    };
    const runner = new HookRunner(useAnalysisExportState, initial);
    runner.update({ ...initial, locale: "ko" });
    await runner.flush();
    oldCapability.resolve(reportCapability("analysis-a", "en"));
    await runner.flush();
    expect(runner.output.analysisReportCapability?.locale).toBe("ko");
    apiMocks.createAnalysisResultHtmlReport.mockReturnValue(oldHtml.promise);
    await runner.act(() => runner.output.onCreateAnalysisResultHtmlReport("analysis-a"));
    runner.update({ ...initial, locale: "ko", workspaceRevision: 1 });
    await runner.flush();
    oldHtml.resolve({ analysis_id: "analysis-a", report_locale: "ko", source_result_sha256: "a".repeat(64) });
    await runner.flush();
    expect(runner.output.analysisResultHtmlReport).toBeNull();
    expect(runner.output.analysisReportCapability?.source_result_sha256).toBe("b".repeat(64));
    expect(runner.output.isCreatingAnalysisResultHtmlReport).toBe(false);
    runner.unmount();
  });

  it("keeps restored owner B coverage when A fails late and retries coverage without reloading exports", async () => {
    const old = deferred<AnalysisReportCapability>();
    apiMocks.fetchAnalysisResultExports.mockImplementation((id: string) => Promise.resolve(exportListResponse(id)));
    apiMocks.fetchAnalysisReportCapability.mockReturnValueOnce(old.promise)
      .mockRejectedValueOnce(new Error("api_unreachable"))
      .mockResolvedValueOnce(reportCapability("analysis-b", "en"));
    const runner = new HookRunner(useAnalysisExportState, {
      currentAnalysisId: "analysis-a", currentDatasetVersionId: "dataset-a", resetKey: 0, locale: "en" as const,
    });
    await runner.act(() => { void runner.output.onRefreshAnalysisResultExports("analysis-b"); });
    expect(runner.output.analysisReportCapabilityError).toBe("api_unreachable");
    old.reject(new Error("private raw failure"));
    await runner.flush();
    expect(runner.output.analysisReportCapabilityError).toBe("api_unreachable");
    const count = apiMocks.fetchAnalysisResultExports.mock.calls.length;
    await runner.act(() => runner.output.onRefreshAnalysisReportCapability());
    expect(runner.output.analysisReportCapability?.analysis_id).toBe("analysis-b");
    expect(apiMocks.fetchAnalysisResultExports).toHaveBeenCalledTimes(count);
    runner.unmount();
  });

  it("rejects mismatched capability and never publishes a report with another source hash", async () => {
    apiMocks.fetchAnalysisResultExports.mockResolvedValue(exportListResponse("analysis-a"));
    apiMocks.fetchAnalysisReportCapability.mockResolvedValueOnce(reportCapability("analysis-b", "en"))
      .mockResolvedValueOnce(reportCapability("analysis-a", "en"));
    const runner = new HookRunner(useAnalysisExportState, {
      currentAnalysisId: "analysis-a", currentDatasetVersionId: "dataset-a", resetKey: 0, locale: "en" as const,
    });
    await runner.flush();
    expect(runner.output.analysisReportCapability).toBeNull();
    expect(runner.output.analysisReportCapabilityError).toBe("analysis_report_capability_invalid");
    await runner.act(() => runner.output.onRefreshAnalysisReportCapability());
    apiMocks.createAnalysisResultHtmlReport.mockResolvedValue({ analysis_id: "analysis-a", report_locale: "en", source_result_sha256: "b".repeat(64) });
    await runner.act(() => runner.output.onCreateAnalysisResultHtmlReport("analysis-a"));
    expect(runner.output.analysisResultHtmlReport).toBeNull();
    expect(runner.output.analysisResultHtmlReportError).toBe("analysis_report_source_mismatch");
    runner.unmount();
  });

  it("invalidates in-flight capability on unmount without exposing exception text", async () => {
    const pending = deferred<AnalysisReportCapability>();
    apiMocks.fetchAnalysisResultExports.mockResolvedValue(exportListResponse("analysis-a"));
    apiMocks.fetchAnalysisReportCapability.mockReturnValue(pending.promise);
    const runner = new HookRunner(useAnalysisExportState, {
      currentAnalysisId: "analysis-a", currentDatasetVersionId: "dataset-a", resetKey: 0,
    });
    runner.unmount();
    pending.reject(new Error("private exception detail"));
    await runner.flush();
    expect(runner.output.analysisReportCapability).toBeNull();
    expect(runner.output.analysisReportCapabilityError).toBeNull();
  });

  it("keeps export deletion reset state after old preflight and delete responses", async () => {
    const preflight = deferred<AnalysisResultExportDeletionPreflightResponse>();
    apiMocks.fetchAnalysisResultExports.mockResolvedValue(exportListResponse("analysis-a"));
    apiMocks.fetchAnalysisResultExportDeletionPreflight.mockReturnValueOnce(
      preflight.promise,
    );
    const initialProps: Parameters<typeof useAnalysisExportState>[0] = {
      currentAnalysisId: "analysis-a",
      currentDatasetVersionId: "dataset-a",
      resetKey: 0,
    };
    const runner = new HookRunner(useAnalysisExportState, initialProps);

    await runner.act(() =>
      runner.output.onLoadAnalysisResultExportDeletionPreflight(
        "analysis-a",
        "export-a",
      ),
    );
    expect(runner.output.isLoadingAnalysisResultExportDeletionPreflight).toBe(true);
    runner.update({ ...initialProps, currentAnalysisId: null, resetKey: 1 });
    preflight.resolve(exportDeletionPreflight("analysis-a", "export-a"));
    await runner.flush();

    expect(runner.output.analysisResultExportDeletionPreflight).toBeNull();
    expect(runner.output.isLoadingAnalysisResultExportDeletionPreflight).toBe(false);

    runner.update({ ...initialProps, resetKey: 2 });
    await runner.flush();
    apiMocks.fetchAnalysisResultExportDeletionPreflight.mockResolvedValueOnce(
      exportDeletionPreflight("analysis-a", "export-a"),
    );
    await runner.act(() =>
      runner.output.onLoadAnalysisResultExportDeletionPreflight(
        "analysis-a",
        "export-a",
      ),
    );
    const deletion = deferred<AnalysisResultExportDeleteResponse>();
    apiMocks.deleteAnalysisResultExport.mockReturnValueOnce(deletion.promise);
    await runner.act(() =>
      runner.output.onDeleteAnalysisResultExport(
        exportDeletionPreflight("analysis-a", "export-a"),
      ),
    );
    expect(runner.output.isDeletingAnalysisResultExport).toBe(true);
    runner.update({ ...initialProps, currentAnalysisId: null, resetKey: 3 });
    deletion.resolve({
      deletion_schema_version: 1,
      analysis_id: "analysis-a",
      export_id: "export-a",
      deletion_manifest_sha256: "b".repeat(64),
      deleted_at: "2026-07-16T00:00:00Z",
      deleted_counts: { metadata_record_count: 1, file_count: 1, file_bytes: 128 },
      cleanup_status: "deleted",
    });
    await runner.flush();

    expect(runner.output.analysisResultExportDeletion).toBeNull();
    expect(runner.output.isDeletingAnalysisResultExport).toBe(false);
    expect(runner.output.analysisResultExportList).toBeNull();
    runner.unmount();
  });

  it("keeps comparison reset state after the old response resolves", async () => {
    const response = deferred<AnalysisRunComparisonResponse>();
    apiMocks.fetchAnalysisRunComparison.mockReturnValueOnce(response.promise);
    const runner = new HookRunner(useAnalysisComparisonState, { resetKey: 0 });
    await runner.act(() => runner.output.onSelectAnalysisComparisonRun("left", "analysis-a"));
    await runner.act(() => runner.output.onSelectAnalysisComparisonRun("right", "analysis-b"));
    await runner.act(() => runner.output.onCompareAnalysisRuns());
    expect(runner.output.isComparingAnalysisRuns).toBe(true);

    runner.update({ resetKey: 1 });
    response.resolve({ left: { analysis_id: "analysis-a" } } as AnalysisRunComparisonResponse);
    await runner.flush();

    expect(runner.output.analysisComparison).toBeNull();
    expect(runner.output.isComparingAnalysisRuns).toBe(false);
    runner.unmount();
  });

  it("keeps restore reset state after the dataset is cleared", async () => {
    const response = deferred<AnalysisResultEnvelope>();
    apiMocks.fetchAnalysisRunResult.mockReturnValueOnce(response.promise);
    const onRefreshAnalysisResultExports = vi.fn(() => Promise.resolve());
    const onSelectMethod = vi.fn();
    const initialProps = {
      analysisCatalog: null,
      currentAnalysisId: null,
      currentDatasetVersionId: "dataset-a",
      onRefreshAnalysisResultExports,
      onSelectMethod,
      resetKey: 0,
    };
    const runner = new HookRunner<
      Parameters<typeof useRestoredAnalysisResultState>[0],
      ReturnType<typeof useRestoredAnalysisResultState>
    >(useRestoredAnalysisResultState, initialProps);
    await runner.act(() => runner.output.onRestoreAnalysisRun("analysis-a"));
    expect(runner.output.isRestoringAnalysisResult).toBe(true);

    runner.update({ ...initialProps, currentDatasetVersionId: null });
    response.resolve({ analysis_id: "analysis-a" } as AnalysisResultEnvelope);
    await runner.flush();

    expect(runner.output.restoredAnalysisResult).toBeNull();
    expect(runner.output.isRestoringAnalysisResult).toBe(false);
    expect(onRefreshAnalysisResultExports).not.toHaveBeenCalled();
    runner.unmount();
  });

  it("keeps model B target catalog when model A resolves late", async () => {
    const first = deferred<DatasetVersionCatalogResponse>();
    const second = deferred<DatasetVersionCatalogResponse>();
    apiMocks.fetchDatasetVersions.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const runner = new HookRunner(useRegressionPredictionTargetState, {
      activeModelId: "model-a",
      currentVersionId: "dataset-a",
    });

    runner.update({ activeModelId: "model-b", currentVersionId: "dataset-a" });
    second.resolve({
      offset: 0,
      limit: 20,
      total: 2,
      returned: 0,
      has_previous: false,
      has_next: false,
      versions: [],
    });
    await runner.flush();
    first.resolve({
      offset: 0,
      limit: 20,
      total: 1,
      returned: 0,
      has_previous: false,
      has_next: false,
      versions: [],
    });
    await runner.flush();

    expect(runner.output.catalog?.total).toBe(2);
    expect(runner.output.isLoading).toBe(false);
    runner.unmount();
  });

  it("keeps prediction B CSV state when prediction A resolves late", async () => {
    const first = deferred<RegressionPredictionCsvExportResponse>();
    const second = deferred<RegressionPredictionCsvExportResponse>();
    apiMocks.createRegressionPredictionCsvExport
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const runner = new HookRunner<
      Parameters<typeof useRegressionPredictionExportState>[0],
      ReturnType<typeof useRegressionPredictionExportState>
    >(useRegressionPredictionExportState, "prediction-a");
    await runner.act(() => runner.output.onCreate());
    runner.update("prediction-b");
    await runner.act(() => runner.output.onCreate());
    second.resolve({ export_id: "export-b", prediction_id: "prediction-b" } as RegressionPredictionCsvExportResponse);
    await runner.flush();
    first.resolve({ export_id: "export-a", prediction_id: "prediction-a" } as RegressionPredictionCsvExportResponse);
    await runner.flush();

    expect(runner.output.csvExport?.prediction_id).toBe("prediction-b");
    expect(runner.output.isCreating).toBe(false);
    expect(runner.output.isDownloading).toBe(false);
    runner.unmount();
  });

  it("keeps the latest model preflight when an older preflight resolves late", async () => {
    const first = deferred<RegressionPredictionPreflightResponse>();
    const second = deferred<RegressionPredictionPreflightResponse>();
    apiMocks.fetchRegressionPredictionPreflight
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const initialProps = {
      confidenceLevel: 0.95,
      currentDatasetVersionId: "source-a",
      modelId: "model-a",
      targetDatasetVersionId: "target-a",
    };
    const runner = new HookRunner<
      Parameters<typeof useRegressionPredictionState>[0],
      ReturnType<typeof useRegressionPredictionState>
    >(useRegressionPredictionState, initialProps);
    await runner.act(() => runner.output.onRunPreflight());
    runner.update({ ...initialProps, modelId: "model-b", targetDatasetVersionId: "target-b" });
    await runner.act(() => runner.output.onRunPreflight());

    second.resolve(readyPreflight("model-b", "target-b"));
    await runner.flush();
    first.resolve(readyPreflight("model-a", "target-a"));
    await runner.flush();

    expect(runner.output.preflight?.model_id).toBe("model-b");
    expect(runner.output.isRunningPreflight).toBe(false);
    runner.unmount();
  });

  it("hydrates a checksum-validated stored prediction for matching model and target", () => {
    const stored = {
      prediction_id: "prediction-stored",
      model_id: "model-a",
      source_dataset_version_id: "source-a",
      target_dataset_version_id: "target-a",
    } as RegressionPredictionResponse;
    const props = {
      confidenceLevel: 0.95,
      currentDatasetVersionId: "source-a",
      initialPrediction: stored,
      modelId: "model-a",
      targetDatasetVersionId: "target-a",
    };
    const runner = new HookRunner<
      Parameters<typeof useRegressionPredictionState>[0],
      ReturnType<typeof useRegressionPredictionState>
    >(useRegressionPredictionState, props);

    expect(runner.output.prediction).toBe(stored);
    runner.update({ ...props, targetDatasetVersionId: "target-b" });
    expect(runner.output.prediction).toBeNull();
    expect(runner.output.isRunningPrediction).toBe(false);
    runner.unmount();
  });

  it("keeps prediction state reset when its target changes during execution", async () => {
    const prediction = deferred<RegressionPredictionResponse>();
    apiMocks.fetchRegressionPredictionPreflight.mockResolvedValueOnce(
      readyPreflight("model-a", "target-a"),
    );
    apiMocks.fetchRegressionPredictions.mockReturnValueOnce(prediction.promise);
    const initialProps = {
      confidenceLevel: 0.95,
      currentDatasetVersionId: "source-a",
      modelId: "model-a",
      targetDatasetVersionId: "target-a",
    };
    const runner = new HookRunner<
      Parameters<typeof useRegressionPredictionState>[0],
      ReturnType<typeof useRegressionPredictionState>
    >(useRegressionPredictionState, initialProps);
    await runner.act(() => runner.output.onRunPreflight());
    await runner.act(() => runner.output.onRunPrediction());
    expect(runner.output.isRunningPrediction).toBe(true);

    runner.update({ ...initialProps, targetDatasetVersionId: "target-b" });
    prediction.resolve({ prediction_id: "prediction-a" } as RegressionPredictionResponse);
    await runner.flush();

    expect(runner.output.prediction).toBeNull();
    expect(runner.output.preflight).toBeNull();
    expect(runner.output.isRunningPrediction).toBe(false);
    expect(runner.output.isRunningPreflight).toBe(false);
    runner.unmount();
  });

  it("ignores an old page response after a new prediction and resets loading", async () => {
    const firstPage = deferred<RegressionPredictionRowsPageResponse>();
    const oldSecondPage = deferred<RegressionPredictionRowsPageResponse>();
    const newFirstPage = deferred<RegressionPredictionRowsPageResponse>();
    apiMocks.fetchRegressionPredictionRows
      .mockReturnValueOnce(firstPage.promise)
      .mockReturnValueOnce(oldSecondPage.promise)
      .mockReturnValueOnce(newFirstPage.promise);
    const runner = new HookRunner<
      Parameters<typeof useRegressionPredictionRowsState>[0],
      ReturnType<typeof useRegressionPredictionRowsState>
    >(useRegressionPredictionRowsState, "prediction-a");
    firstPage.resolve(rowsPage("prediction-a", 0));
    await runner.flush();
    await runner.act(() => runner.output.onPageChange(25));
    runner.update("prediction-b");
    newFirstPage.resolve(rowsPage("prediction-b", 0));
    await runner.flush();
    oldSecondPage.resolve(rowsPage("prediction-a", 25));
    await runner.flush();

    expect(runner.output.page?.prediction_id).toBe("prediction-b");
    expect(runner.output.page?.offset).toBe(0);
    expect(runner.output.isLoading).toBe(false);

    runner.update(null);
    expect(runner.output.page).toBeNull();
    expect(runner.output.isLoading).toBe(false);
    runner.unmount();
  });

  it("reaches the 51st Bayesian study and ignores an older catalog response", async () => {
    const first = deferred<BayesianStudyListResponse>();
    const second = deferred<BayesianStudyListResponse>();
    apiMocks.fetchBayesianStudies
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const selectedId = "00000000-0000-4000-8000-000000000099";
    const runner = new HookRunner<
      string | null,
      ReturnType<typeof useBayesianStudyCatalogState>
    >(useBayesianStudyCatalogState, selectedId);

    await runner.act(() => runner.output.onPageChange(40));
    second.resolve({
      total: 51,
      offset: 40,
      limit: 20,
      items: [
        {
          study_id: "00000000-0000-4000-8000-000000000051",
          study_version_id: "00000000-0000-4000-8000-000000000151",
          method_id: "doe.bayesian_optimization",
          method_version: "0.2.2",
          name: "Study 51",
          status: "active",
          predecessor_study_id: null,
          updated_at: "2026-07-19T00:00:00Z",
          definition_sha256: "a".repeat(64),
          pending_trial_count: 2,
          completed_trial_count: 0,
          abandoned_trial_count: 0,
          observation_history_sha256: "b".repeat(64),
        },
      ],
    });
    await runner.flush();
    first.resolve({ total: 51, offset: 0, limit: 20, items: [] });
    await runner.flush();

    expect(apiMocks.fetchBayesianStudies).toHaveBeenNthCalledWith(1, 0, 20);
    expect(apiMocks.fetchBayesianStudies).toHaveBeenNthCalledWith(2, 40, 20);
    expect(runner.output.catalog?.offset).toBe(40);
    expect(runner.output.catalog?.items[0]?.name).toBe("Study 51");
    expect(runner.output.selectedStudyId).toBe(selectedId);
    expect(runner.output.selectedSummary).toBeNull();
    expect(runner.output.isLoading).toBe(false);
    runner.unmount();
  });

  it("keeps Bayesian draft factor and constraint state independent from catalog state", async () => {
    const runner = new HookRunner<void, ReturnType<typeof useBayesianStudyDraftState>>(
      useBayesianStudyDraftState,
      undefined,
    );

    await runner.act(() => runner.output.addFactor());
    expect(runner.output.factors).toHaveLength(2);
    expect(runner.output.minimumInitialDesignSize).toBe(3);
    expect(runner.output.initialDesignSize).toBe("3");
    await runner.act(() => runner.output.addConstraint());
    await runner.act(() =>
      runner.output.updateConstraintCoefficient(
        runner.output.constraints[0].key,
        runner.output.factors[0].key,
        "1.5",
      ),
    );
    expect(runner.output.constraints[0]?.coefficients[1]).toBe("1.5");
    runner.unmount();
  });

  it("keeps the newest Bayesian Study restore and resets lifecycle loading on selection", async () => {
    const studyA = deferred<BayesianStudyResponse>();
    const studyB = deferred<BayesianStudyResponse>();
    apiMocks.fetchBayesianStudy
      .mockReturnValueOnce(studyA.promise)
      .mockReturnValueOnce(studyB.promise);
    const runner = new HookRunner<
      string | null,
      ReturnType<typeof useBayesianStudyLifecycleState>
    >(useBayesianStudyLifecycleState, "study-a");

    runner.update("study-b");
    expect(runner.output.study).toBeNull();
    expect(runner.output.isRestoring).toBe(true);
    studyB.resolve(bayesianStudy("study-b"));
    await runner.flush();
    studyA.resolve(bayesianStudy("study-a"));
    await runner.flush();

    expect(runner.output.study?.study_id).toBe("study-b");
    expect(runner.output.isRestoring).toBe(false);
    expect(runner.output.isSavingTrial).toBe(false);
    expect(runner.output.isClosing).toBe(false);
    runner.update(null);
    expect(runner.output.study).toBeNull();
    expect(runner.output.isRestoring).toBe(false);
    runner.unmount();
  });

  it("does not apply a Bayesian Study restore after unmount", async () => {
    const pending = deferred<BayesianStudyResponse>();
    apiMocks.fetchBayesianStudy.mockReturnValueOnce(pending.promise);
    const runner = new HookRunner<
      string | null,
      ReturnType<typeof useBayesianStudyLifecycleState>
    >(useBayesianStudyLifecycleState, "study-a");

    runner.unmount();
    pending.resolve(bayesianStudy("study-a"));
    await Promise.resolve();
    await Promise.resolve();

    expect(runner.output.study).toBeNull();
  });

  it("ignores observation and close responses after the selected Study changes", async () => {
    const observation = deferred<unknown>();
    const close = deferred<{ study: BayesianStudyResponse }>();
    const studyB = deferred<BayesianStudyResponse>();
    const studyC = deferred<BayesianStudyResponse>();
    apiMocks.fetchBayesianStudy
      .mockResolvedValueOnce(bayesianStudy("study-a"))
      .mockReturnValueOnce(studyB.promise)
      .mockReturnValueOnce(studyC.promise);
    apiMocks.recordBayesianObservation.mockReturnValueOnce(observation.promise);
    apiMocks.closeBayesianStudy.mockReturnValueOnce(close.promise);
    const runner = new HookRunner<
      string | null,
      ReturnType<typeof useBayesianStudyLifecycleState>
    >(useBayesianStudyLifecycleState, "study-a");
    await runner.flush();

    await runner.act(() => runner.output.setObservation("study-a-trial-1", "1.25"));
    await runner.act(() =>
      runner.output.requestTrialTransition("study-a-trial-1", "complete"),
    );
    await runner.act(() => {
      void runner.output.confirmTrialTransition();
    });
    expect(runner.output.isSavingTrial).toBe(true);
    runner.update("study-b");
    expect(runner.output.isSavingTrial).toBe(false);
    observation.resolve({});
    studyB.resolve(bayesianStudy("study-b"));
    await runner.flush();
    expect(runner.output.study?.study_id).toBe("study-b");

    await runner.act(() => {
      runner.output.setPendingStudyClose(true);
      void runner.output.confirmStudyClose();
    });
    expect(runner.output.isClosing).toBe(true);
    runner.update("study-c");
    expect(runner.output.isClosing).toBe(false);
    close.resolve({ study: bayesianStudy("study-b", "completed") });
    studyC.resolve(bayesianStudy("study-c"));
    await runner.flush();

    expect(runner.output.study?.study_id).toBe("study-c");
    expect(apiMocks.fetchBayesianStudy).toHaveBeenCalledTimes(3);
    runner.unmount();
  });

  it("restores only the current Study recommendation and preserves its request budget", async () => {
    const latestA = deferred<{ item: BayesianRecommendationResponse | null }>();
    const exactB = deferred<BayesianRecommendationResponse>();
    const selected = vi.fn();
    apiMocks.fetchLatestBayesianRecommendation.mockReturnValueOnce(latestA.promise);
    apiMocks.fetchBayesianRecommendation.mockReturnValueOnce(exactB.promise);
    const runner = new HookRunner<
      Parameters<typeof useBayesianRecommendationState>[0],
      ReturnType<typeof useBayesianRecommendationState>
    >(useBayesianRecommendationState, {
      selectedStudyId: "study-a",
      requestedRecommendationId: null,
      onRecommendationSelected: selected,
    });

    runner.update({
      selectedStudyId: "study-b",
      requestedRecommendationId: "recommendation-b",
      onRecommendationSelected: selected,
    });
    exactB.resolve(bayesianRecommendation("study-b", "recommendation-b", 75));
    await runner.flush();
    latestA.resolve({ item: bayesianRecommendation("study-a", "recommendation-a") });
    await runner.flush();

    expect(runner.output.recommendation?.recommendation_id).toBe("recommendation-b");
    expect(runner.output.totalTrialBudget).toBe("75");
    expect(runner.output.isRestoring).toBe(false);
    expect(selected).not.toHaveBeenCalledWith("recommendation-a");
    runner.unmount();
  });

  it("reports a recommendation/Study mismatch and does not duplicate latest with an exact fetch", async () => {
    const selected = vi.fn();
    apiMocks.fetchLatestBayesianRecommendation.mockResolvedValueOnce({
      study_id: "study-a",
      study_version_id: "study-a-version",
      item: bayesianRecommendation("study-a", "recommendation-a"),
    });
    const latestRunner = new HookRunner<
      Parameters<typeof useBayesianRecommendationState>[0],
      ReturnType<typeof useBayesianRecommendationState>
    >(useBayesianRecommendationState, {
      selectedStudyId: "study-a",
      requestedRecommendationId: null,
      onRecommendationSelected: selected,
    });
    await latestRunner.flush();

    expect(selected).toHaveBeenCalledWith("recommendation-a");
    expect(apiMocks.fetchBayesianRecommendation).not.toHaveBeenCalled();
    latestRunner.unmount();

    apiMocks.fetchBayesianRecommendation.mockResolvedValueOnce(
      bayesianRecommendation("study-b", "recommendation-a"),
    );
    const mismatchRunner = new HookRunner<
      Parameters<typeof useBayesianRecommendationState>[0],
      ReturnType<typeof useBayesianRecommendationState>
    >(useBayesianRecommendationState, {
      selectedStudyId: "study-a",
      requestedRecommendationId: "recommendation-a",
      onRecommendationSelected: vi.fn(),
    });
    await mismatchRunner.flush();

    expect(mismatchRunner.output.recommendation).toBeNull();
    expect(mismatchRunner.output.error).toBe("bayesian_recommendation_study_mismatch");
    mismatchRunner.unmount();
  });

  it("ignores recommendation creation after a Study change and clears loading", async () => {
    const created = deferred<BayesianRecommendationBatchResponse>();
    apiMocks.fetchLatestBayesianRecommendation.mockResolvedValue({
      study_id: "study-a",
      study_version_id: "study-a-version",
      item: null,
    });
    apiMocks.createBayesianRecommendationBatch.mockReturnValueOnce(created.promise);
    const selected = vi.fn();
    const runner = new HookRunner<
      Parameters<typeof useBayesianRecommendationState>[0],
      ReturnType<typeof useBayesianRecommendationState>
    >(useBayesianRecommendationState, {
      selectedStudyId: "study-a",
      requestedRecommendationId: null,
      onRecommendationSelected: selected,
    });
    await runner.flush();

    await runner.act(() => {
      void runner.output.onRecommend({
        ...bayesianStudy("study-a"),
        trial_count: 2,
        recommendation_hard_trial_limit: 200,
      });
    });
    expect(runner.output.isRecommending).toBe(true);
    runner.update({
      selectedStudyId: "study-b",
      requestedRecommendationId: null,
      onRecommendationSelected: selected,
    });
    expect(runner.output.isRecommending).toBe(false);
    created.resolve(bayesianRecommendationBatch("study-a", "batch-a"));
    await runner.flush();

    expect(runner.output.recommendation).toBeNull();
    expect(selected).not.toHaveBeenCalledWith("recommendation-a");
    runner.unmount();
  });

  it("creates one atomic batch request with a distinct batch size and candidate pool", async () => {
    const selectedBatch = vi.fn();
    apiMocks.fetchLatestBayesianRecommendation.mockResolvedValue({
      study_id: "study-a",
      study_version_id: "study-a-version",
      item: null,
    });
    apiMocks.createBayesianRecommendationBatch.mockResolvedValue(
      bayesianRecommendationBatch("study-a", "batch-a"),
    );
    const runner = new HookRunner<
      Parameters<typeof useBayesianRecommendationState>[0],
      ReturnType<typeof useBayesianRecommendationState>
    >(useBayesianRecommendationState, {
      selectedStudyId: "study-a",
      requestedBatchId: null,
      requestedRecommendationId: null,
      onBatchSelected: selectedBatch,
      onRecommendationSelected: vi.fn(),
    });
    await runner.flush();

    await runner.act(() => {
      runner.output.onExecutionModeChange("parallel_batch");
      runner.output.setBatchSize("4");
      runner.output.setExplorationProfile("exploration");
    });
    const recommendationPromise = runner.output.onRecommend({
      ...bayesianStudy("study-a"),
      trial_count: 2,
      recommendation_hard_trial_limit: 200,
    });
    await runner.flush();
    await recommendationPromise;
    await runner.flush();

    expect(apiMocks.createBayesianRecommendationBatch).toHaveBeenCalledTimes(1);
    const request = apiMocks.createBayesianRecommendationBatch.mock.calls[0]?.[1] as
      | BayesianRecommendationBatchCreateRequest
      | undefined;
    if (request === undefined) {
      throw new Error("expected_batch_request");
    }
    expect(request).toMatchObject({
      execution_mode: "parallel_batch",
      batch_size: 4,
      acquisition: {
        kind: "expected_improvement",
        exploration_profile: "exploration",
        xi_standardized: 0.1,
      },
      search: {
        candidate_count_per_step: 256,
        total_trial_budget: 50,
      },
    });
    expect(request.batch_size).not.toBe(
      request.search.candidate_count_per_step,
    );
    expect(selectedBatch).toHaveBeenCalledWith("batch-a");
    runner.unmount();
  });

  it("keeps deletion preflight and delete responses scoped to the current Study", async () => {
    const preflightA = deferred<BayesianStudyDeletionPreflightResponse>();
    apiMocks.fetchBayesianStudyDeletionPreflight.mockReturnValueOnce(preflightA.promise);
    const runner = new HookRunner<
      BayesianStudyResponse | null,
      ReturnType<typeof useBayesianRetentionState>
    >(useBayesianRetentionState, bayesianStudy("study-a", "abandoned"));

    await runner.act(() => {
      void runner.output.onCheck();
    });
    expect(runner.output.isChecking).toBe(true);
    runner.update(bayesianStudy("study-b", "abandoned"));
    preflightA.resolve(bayesianDeletionPreflight("study-a"));
    await runner.flush();
    expect(runner.output.preflight).toBeNull();
    expect(runner.output.isChecking).toBe(false);

    apiMocks.fetchBayesianStudyDeletionPreflight.mockResolvedValueOnce(
      bayesianDeletionPreflight("study-b", ["bayesian_study_deletion_referenced"]),
    );
    await runner.act(() => {
      void runner.output.onCheck();
    });
    expect(runner.output.preflight?.eligible).toBe(false);
    expect(runner.output.preflight?.successor_study_count).toBe(1);

    runner.update(bayesianStudy("study-c", "abandoned"));
    apiMocks.fetchBayesianStudyDeletionPreflight.mockResolvedValueOnce(
      bayesianDeletionPreflight("study-c"),
    );
    await runner.act(() => {
      void runner.output.onCheck();
    });
    const deletion = deferred<unknown>();
    apiMocks.deleteBayesianStudy.mockReturnValueOnce(deletion.promise);
    await runner.act(() => {
      void runner.output.onDelete();
    });
    expect(runner.output.isDeleting).toBe(true);
    runner.update(bayesianStudy("study-d", "abandoned"));
    deletion.resolve({});
    await runner.flush();
    expect(runner.output.preflight).toBeNull();
    expect(runner.output.isDeleting).toBe(false);

    runner.update(bayesianStudy("study-active"));
    await runner.act(() => {
      void runner.output.onCheck();
    });
    expect(apiMocks.fetchBayesianStudyDeletionPreflight).toHaveBeenCalledTimes(3);
    runner.unmount();
  });
});
