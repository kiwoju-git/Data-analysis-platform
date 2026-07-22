import type { DatasetVersionResponse } from "./api";
import { shortHash } from "./datasetDisplay";
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
    catalogState.activeItem !== null && !activeOnCurrentPage
      ? catalogState.activeItem
      : null;
  const disabled = isSwitching || catalogState.isLoading;

  return (
    <section className="context-bar active-dataset-selector" aria-label="데이터셋 컨텍스트">
      <div className="active-dataset-control">
        <label htmlFor="active-dataset-version">
          <span>현재 분석 데이터셋</span>
          <select
            id="active-dataset-version"
            disabled={disabled || catalogState.catalog === null}
            value={selectedVersionId}
            onChange={(event) => onSelect(event.currentTarget.value)}
          >
            <option value="">데이터셋 버전 선택</option>
            {activeOffPage !== null ? (
              <option value={activeOffPage.version_id}>{catalogItemLabel(activeOffPage)}</option>
            ) : null}
            {catalogState.catalog?.versions.map((item) => (
              <option key={item.version_id} value={item.version_id}>
                {catalogItemLabel(item)}
              </option>
            ))}
          </select>
        </label>
        <span className="cell-subtle">
          전환하면 현재 일반 분석 입력과 화면 결과가 새 버전에 맞게 초기화됩니다.
        </span>
      </div>
      {version !== null ? (
        <div className="active-dataset-summary">
          <span>v{version.version_number}</span>
          <span>{version.row_count.toLocaleString()}행</span>
          <span>{version.column_count.toLocaleString()}컬럼</span>
          <span className="hash-text">schema {shortHash(version.schema_hash)}</span>
          <span className="hash-text">ID {shortId(version.version_id)}</span>
        </div>
      ) : null}
      {isSwitching || catalogState.isResolvingActiveItem ? (
        <span role="status">데이터셋 버전 확인 중</span>
      ) : null}
      {catalogState.error !== null ? (
        <div className="context-bar-error" role="alert">
          데이터셋 목록 조회 실패: {catalogState.error}
          <button className="secondary-button" onClick={catalogState.onRefresh} type="button">
            목록 다시 불러오기
          </button>
        </div>
      ) : null}
      {version === null && pendingVersionId !== null && !isSwitching ? (
        <button className="secondary-button" onClick={onRetrySwitch} type="button">
          선택한 데이터셋 다시 불러오기
        </button>
      ) : null}
      {catalogState.catalog !== null && catalogState.catalog.total > catalogState.catalog.limit ? (
        <div className="result-pagination" aria-label="분석 데이터셋 목록 페이지 이동">
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
  const original = item.user_label === null ? "" : ` · ${item.original_filename}`;
  return `${label}${original} · ${item.row_count.toLocaleString()}행 · ${item.column_count.toLocaleString()}열 · v${item.version_number} · ${shortId(item.version_id)}`;
}

function shortId(value: string) {
  return value.length <= 12 ? value : `${value.slice(0, 8)}…`;
}
