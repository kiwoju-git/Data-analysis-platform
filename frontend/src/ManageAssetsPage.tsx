import { useEffect, useRef, useState } from "react";

import type {
  AnalysisRunDeletionPreflightResponse,
  DatasetDeletionOperationId,
  DatasetVersionCatalogItem,
  RegressionModelDependentPredictionDescriptor,
  RegressionModelCatalogItem,
} from "./api";
import {
  deleteStoredAnalysisRun,
  fetchAnalysisRunDeletionPreflight,
} from "./api";
import type { AssetManagementError } from "./assetManagementErrors";
import { formatLocalDateTime } from "./dateFormat";
import { useAssetManagementState } from "./useAssetManagementState";
import { useDatasetVersionRetentionState } from "./useDatasetVersionRetentionState";
import { useRegressionModelRetentionState } from "./useRegressionModelRetentionState";

export interface ManageAssetsPageProps {
  activeDatasetVersionId: string | null;
  onActivateDataset: (versionId: string) => void;
  onAssetsDeleted: () => void;
  onDatasetMetadataChanged: () => void;
}

export function ManageAssetsPage({
  activeDatasetVersionId,
  onActivateDataset,
  onAssetsDeleted,
  onDatasetMetadataChanged,
}: ManageAssetsPageProps) {
  const state = useAssetManagementState();
  const [tab, setTab] = useState<"datasets" | "models">("datasets");

  return (
    <section className="asset-management-page" aria-labelledby="asset-management-title">
      <div className="panel-heading">
        <div>
          <h2 id="asset-management-title">데이터모델 관리</h2>
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
          onAssetsDeleted={onAssetsDeleted}
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
  onAssetsDeleted,
  onDatasetMetadataChanged,
  state,
}: {
  activeDatasetVersionId: string | null;
  onActivateDataset: (versionId: string) => void;
  onAssetsDeleted: () => void;
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
      <div
        className="segmented-control compact-segments"
        role="group"
        aria-label="데이터셋 표시 범위"
      >
        {(
          [
            ["visible", "표시 중"],
            ["archived", "보관됨"],
            ["all", "전체"],
          ] as const
        ).map(([visibility, label]) => (
          <button
            aria-pressed={state.datasetVisibility === visibility}
            className={state.datasetVisibility === visibility ? "segment-active" : ""}
            key={visibility}
            onClick={() => state.onDatasetVisibilityChange(visibility)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>
      {state.datasetLoading ? <p role="status">데이터셋 목록 확인 중</p> : null}
      {state.datasetError !== null ? (
        <AssetManagementErrorNotice error={state.datasetError} />
      ) : null}
      {state.datasetCatalog?.versions.length === 0 ? <div className="empty-state">저장 데이터셋이 없습니다.</div> : null}
      <div className="asset-management-list">
        {state.datasetCatalog?.versions.map((item) => (
          <DatasetAssetEditor
            active={item.version_id === activeDatasetVersionId}
            item={item}
            key={`${item.version_id}-${item.metadata_updated_at ?? "none"}`}
            saved={state.savedId === item.version_id}
            saving={state.savingId === item.version_id}
            onActivate={() => onActivateDataset(item.version_id)}
            onMetadataChanged={onDatasetMetadataChanged}
            onDeleted={() => {
              state.onRefreshDatasets();
              onAssetsDeleted();
            }}
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
  onDeleted,
  onSave,
  saved,
  saving,
}: {
  active: boolean;
  item: DatasetVersionCatalogItem;
  onActivate: () => void;
  onMetadataChanged: () => void;
  onDeleted: () => void;
  onSave: ReturnType<typeof useAssetManagementState>["onSaveDatasetMetadata"];
  saved: boolean;
  saving: boolean;
}) {
  const [label, setLabel] = useState(item.user_label ?? "");
  const [note, setNote] = useState(item.note ?? "");
  const [pinned, setPinned] = useState(item.pinned);
  const [deleteConfirmed, setDeleteConfirmed] = useState(false);
  const [metadataOnlyConfirmed, setMetadataOnlyConfirmed] = useState(false);
  const [cascadeConfirmed, setCascadeConfirmed] = useState(false);
  const [cascadeConfirmationText, setCascadeConfirmationText] = useState("");
  const retention = useDatasetVersionRetentionState(item.version_id, onDeleted);
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
        <span>생성 {formatLocalDateTime(item.created_at)}</span>
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
        {saved ? <span className="field-note" role="status">이름과 메모를 저장했습니다.</span> : null}
        <button
          className="secondary-button"
          disabled={saving || active}
          onClick={() =>
            void onSave(item.version_id, {
              archived: !item.archived,
              expected_metadata_updated_at: item.metadata_updated_at,
            }).then((updated) => {
              if (updated) onMetadataChanged();
            })
          }
          type="button"
        >
          {item.archived ? "다시 표시" : "목록에서 숨기기"}
        </button>
        <button
          className="secondary-button"
          disabled={active || retention.isLoadingPreflight || retention.isDeleting}
          onClick={retention.onLoadPreflight}
          type="button"
        >
          {retention.isLoadingPreflight ? "확인 중" : "삭제 영향 확인"}
        </button>
      </div>
      {active ? (
        <p className="field-note">현재 분석 데이터셋은 삭제할 수 없습니다. 다른 버전을 먼저 선택하세요.</p>
      ) : null}
      {retention.preflight !== null ? (
        <DatasetDeletionImpact
          confirmed={deleteConfirmed}
          item={item}
          preflight={retention.preflight}
          deleting={retention.isDeleting}
          onConfirmedChange={setDeleteConfirmed}
          metadataOnlyConfirmed={metadataOnlyConfirmed}
          cascadeConfirmed={cascadeConfirmed}
          cascadeConfirmationText={cascadeConfirmationText}
          dependencies={retention.dependencies}
          onCascadeConfirmedChange={setCascadeConfirmed}
          onCascadeConfirmationTextChange={setCascadeConfirmationText}
          onMetadataOnlyConfirmedChange={setMetadataOnlyConfirmed}
          onLoadDependencies={retention.onLoadDependencies}
          onDelete={(mode) => retention.onDelete(retention.preflight!, mode)}
        />
      ) : null}
      {retention.error !== null ? (
        <AssetManagementErrorNotice error={retention.error} />
      ) : null}
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
      {state.modelError !== null ? (
        <AssetManagementErrorNotice error={state.modelError} />
      ) : null}
      {state.modelCatalog?.models.length === 0 ? <div className="empty-state">저장 회귀모델이 없습니다.</div> : null}
      <div className="asset-management-list">
        {state.modelCatalog?.models.map((item) => (
          <ModelAssetEditor
            item={item}
            key={`${item.model_id}-${item.metadata_updated_at ?? "none"}`}
            saved={state.savedId === item.model_id}
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
  saved,
  saving,
}: {
  item: RegressionModelCatalogItem;
  onSave: ReturnType<typeof useAssetManagementState>["onSaveModelMetadata"];
  onDeleted: () => void;
  saved: boolean;
  saving: boolean;
}) {
  const [label, setLabel] = useState(item.user_label ?? "");
  const [note, setNote] = useState(item.note ?? "");
  const [pinned, setPinned] = useState(item.pinned);
  const [deleteConfirmed, setDeleteConfirmed] = useState(false);
  const [cascadeConfirmed, setCascadeConfirmed] = useState(false);
  const retention = useRegressionModelRetentionState(item.model_id);
  const deletionNotificationRef = useRef<string | null>(null);
  useEffect(() => {
    if (
      retention.deletion !== null &&
      deletionNotificationRef.current !== retention.deletion.model_id
    ) {
      deletionNotificationRef.current = retention.deletion.model_id;
      onDeleted();
    }
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
        {saved ? <span className="field-note" role="status">관리용 이름과 메모를 저장했습니다.</span> : null}
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
          {retention.preflight.dependent_predictions.length > 0 ? (
            <details>
              <summary>종속 예측 위치와 삭제 작업</summary>
              <div className="asset-dependent-list">
                {retention.preflight.dependent_predictions.map((prediction) => (
                  <DependentPredictionItem
                    key={prediction.analysis_id}
                    prediction={prediction}
                    onDeleted={retention.onLoadPreflight}
                  />
                ))}
              </div>
              {retention.preflight.dependent_predictions_truncated ? (
                <span className="field-note">
                  첫 5건만 표시합니다. 전체 목록은 향후 페이지 탐색 API로 확인할 수 있습니다.
                </span>
              ) : null}
            </details>
          ) : null}
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
            <>
              <span>
                각 예측을 위에서 직접 삭제하거나, 아래에서 모든 종속 예측과 모델을
                원자적으로 함께 삭제할 수 있습니다.
              </span>
              {retention.preflight.cascade_deletion_ready ? (
                <>
                  <label className="checkbox-field">
                    <input
                      checked={cascadeConfirmed}
                      type="checkbox"
                      onChange={(event) =>
                        setCascadeConfirmed(event.currentTarget.checked)
                      }
                    />
                    <span>
                      종속 예측 {retention.preflight.counts.dependent_prediction_count}건과
                      모델을 함께 영구 삭제하는 영향을 확인했습니다.
                    </span>
                  </label>
                  <button
                    className="danger-button"
                    disabled={!cascadeConfirmed || retention.isDeleting}
                    onClick={() =>
                      retention.onDelete(retention.preflight!, "model_and_predictions")
                    }
                    type="button"
                  >
                    {retention.isDeleting ? "삭제 중" : "예측과 모델 함께 삭제"}
                  </button>
                </>
              ) : (
                <span className="field-note">
                  종속 예측 중 검증되지 않았거나 삭제 blocker가 있는 항목이 있어 일괄
                  삭제할 수 없습니다.
                </span>
              )}
            </>
          )}
        </div>
      ) : null}
      {retention.errorDetail !== null ? (
        <AssetManagementErrorNotice error={retention.errorDetail} />
      ) : null}
    </article>
  );
}

function DependentPredictionItem({
  onDeleted,
  prediction,
}: {
  onDeleted: () => void;
  prediction: RegressionModelDependentPredictionDescriptor;
}) {
  const [preflight, setPreflight] =
    useState<AnalysisRunDeletionPreflightResponse | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPreflight = () => {
    setBusy(true);
    setError(null);
    void fetchAnalysisRunDeletionPreflight(prediction.analysis_id)
      .then(setPreflight)
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : "analysis_run_deletion_preflight_failed",
        ),
      )
      .finally(() => setBusy(false));
  };
  const deletePrediction = () => {
    if (preflight === null || !preflight.deletion_ready || !confirmed) return;
    setBusy(true);
    setError(null);
    void deleteStoredAnalysisRun(prediction.analysis_id, {
      confirmation_analysis_id: prediction.analysis_id,
      expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
    })
      .then(() => {
        setPreflight(null);
        onDeleted();
      })
      .catch((requestError) =>
        setError(
          requestError instanceof Error
            ? requestError.message
            : "analysis_run_delete_failed",
        ),
      )
      .finally(() => setBusy(false));
  };

  return (
    <article className="asset-dependent-item">
      <div>
        <strong>{prediction.target_dataset_display_name}</strong>
        <span>
          {formatLocalDateTime(prediction.created_at)} · 전체{" "}
          {prediction.row_count_total.toLocaleString()}행 · 예측{" "}
          {prediction.row_count_predicted.toLocaleString()}행
        </span>
        <span>
          {prediction.stale ? "stale" : "current"} · ID {shortId(prediction.analysis_id)}
        </span>
      </div>
      <div className="button-row">
        <a
          className="secondary-button link-button"
          href={`/reports?tab=reports&method_id=regression.predict&analysis_id=${encodeURIComponent(prediction.analysis_id)}`}
        >
          리포트에서 열기
        </a>
        <button
          className="secondary-button"
          disabled={busy}
          onClick={loadPreflight}
          type="button"
        >
          {busy ? "확인 중" : "삭제 영향 확인"}
        </button>
      </div>
      {preflight !== null ? (
        preflight.deletion_ready ? (
          <>
            <label className="checkbox-field">
              <input
                checked={confirmed}
                type="checkbox"
                onChange={(event) => setConfirmed(event.currentTarget.checked)}
              />
              <span>이 예측 결과만 영구 삭제합니다.</span>
            </label>
            <button
              className="danger-button"
              disabled={busy || !confirmed}
              onClick={deletePrediction}
              type="button"
            >
              예측 결과 삭제
            </button>
          </>
        ) : (
          <span className="field-note">
            blocker: {preflight.blockers.join(", ")}
          </span>
        )
      ) : null}
      {error !== null ? <span className="error-text">{error}</span> : null}
    </article>
  );
}

export function DatasetDeletionImpact({
  cascadeConfirmed,
  cascadeConfirmationText,
  confirmed,
  dependencies,
  deleting,
  item,
  metadataOnlyConfirmed,
  onCascadeConfirmedChange,
  onCascadeConfirmationTextChange,
  onConfirmedChange,
  onDelete,
  onLoadDependencies,
  onMetadataOnlyConfirmedChange,
  preflight,
}: {
  cascadeConfirmed: boolean;
  cascadeConfirmationText: string;
  confirmed: boolean;
  dependencies: import("./api").DatasetDeletionDependencyPage | null;
  deleting: boolean;
  item: DatasetVersionCatalogItem;
  metadataOnlyConfirmed: boolean;
  onCascadeConfirmedChange: (confirmed: boolean) => void;
  onCascadeConfirmationTextChange: (value: string) => void;
  onConfirmedChange: (confirmed: boolean) => void;
  onDelete: (operationId: DatasetDeletionOperationId) => void;
  onLoadDependencies: (
    assetType: import("./api").DatasetDeletionDependencyAssetType | null,
    offset?: number,
  ) => void;
  onMetadataOnlyConfirmedChange: (confirmed: boolean) => void;
  preflight: import("./api").DatasetVersionDeletionPreflightResponse;
}) {
  const counts = preflight.counts;
  const dependencyTotal =
    counts.analysis_run_count +
    counts.regression_model_count +
    counts.prediction_source_count +
    counts.prediction_target_count +
    counts.analysis_export_count +
    counts.attribute_control_limit_set_count +
    counts.phase_2_analysis_count +
    counts.job_count;
  const operation = (id: DatasetDeletionOperationId) =>
    preflight.available_operations.find((candidate) => candidate.operation_id === id);
  const verified = operation("delete_dataset_verified");
  const metadataOnly = operation("remove_dataset_metadata_preserve_files");
  const cascadeVerified = operation("delete_dataset_and_dependents_verified");
  const cascadePreserve = operation(
    "delete_dataset_and_dependents_preserve_unverified",
  );
  const selectedCascade =
    cascadeVerified?.ready === true ? cascadeVerified : cascadePreserve;
  const expectedConfirmationValues = [
    shortId(item.version_id),
    item.user_label?.trim(),
  ].filter((value): value is string => Boolean(value));
  const cascadeTextMatches = expectedConfirmationValues.includes(
    cascadeConfirmationText.trim(),
  );
  return (
    <div className="notice-box dataset-deletion-impact">
      <strong>삭제 영향</strong>
      <div className="metadata-grid">
        <span>분석 {counts.analysis_run_count.toLocaleString()}건</span>
        <span>모델 {counts.regression_model_count.toLocaleString()}건</span>
        <span>예측 {counts.prediction_source_count + counts.prediction_target_count}건</span>
        <span>내보내기 {counts.analysis_export_count.toLocaleString()}건</span>
        <span>관리한계 {counts.attribute_control_limit_set_count.toLocaleString()}건</span>
        <span>Phase II {counts.phase_2_analysis_count.toLocaleString()}건</span>
        <span>job {counts.job_count.toLocaleString()}건</span>
        <span>다른 버전 {counts.sibling_version_count.toLocaleString()}개</span>
      </div>
      {preflight.integrity_issue_codes.length > 0 ? (
        <div className="warning-box">
          <strong>{integrityIssueTitle(preflight.integrity_issue_codes[0])}</strong>
          <p>{integrityIssueDescription(preflight.integrity_issue_codes[0])}</p>
          <p>내부 경로나 파일 내용은 표시하지 않습니다.</p>
        </div>
      ) : null}
      {preflight.dependency_preview.length > 0 ? (
        <details
          onToggle={(event) => {
            if (event.currentTarget.open && dependencies === null) {
              onLoadDependencies(null, 0);
            }
          }}
        >
          <summary>연결 자산 {dependencyTotal.toLocaleString()}건 보기</summary>
          <ul className="asset-dependency-list">
            {(dependencies?.dependencies ?? preflight.dependency_preview).map(
              (dependency) => (
                <li key={`${dependency.asset_type}:${dependency.asset_id}`}>
                  <strong>{dependency.display_name}</strong>
                  <span>{dependencyLabel(dependency.asset_type)}</span>
                  {dependency.related_dataset_version_id !== null &&
                  dependency.related_dataset_version_id !== item.version_id ? (
                    <span>다른 데이터셋의 결과도 함께 삭제됩니다.</span>
                  ) : null}
                </li>
              ),
            )}
          </ul>
          {dependencies?.has_next ? (
            <button
              className="secondary-button"
              onClick={() =>
                onLoadDependencies(null, dependencies.offset + dependencies.limit)
              }
              type="button"
            >
              다음 연결 자산
            </button>
          ) : null}
        </details>
      ) : null}
      {verified?.ready ? (
        <>
          <p>
            {preflight.deletion_scope === "dataset_root"
              ? "마지막 버전이므로 검증된 원본 업로드와 dataset root도 함께 삭제됩니다."
              : "이 버전의 검증된 canonical/profile 파일만 삭제되고 shared 원본은 유지됩니다."}
          </p>
          <label className="checkbox-field">
            <input
              checked={confirmed}
              type="checkbox"
              onChange={(event) => onConfirmedChange(event.currentTarget.checked)}
            />
            <span>
              {item.user_label ?? item.original_filename} · {item.row_count.toLocaleString()}행 · ID {shortId(item.version_id)} 삭제가 되돌릴 수 없음을 확인했습니다.
            </span>
          </label>
          <button
            className="secondary-button danger-button"
            disabled={!confirmed || deleting}
            onClick={() => onDelete("delete_dataset_verified")}
            type="button"
          >
            {deleting ? "삭제 중" : "데이터셋 버전 삭제"}
          </button>
        </>
      ) : metadataOnly?.ready ? (
        <>
          <strong>파일 검증 실패 · 목록에서만 안전하게 정리 가능</strong>
          <p>
            저장 경로나 checksum을 확인할 수 없어 실제 파일은 삭제하지 않습니다.
            데이터셋 메타데이터만 제거하며 최대{" "}
            {preflight.preserved_unverified_file_count.toLocaleString()}개 파일이 디스크에
            남을 수 있습니다.
          </p>
          <label className="checkbox-field">
            <input
              checked={metadataOnlyConfirmed}
              type="checkbox"
              onChange={(event) =>
                onMetadataOnlyConfirmedChange(event.currentTarget.checked)
              }
            />
            <span>검증되지 않은 파일을 보존하고 목록에서만 제거하는 것을 확인했습니다.</span>
          </label>
          <button
            className="secondary-button danger-button"
            disabled={!metadataOnlyConfirmed || deleting}
            onClick={() => onDelete("remove_dataset_metadata_preserve_files")}
            type="button"
          >
            {deleting ? "정리 중" : "파일을 보존하고 목록에서 제거"}
          </button>
        </>
      ) : null}
      {dependencyTotal > 0 && selectedCascade?.ready ? (
        <div className="danger-zone">
          <strong>연결 자산과 데이터셋 모두 영구 삭제</strong>
          <p>
            분석·리포트·모델·예측 등 연결 자산{" "}
            {selectedCascade.affected_asset_count.toLocaleString()}건을 하나의 원자적
            작업으로 삭제합니다. 다른 데이터셋 자체는 삭제하지 않습니다.
          </p>
          {selectedCascade.unverified_file_policy === "preserve" ? (
            <p>
              검증하지 못한 파일{" "}
              {selectedCascade.preserved_unverified_file_count.toLocaleString()}개는 열거나
              이동하지 않고 디스크에 보존합니다.
            </p>
          ) : null}
          <label className="checkbox-field">
            <input
              checked={cascadeConfirmed}
              onChange={(event) =>
                onCascadeConfirmedChange(event.currentTarget.checked)
              }
              type="checkbox"
            />
            <span>
              연결된 자산 {selectedCascade.affected_asset_count.toLocaleString()}건도 함께
              영구 삭제되는 것을 확인했습니다.
            </span>
          </label>
          <label>
            <span>
              확인을 위해 {item.user_label ? "데이터셋 이름 또는 " : ""}
              짧은 ID <strong>{shortId(item.version_id)}</strong> 입력
            </span>
            <input
              aria-label="데이터셋 cascade 삭제 확인"
              value={cascadeConfirmationText}
              onChange={(event) =>
                onCascadeConfirmationTextChange(event.currentTarget.value)
              }
            />
          </label>
          <button
            className="danger-button"
            disabled={!cascadeConfirmed || !cascadeTextMatches || deleting}
            onClick={() => onDelete(selectedCascade.operation_id)}
            type="button"
          >
            {deleting
              ? "삭제 중"
              : `연결 자산 ${selectedCascade.affected_asset_count.toLocaleString()}건과 데이터셋 모두 삭제`}
          </button>
        </div>
      ) : dependencyTotal > 0 ? (
        <p>
          연결 자산을 포함한 안전한 삭제 계획을 만들 수 없습니다. blocker:{" "}
          {[
            ...(cascadeVerified?.blockers ?? []),
            ...(cascadePreserve?.blockers ?? []),
          ]
            .filter((value, index, all) => all.indexOf(value) === index)
            .join(", ")}
        </p>
      ) : null}
    </div>
  );
}

function integrityIssueTitle(code: string): string {
  if (code === "dataset_version_path_invalid") return "저장 경로 검증 실패";
  if (code === "dataset_version_artifact_mismatch") return "저장 파일 무결성 불일치";
  if (code === "dataset_version_file_missing") return "저장 파일 누락";
  return "저장 자산 무결성 확인 필요";
}

function integrityIssueDescription(code: string): string {
  if (code === "dataset_version_path_invalid") {
    return "일부 저장 위치 정보가 안전한 workspace 규칙과 일치하지 않습니다. 외부 파일을 잘못 삭제하지 않도록 물리 파일 삭제를 중단했습니다.";
  }
  if (code === "dataset_version_artifact_mismatch") {
    return "저장 파일의 크기 또는 checksum이 등록 당시 정보와 다릅니다.";
  }
  if (code === "dataset_version_file_missing") {
    return "등록된 저장 파일 중 일부를 찾을 수 없습니다.";
  }
  return "검증되지 않은 파일은 삭제하지 않고 보존합니다.";
}

function dependencyLabel(
  assetType: import("./api").DatasetDeletionDependencyAssetType,
): string {
  const labels: Record<
    import("./api").DatasetDeletionDependencyAssetType,
    string
  > = {
    analysis_run: "분석 결과",
    regression_model: "회귀모델",
    prediction: "예측 결과",
    analysis_export: "리포트/내보내기",
    attribute_control_limit_set: "관리한계",
    phase_2_analysis: "Phase II 분석",
    job: "Job 기록",
  };
  return labels[assetType];
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

function AssetManagementErrorNotice({ error }: { error: AssetManagementError }) {
  return (
    <div className="error-box asset-management-error" role="alert">
      <strong>{error.title}</strong>
      <p>{error.message}</p>
      <span className="field-note">오류 코드: {error.code}</span>
      {error.correlationId !== null ? (
        <span className="field-note">요청 ID: {error.correlationId}</span>
      ) : null}
    </div>
  );
}
