import type { DatasetVersionResponse } from "./api";
import { formatLocalDateTime } from "./dateFormat";
import type { DatasetVersionCatalogState } from "./useDatasetVersionCatalogState";

export interface ActiveDatasetVersionSelectorProps {
  catalogState: DatasetVersionCatalogState;
  isSwitching: boolean;
  pendingVersionId: string | null;
  version: DatasetVersionResponse | null;
  onRetrySwitch: () => void;
  onSelect: (versionId: string) => void;
}

export function ActiveDatasetVersionSelector({
  catalogState,
  isSwitching,
  pendingVersionId,
  version,
  onRetrySwitch,
  onSelect,
}: ActiveDatasetVersionSelectorProps) {
  const selectedVersionId = pendingVersionId ?? version?.version_id ?? "";
  const activeOnCurrentPage = catalogState.catalog?.versions.some(
    (candidate) => candidate.version_id === selectedVersionId,
  );
  const activeOffPage =
    catalogState.activeItem !== null &&
    catalogState.activeItem.version_id === selectedVersionId &&
    !activeOnCurrentPage
      ? catalogState.activeItem
      : null;
  const currentVersionFallback =
    version !== null &&
    version.version_id === selectedVersionId &&
    !activeOnCurrentPage &&
    activeOffPage === null
      ? version
      : null;
  const disabled = isSwitching || catalogState.isLoading;

  return (
    <section
      className="active-dataset-card active-dataset-selector"
      aria-label="데이터셋 컨텍스트"
    >
      <div className="active-dataset-main">
        <div className="active-dataset-picker">
          <label htmlFor="active-dataset-version">현재 분석 데이터셋</label>
          <select
            aria-describedby="active-dataset-help"
            id="active-dataset-version"
            disabled={disabled || catalogState.catalog === null}
            value={selectedVersionId}
            onChange={(event) => onSelect(event.currentTarget.value)}
          >
            <option value="">데이터셋 버전 선택</option>
            {activeOffPage !== null ? (
              <option value={activeOffPage.version_id}>
                {catalogItemLabel(activeOffPage)}
              </option>
            ) : null}
            {currentVersionFallback !== null ? (
              <option value={currentVersionFallback.version_id}>
                {currentVersionLabel(currentVersionFallback)}
              </option>
            ) : null}
            {catalogState.catalog?.versions.map((item) => (
              <option key={item.version_id} value={item.version_id}>
                {catalogItemLabel(item)}
              </option>
            ))}
          </select>
          <span className="active-dataset-inline-help" aria-hidden="true">
            전환 시 미저장 입력과 현재 결과가 초기화됩니다.
          </span>
          <span className="visually-hidden" id="active-dataset-help">
            데이터셋을 전환하면 현재 일반 분석 입력과 화면 결과가 새 버전에 맞게
            초기화됩니다.
          </span>
        </div>
        {version !== null ? (
          <div className="active-dataset-summary-region">
            <dl className="active-dataset-summary" aria-label="현재 데이터셋 요약">
              <div className="active-dataset-stat">
                <dt>버전</dt>
                <dd>{`v${version.version_number}`}</dd>
              </div>
              <div className="active-dataset-stat">
                <dt>행</dt>
                <dd>{version.row_count.toLocaleString()}</dd>
              </div>
              <div className="active-dataset-stat">
                <dt>열</dt>
                <dd>{version.column_count.toLocaleString()}</dd>
              </div>
              <div className="active-dataset-stat">
                <dt>생성</dt>
                <dd>{formatLocalDateTime(version.created_at)}</dd>
              </div>
            </dl>
          </div>
        ) : null}
      </div>
      {isSwitching || catalogState.isResolvingActiveItem ? (
        <div className="active-dataset-operational-row context-status" role="status">
          데이터셋 버전 확인 중
        </div>
      ) : null}
      {catalogState.error !== null ? (
        <div className="active-dataset-operational-row context-bar-error" role="alert">
          데이터셋 목록 조회 실패: {catalogState.error}
          <button className="secondary-button" onClick={catalogState.onRefresh} type="button">
            목록 다시 불러오기
          </button>
        </div>
      ) : null}
      {version === null && pendingVersionId !== null && !isSwitching ? (
        <div className="active-dataset-operational-row">
          <button className="secondary-button" onClick={onRetrySwitch} type="button">
            선택한 데이터셋 다시 불러오기
          </button>
        </div>
      ) : null}
      {catalogState.catalog !== null && catalogState.catalog.total > catalogState.catalog.limit ? (
        <div
          className="active-dataset-operational-row result-pagination"
          aria-label="분석 데이터셋 목록 페이지 이동"
        >
          <button
            disabled={disabled || !catalogState.catalog.has_previous}
            onClick={() =>
              catalogState.onPageChange(
                Math.max(0, catalogState.catalog!.offset - catalogState.catalog!.limit),
              )
            }
            type="button"
          >
            이전
          </button>
          <span>
            {catalogState.catalog.offset + 1}-
            {catalogState.catalog.offset + catalogState.catalog.returned} /{" "}
            {catalogState.catalog.total}
          </span>
          <button
            disabled={disabled || !catalogState.catalog.has_next}
            onClick={() =>
              catalogState.onPageChange(
                catalogState.catalog!.offset + catalogState.catalog!.limit,
              )
            }
            type="button"
          >
            다음
          </button>
        </div>
      ) : null}
    </section>
  );
}

function catalogItemLabel(item: NonNullable<DatasetVersionCatalogState["activeItem"]>) {
  const label = item.user_label ?? item.original_filename;
  return `${label} · ${item.row_count.toLocaleString()}행 · ${item.column_count.toLocaleString()}열 · v${item.version_number} · ${formatLocalDateTime(item.created_at)}`;
}

function currentVersionLabel(version: DatasetVersionResponse) {
  return `데이터셋 v${version.version_number} · ${version.row_count.toLocaleString()}행 · ${version.column_count.toLocaleString()}열 · ${formatLocalDateTime(version.created_at)}`;
}
