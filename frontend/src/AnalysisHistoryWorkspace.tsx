import type {
  AnalysisWorkbenchComparisonState,
  AnalysisWorkbenchHistoryState,
  AnalysisWorkbenchRestoredState,
} from "./AnalysisWorkbench";
import { AnalysisHistoryPanel } from "./AnalysisHistoryPanel";
import type { AnalysisMethodListResponse, DatasetVersionResponse } from "./api";

export function AnalysisHistoryWorkspace({
  catalog,
  comparisonState,
  historyState,
  restoredState,
  version,
}: {
  catalog: AnalysisMethodListResponse;
  comparisonState?: AnalysisWorkbenchComparisonState;
  historyState?: AnalysisWorkbenchHistoryState;
  restoredState?: AnalysisWorkbenchRestoredState;
  version: DatasetVersionResponse | null;
}) {
  return (
    <AnalysisHistoryPanel
      catalog={catalog}
      comparison={comparisonState?.analysisComparison ?? null}
      comparisonError={comparisonState?.analysisComparisonError ?? null}
      comparisonLeftId={comparisonState?.analysisComparisonLeftId ?? null}
      comparisonRightId={comparisonState?.analysisComparisonRightId ?? null}
      deletion={historyState?.analysisRunDeletion ?? null}
      deletionError={historyState?.analysisRunDeletionError ?? null}
      deletionPreflight={historyState?.analysisRunDeletionPreflight ?? null}
      fetchError={historyState?.analysisHistoryError ?? null}
      history={historyState?.analysisHistory ?? null}
      isComparing={comparisonState?.isComparingAnalysisRuns ?? false}
      isDeleting={historyState?.isDeletingAnalysisRun ?? false}
      isLoading={historyState?.isLoadingAnalysisHistory ?? false}
      isLoadingDeletionPreflight={
        historyState?.isLoadingAnalysisRunDeletionPreflight ?? false
      }
      isRestoring={restoredState?.isRestoringAnalysisResult ?? false}
      methodIdFilter={historyState?.analysisHistoryMethodId ?? ""}
      offset={historyState?.analysisHistoryOffset ?? 0}
      restoredResult={restoredState?.restoredAnalysisResult ?? null}
      restoreError={restoredState?.restoredAnalysisResultError ?? null}
      resultAvailabilityFilter={
        historyState?.analysisHistoryResultAvailabilityFilter ?? "all"
      }
      staleFilter={historyState?.analysisHistoryStaleFilter ?? "all"}
      statusFilter={historyState?.analysisHistoryStatus ?? ""}
      version={version}
      onChangeFilters={historyState?.onChangeAnalysisHistoryFilters ?? (() => undefined)}
      onClearDeletion={historyState?.onClearAnalysisRunDeletion ?? (() => undefined)}
      onCompare={comparisonState?.onCompareAnalysisRuns ?? (() => undefined)}
      onDelete={historyState?.onDeleteAnalysisRun ?? (() => undefined)}
      onLoadDeletionPreflight={
        historyState?.onLoadAnalysisRunDeletionPreflight ?? (() => undefined)
      }
      onPageChange={historyState?.onChangeAnalysisHistoryPage ?? (() => undefined)}
      onRefresh={historyState?.onRefreshAnalysisHistory ?? (() => undefined)}
      onRestore={restoredState?.onRestoreAnalysisRun ?? (() => undefined)}
      onSelectComparisonRun={
        comparisonState?.onSelectAnalysisComparisonRun ?? (() => undefined)
      }
    />
  );
}
