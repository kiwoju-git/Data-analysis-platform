import { useEffect, useState } from "react";

import type {
  DatasetVersionCatalogItem,
  RegressionModelCatalogItem,
} from "./api";
import { useAssetManagementState } from "./useAssetManagementState";
import { useRegressionModelRetentionState } from "./useRegressionModelRetentionState";

export interface ManageAssetsPageProps {
  activeDatasetVersionId: string | null;
  onActivateDataset: (versionId: string) => void;
  onDatasetMetadataChanged: () => void;
}

export function ManageAssetsPage({
  activeDatasetVersionId,
  onActivateDataset,
  onDatasetMetadataChanged,
}: ManageAssetsPageProps) {
  const state = useAssetManagementState();
  const [tab, setTab] = useState<"datasets" | "models">("datasets");

  return (
    <section className="asset-management-page" aria-labelledby="asset-management-title">
      <div className="panel-heading">
        <div>
          <h2 id="asset-management-title">데이터·모델 관리</h2>
          <p>로컬에 저장된 데이터셋 버전과 회귀모델의 이름, 메모, 고정 상태를 관리합니다.</p>
        </div>
        <span className="status-pill status-ready">로컬 저장됨</span>
      </div>
      <div className="segmented-control" role="tablist" aria-label="관리 자산 종류">
        <button
          aria-selected={tab === "datasets"}
          className={tab === "datasets" ? "segment-active" : ""}
          onClick={() => setTab("datasets")}
          role="tab"
          type="button"
        >
          데이터셋
        </button>
        <button
          aria-selected={tab === "models"}
          className={tab === "models" ? "segment-active" : ""}
          onClick={() => setTab("models")}
          role="tab"
          type="button"
        >
          회귀모델
        </button>
      </div>
      {tab === "datasets" ? (
        <DatasetManagementPanel
          activeDatasetVersionId={activeDatasetVersionId}
          state={state}
          onActivateDataset={onActivateDataset}
          onDatasetMetadataChanged={onDatasetMetadataChanged}
        />
      ) : (
        <RegressionModelManagementPanel state={state} />
      )}
    </section>
  );
}

function DatasetManagementPanel({
  activeDatasetVersionId,
  onActivateDataset,
  onDatasetMetadataChanged,
  state,
}: {
  activeDatasetVersionId: string | null;
  onActivateDataset: (versionId: string) => void;
  onDatasetMetadataChanged: () => void;
  state: ReturnType<typeof useAssetManagementState>;
}) {
  return (
    <section aria-labelledby="dataset-management-title">
      <div className="panel-heading compact-heading">
        <div>
          <h3 id="dataset-management-title">저장 데이터셋 버전</h3>
          <p>확정된 버전은 자동 저장되며 이름 변경은 데이터나 schema hash를 수정하지 않습니다.</p>
        </div>
        <button className="secondary-button" onClick={state.onRefreshDatasets} type="button">
          목록 새로고침
        </button>
      </div>
      {state.datasetLoading ? <p role="status">데이터셋 목록 확인 중</p> : null}
      {state.datasetError !== null ? <div className="error-box" role="alert">{state.datasetError}</div> : null}
      {state.datasetCatalog?.versions.length === 0 ? <div className="empty-state">저장 데이터셋이 없습니다.</div> : null}
      <div className="asset-management-list">
        {state.datasetCatalog?.versions.map((item) => (
          <DatasetAssetEditor
            active={item.version_id === activeDatasetVersionId}
            item={item}
            key={`${item.version_id}-${item.metadata_updated_at ?? "none"}`}
            saving={state.savingId === item.version_id}
            onActivate={() => onActivateDataset(item.version_id)}
            onMetadataChanged={onDatasetMetadataChanged}
            onSave={state.onSaveDatasetMetadata}
          />
        ))}
      </div>
      <Pagination
        catalog={state.datasetCatalog}
        disabled={state.datasetLoading}
        onPageChange={state.onDatasetPageChange}
      />
    </section>
  );
}

function DatasetAssetEditor({
  active,
  item,
  onActivate,
  onMetadataChanged,
  onSave,
  saving,
}: {
  active: boolean;
  item: DatasetVersionCatalogItem;
  onActivate: () => void;
  onMetadataChanged: () => void;
  onSave: ReturnType<typeof useAssetManagementState>["onSaveDatasetMetadata"];
  saving: boolean;
}) {
  const [label, setLabel] = useState(item.user_label ?? "");
  const [note, setNote] = useState(item.note ?? "");
  const [pinned, setPinned] = useState(item.pinned);
  return (
    <article className="asset-management-item">
      <div className="asset-management-summary">
        <div>
          <strong>{item.user_label ?? item.original_filename}</strong>
          <span>{item.original_filename}</span>
        </div>
        <span className={active ? "status-pill status-ready" : "status-pill"}>
          {active ? "현재 분석 데이터셋" : "로컬 저장됨"}
        </span>
      </div>
      <div className="metadata-grid">
        <span>{item.row_count.toLocaleString()}행</span>
        <span>{item.column_count.toLocaleString()}열</span>
        <span>v{item.version_number}</span>
        <span>ID {shortId(item.version_id)}</span>
      </div>
      <AssetMetadataFields
        label={label}
        note={note}
        pinned={pinned}
        onLabelChange={setLabel}
        onNoteChange={setNote}
        onPinnedChange={setPinned}
      />
      <div className="button-row">
        <button className="secondary-button" disabled={active} onClick={onActivate} type="button">
          현재 분석 데이터셋으로 사용
        </button>
        <button
          className="primary-button"
          disabled={saving}
          onClick={() => void onSave(item.version_id, {
            user_label: label,
            note,
            pinned,
            expected_metadata_updated_at: item.metadata_updated_at,
          }).then((saved) => {
            if (saved) onMetadataChanged();
          })}
          type="button"
        >
          {saving ? "저장 중" : "이름 저장"}
        </button>
      </div>
    </article>
  );
}

function RegressionModelManagementPanel({
  state,
}: {
  state: ReturnType<typeof useAssetManagementState>;
}) {
  return (
    <section aria-labelledby="model-management-title">
      <div className="panel-heading compact-heading">
        <div>
          <h3 id="model-management-title">저장 회귀모델</h3>
          <p>회귀모형 적합 성공 시 모델은 자동 저장됩니다. 이름 변경은 manifest를 다시 쓰지 않습니다.</p>
        </div>
        <button className="secondary-button" onClick={state.onRefreshModels} type="button">
          모델 상태 다시 확인
        </button>
      </div>
      {state.modelLoading ? <p role="status">회귀모델 목록 확인 중</p> : null}
      {state.modelError !== null ? <div className="error-box" role="alert">{state.modelError}</div> : null}
      {state.modelCatalog?.models.length === 0 ? <div className="empty-state">저장 회귀모델이 없습니다.</div> : null}
      <div className="asset-management-list">
        {state.modelCatalog?.models.map((item) => (
          <ModelAssetEditor
            item={item}
            key={`${item.model_id}-${item.metadata_updated_at ?? "none"}`}
            saving={state.savingId === item.model_id}
            onSave={state.onSaveModelMetadata}
            onDeleted={state.onRefreshModels}
          />
        ))}
      </div>
      <Pagination
        catalog={state.modelCatalog}
        disabled={state.modelLoading}
        onPageChange={state.onModelPageChange}
      />
    </section>
  );
}

function ModelAssetEditor({
  item,
  onSave,
  onDeleted,
  saving,
}: {
  item: RegressionModelCatalogItem;
  onSave: ReturnType<typeof useAssetManagementState>["onSaveModelMetadata"];
  onDeleted: () => void;
  saving: boolean;
}) {
  const [label, setLabel] = useState(item.user_label ?? "");
  const [note, setNote] = useState(item.note ?? "");
  const [pinned, setPinned] = useState(item.pinned);
  const [deleteConfirmed, setDeleteConfirmed] = useState(false);
  const retention = useRegressionModelRetentionState(item.model_id);
  useEffect(() => {
    if (retention.deletion !== null) onDeleted();
  }, [onDeleted, retention.deletion]);
  const fallback = `${item.response?.display_name ?? "반응 metadata 확인 필요"} · predictor ${item.predictor_count ?? "?"}개`;
  return (
    <article className="asset-management-item">
      <div className="asset-management-summary">
        <div>
          <strong>{item.user_label ?? fallback}</strong>
          <span>source {shortId(item.source_dataset_version_id)} · analysis {shortId(item.source_analysis_id)}</span>
        </div>
        <span className="status-pill">{availabilityLabel(item.availability)}</span>
      </div>
      <div className="metadata-grid">
        <span>{item.method_id}</span>
        <span>v{item.method_version}</span>
        <span>{item.predictor_count ?? "?"} predictors</span>
        <span>ID {shortId(item.model_id)}</span>
      </div>
      <AssetMetadataFields
        label={label}
        note={note}
        pinned={pinned}
        onLabelChange={setLabel}
        onNoteChange={setNote}
        onPinnedChange={setPinned}
      />
      <div className="button-row">
        <a className="secondary-button link-button" href={`/analysis/regression/regression.predict?model_id=${encodeURIComponent(item.model_id)}`}>
          Predict에서 열기
        </a>
        <button
          className="primary-button"
          disabled={saving}
          onClick={() => void onSave(item.model_id, {
            user_label: label,
            note,
            pinned,
            expected_metadata_updated_at: item.metadata_updated_at,
          })}
          type="button"
        >
          {saving ? "저장 중" : "이름 저장"}
        </button>
        <button
          className="secondary-button"
          disabled={retention.isLoadingPreflight || retention.isDeleting}
          onClick={retention.onLoadPreflight}
          type="button"
        >
          {retention.isLoadingPreflight ? "확인 중" : "삭제 영향 확인"}
        </button>
      </div>
      {retention.preflight !== null ? (
        <div className="notice-box">
          <span>
            종속 예측 {retention.preflight.counts.dependent_prediction_count.toLocaleString()}건
          </span>
          {retention.preflight.deletion_ready ? (
            <>
              <label className="checkbox-field">
                <input
                  checked={deleteConfirmed}
                  type="checkbox"
                  onChange={(event) => setDeleteConfirmed(event.currentTarget.checked)}
                />
                <span>예측용 모델 자산 삭제가 되돌릴 수 없음을 확인했습니다.</span>
              </label>
              <button
                className="secondary-button"
                disabled={!deleteConfirmed || retention.isDeleting}
                onClick={() => retention.onDelete(retention.preflight!)}
                type="button"
              >
                {retention.isDeleting ? "삭제 중" : "모델 삭제"}
              </button>
            </>
          ) : (
            <span>종속 예측 결과를 먼저 삭제해야 합니다.</span>
          )}
        </div>
      ) : null}
      {retention.error !== null ? <div className="error-box" role="alert">{retention.error}</div> : null}
    </article>
  );
}

function AssetMetadataFields({
  label,
  note,
  onLabelChange,
  onNoteChange,
  onPinnedChange,
  pinned,
}: {
  label: string;
  note: string;
  onLabelChange: (value: string) => void;
  onNoteChange: (value: string) => void;
  onPinnedChange: (value: boolean) => void;
  pinned: boolean;
}) {
  return (
    <div className="asset-metadata-fields">
      <label><span>이름</span><input maxLength={120} value={label} onChange={(event) => onLabelChange(event.currentTarget.value)} /></label>
      <label><span>메모</span><textarea maxLength={500} value={note} onChange={(event) => onNoteChange(event.currentTarget.value)} /></label>
      <label className="checkbox-field"><input checked={pinned} type="checkbox" onChange={(event) => onPinnedChange(event.currentTarget.checked)} /><span>목록 위에 고정</span></label>
    </div>
  );
}

function Pagination({ catalog, disabled, onPageChange }: {
  catalog: { offset: number; limit: number; total: number; returned: number; has_previous: boolean; has_next: boolean } | null;
  disabled: boolean;
  onPageChange: (offset: number) => void;
}) {
  if (catalog === null || catalog.total <= catalog.limit) return null;
  return <div className="result-pagination"><button disabled={disabled || !catalog.has_previous} onClick={() => onPageChange(Math.max(0, catalog.offset - catalog.limit))} type="button">이전</button><span>{catalog.offset + 1}-{catalog.offset + catalog.returned} / {catalog.total}</span><button disabled={disabled || !catalog.has_next} onClick={() => onPageChange(catalog.offset + catalog.limit)} type="button">다음</button></div>;
}

function shortId(value: string) {
  return value.length <= 12 ? value : `${value.slice(0, 8)}…`;
}

function availabilityLabel(value: RegressionModelCatalogItem["availability"]) {
  if (value === "available") return "사용 가능";
  if (value === "source_stale") return "source stale";
  return "무결성 오류";
}
