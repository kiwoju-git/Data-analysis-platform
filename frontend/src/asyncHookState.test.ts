import * as React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AnalysisResultEnvelope,
  AnalysisResultExportListResponse,
  AnalysisRunComparisonResponse,
  AnalysisRunListResponse,
  DatasetVersionCatalogResponse,
  RegressionPredictionCsvExportResponse,
  RegressionPredictionPreflightResponse,
  RegressionPredictionResponse,
  RegressionPredictionRowsPageResponse,
} from "./api";
import { useAnalysisComparisonState } from "./useAnalysisComparisonState";
import { useAnalysisExportState } from "./useAnalysisExportState";
import { useAnalysisHistoryState } from "./useAnalysisHistoryState";
import { useRegressionPredictionExportState } from "./useRegressionPredictionExportState";
import { useRegressionPredictionRowsState } from "./useRegressionPredictionRowsState";
import { useRegressionPredictionState } from "./useRegressionPredictionState";
import { useRegressionPredictionTargetState } from "./useRegressionPredictionTargetState";
import { useRestoredAnalysisResultState } from "./useRestoredAnalysisResultState";

const apiMocks = vi.hoisted(() => ({
  createAnalysisResultCsvExport: vi.fn(),
  createAnalysisResultHtmlReport: vi.fn(),
  createAnalysisResultJsonExport: vi.fn(),
  createRegressionPredictionCsvExport: vi.fn(),
  downloadAnalysisResultExport: vi.fn(),
  fetchAnalysisResultExports: vi.fn(),
  fetchAnalysisRunComparison: vi.fn(),
  fetchAnalysisRunResult: vi.fn(),
  fetchAnalysisRuns: vi.fn(),
  fetchDatasetVersions: vi.fn(),
  fetchRegressionPredictionPreflight: vi.fn(),
  fetchRegressionPredictions: vi.fn(),
  fetchRegressionPredictionRows: vi.fn(),
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
});

describe("async workbench hooks", () => {
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
