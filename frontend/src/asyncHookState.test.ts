import * as React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
  DatasetVersionCatalogResponse,
  RegressionPredictionCsvExportResponse,
  RegressionPredictionPreflightResponse,
  RegressionPredictionResponse,
  RegressionPredictionRowsPageResponse,
  RegressionModelDeleteResponse,
  RegressionModelDeletionPreflightResponse,
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

const apiMocks = vi.hoisted(() => ({
  createAnalysisResultCsvExport: vi.fn(),
  createAnalysisResultHtmlReport: vi.fn(),
  createAnalysisResultJsonExport: vi.fn(),
  createRegressionPredictionCsvExport: vi.fn(),
  deleteAnalysisResultExport: vi.fn(),
  deleteAttributeControlLimitSet: vi.fn(),
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
  fetchDatasetVersions: vi.fn(),
  fetchRegressionPredictionPreflight: vi.fn(),
  fetchRegressionPredictions: vi.fn(),
  fetchRegressionPredictionRows: vi.fn(),
  fetchRegressionModelDeletionPreflight: vi.fn(),
  fetchRegressionModelManifest: vi.fn(),
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

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.fetchRegressionModelManifest.mockResolvedValue({});
});

describe("async workbench hooks", () => {
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
});
