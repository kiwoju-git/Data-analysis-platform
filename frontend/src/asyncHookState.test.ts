import * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AnalysisResultEnvelope,
  AnalysisRunDeleteResponse,
  AnalysisRunDeletionPreflightResponse,
  AnalysisResultExportDeleteResponse,
  AnalysisResultExportDeletionPreflightResponse,
  AnalysisResultExportListResponse,
  AnalysisRunComparisonResponse,
  AnalysisRunListResponse,
  AttributeControlLimitSetListResponse,
  AttributeControlLimitSetDeletionPreflightResponse,
  AttributeControlLimitSetResponse,
  BayesianRecommendationResponse,
  BayesianStudyDeletionPreflightResponse,
  BayesianStudyListResponse,
  BayesianStudyResponse,
  DatasetVersionCatalogItem,
  DatasetVersionCatalogResponse,
  DatasetVersionDeleteResponse,
  DatasetVersionDeletionPreflightResponse,
  DatasetVersionResponse,
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
import { useChartPointInteraction } from "./charts/useChartPointInteraction";
import { useDatasetWorkflow } from "./useDatasetWorkflow";
import { useDatasetVersionRetentionState } from "./useDatasetVersionRetentionState";
import { useRuntimeCompatibilityState } from "./useRuntimeCompatibilityState";

const apiMocks = vi.hoisted(() => ({
  abandonBayesianTrial: vi.fn(),
  closeBayesianStudy: vi.fn(),
  createBayesianRecommendation: vi.fn(),
  createBayesianStudy: vi.fn(),
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
  fetchAnalysisRunComparison: vi.fn(),
  fetchAnalysisRunDeletionPreflight: vi.fn(),
  fetchAnalysisRunResult: vi.fn(),
  fetchAnalysisRuns: vi.fn(),
  fetchAttributeControlLimitSets: vi.fn(),
  fetchAttributeControlLimitSetDeletionPreflight: vi.fn(),
  fetchAttributeControlMonitoringPreflight: vi.fn(),
  fetchBayesianRecommendation: vi.fn(),
  fetchBayesianStudy: vi.fn(),
  fetchBayesianStudyDeletionPreflight: vi.fn(),
  fetchBayesianStudies: vi.fn(),
  fetchLatestBayesianRecommendation: vi.fn(),
  fetchDatasetProfile: vi.fn(),
  fetchDatasetVersion: vi.fn(),
  fetchDatasetVersionDeletionPreflight: vi.fn(),
  fetchDatasetVersions: vi.fn(),
  fetchRowsPreview: vi.fn(),
  fetchRuntimeInfo: vi.fn(),
  fetchRegressionPredictionPreflight: vi.fn(),
  fetchRegressionPredictions: vi.fn(),
  fetchRegressionPredictionRows: vi.fn(),
  fetchRegressionModelDeletionPreflight: vi.fn(),
  fetchRegressionModelManifest: vi.fn(),
  recordBayesianObservation: vi.fn(),
}));

vi.mock("./api", () => apiMocks);

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve: (value: T) => void = () => undefined;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
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

function exportListResponse(analysisId: string): AnalysisResultExportListResponse {
  return { analysis_id: analysisId, exports: [] };
}

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
  };
}

function runtimeInfo(
  overrides: Partial<RuntimeInfoResponse> = {},
): RuntimeInfoResponse {
  return {
    service: "datalab-studio-api",
    app_version: "0.1.0",
    api_contract_version: 2,
    metadata_schema_version: 15,
    build_commit: "unknown",
    capabilities: {
      asset_management: true,
      dataset_version_metadata: true,
      dataset_version_deletion: true,
      regression_model_metadata: true,
      regression_model_deletion: true,
      dedicated_predict: true,
      dedicated_response_optimizer: true,
      bayesian_optimization: true,
    },
    ...overrides,
  };
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.fetchRegressionModelManifest.mockResolvedValue({});
  apiMocks.fetchDatasetVersions.mockResolvedValue({
    total: 0,
    offset: 0,
    limit: 20,
    returned: 0,
    has_previous: false,
    has_next: false,
    versions: [],
  });
});

afterEach(() => {
  Reflect.deleteProperty(globalThis, "window");
});

describe("async workbench hooks", () => {
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
      deletion_manifest_sha256: "a".repeat(64),
    } as DatasetVersionDeletionPreflightResponse;
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

    expect(apiMocks.deleteDatasetVersion).toHaveBeenCalledWith(preflight);
    expect(runner.output.deletion).toEqual(response);
    expect(onDeleted).toHaveBeenCalledWith(response);
    runner.unmount();
  });

  it("supports focus selection and Escape clearing for interactive chart points", async () => {
    const runner = new HookRunner<string[], ReturnType<typeof useChartPointInteraction>>(
      useChartPointInteraction,
      ["point-1", "point-2", "point-3"],
    );
    expect(runner.output.tabIndexFor("point-1")).toBe(0);
    expect(runner.output.tabIndexFor("point-2")).toBe(-1);
    await runner.act(() => runner.output.activate("point-1", 20, 30, "focus"));
    expect(runner.output.activePoint).toEqual({
      id: "point-1",
      left: 20,
      top: 30,
      source: "focus",
    });
    const preventDefault = vi.fn();
    await runner.act(() =>
      runner.output.handleKeyDown({
        key: "Escape",
        preventDefault,
      } as unknown as React.KeyboardEvent<Element>),
    );
    expect(preventDefault).toHaveBeenCalledOnce();
    expect(runner.output.activePoint).toBeNull();
    runner.unmount();
  });

  it("uses roving tabindex and arrow/Home/End navigation for chart items", async () => {
    const runner = new HookRunner<string[], ReturnType<typeof useChartPointInteraction>>(
      useChartPointInteraction,
      ["point-1", "point-2", "point-3"],
    );
    const focusSecond = vi.fn();
    const focusThird = vi.fn();
    await runner.act(() => {
      runner.output.itemRef("point-2", { focus: focusSecond } as unknown as SVGElement);
      runner.output.itemRef("point-3", { focus: focusThird } as unknown as SVGElement);
    });
    const preventDefault = vi.fn();
    await runner.act(() => runner.output.handleKeyDown({
      key: "ArrowRight",
      preventDefault,
    } as unknown as React.KeyboardEvent<Element>, "point-1"));
    expect(preventDefault).toHaveBeenCalledOnce();
    expect(focusSecond).toHaveBeenCalledOnce();
    expect(runner.output.tabIndexFor("point-2")).toBe(0);

    await runner.act(() => runner.output.handleKeyDown({
      key: "End",
      preventDefault,
    } as unknown as React.KeyboardEvent<Element>, "point-2"));
    expect(focusThird).toHaveBeenCalledOnce();
    expect(runner.output.tabIndexFor("point-3")).toBe(0);
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
    apiMocks.fetchRowsPreview.mockReturnValueOnce(previewA.promise).mockReturnValueOnce(previewB.promise);
    apiMocks.fetchDatasetProfile.mockReturnValueOnce(profileA.promise).mockReturnValueOnce(profileB.promise);

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

    const columnsB = [{ column_id: "column-b" }] as DatasetVersionResponse["columns"];
    versionB.resolve({
      version_id: idB,
      dataset_id: "10000000-0000-4000-8000-000000000002",
      version_number: 1,
      row_count: 48,
      column_count: 1,
      schema_hash: "schema-b",
      source_sha256: "b".repeat(64),
      parsing: { has_header: true },
      columns: columnsB,
      created_at: "2026-07-21T00:00:00Z",
    } as DatasetVersionResponse);
    previewB.resolve({ version_id: idB, rows: [] } as unknown as DatasetRowsPreviewResponse);
    profileB.resolve({ version_id: idB } as unknown as DatasetProfileResponse);
    await runner.flush();

    versionA.resolve({
      version_id: idA,
      dataset_id: "10000000-0000-4000-8000-000000000001",
      version_number: 1,
      row_count: 240,
      column_count: 1,
      schema_hash: "schema-a",
      source_sha256: "a".repeat(64),
      parsing: { has_header: true },
      columns: [{ column_id: "column-a" }],
      created_at: "2026-07-21T00:00:00Z",
    } as DatasetVersionResponse);
    previewA.resolve({ version_id: idA, rows: [] } as unknown as DatasetRowsPreviewResponse);
    profileA.resolve({ version_id: idA } as unknown as DatasetProfileResponse);
    await runner.flush();

    expect(runner.output.version?.version_id).toBe(idB);
    expect(runner.output.datasetPageProps.preview?.version_id).toBe(idB);
    expect(runner.output.profile?.version_id).toBe(idB);
    expect(storage.get("datalab.current_dataset_version_id")).toBe(idB);
    expect(new URL(currentHref).searchParams.get("dataset_version_id")).toBe(idB);
    expect(callbacks.onDatasetColumnsChanged).toHaveBeenLastCalledWith(columnsB);
    expect(callbacks.onDatasetReset).toHaveBeenCalledTimes(2);
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
    } as AttributeControlLimitSetListResponse);
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
    } as RegressionModelDeletionPreflightResponse);
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
    } as RegressionModelDeletionPreflightResponse);
    apiMocks.deleteRegressionModel.mockResolvedValue({
      model_id: "model-a",
    } as RegressionModelDeleteResponse);
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
    const created = deferred<BayesianRecommendationResponse>();
    apiMocks.fetchLatestBayesianRecommendation.mockResolvedValue({
      study_id: "study-a",
      study_version_id: "study-a-version",
      item: null,
    });
    apiMocks.createBayesianRecommendation.mockReturnValueOnce(created.promise);
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
    created.resolve(bayesianRecommendation("study-a", "recommendation-a"));
    await runner.flush();

    expect(runner.output.recommendation).toBeNull();
    expect(selected).not.toHaveBeenCalledWith("recommendation-a");
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
