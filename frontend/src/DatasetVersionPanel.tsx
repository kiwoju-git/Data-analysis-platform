import type {
  DatasetProfileResponse,
  DatasetCellCorrectionRequest,
  DatasetCellCorrectionResponse,
  DatasetRowsPreviewResponse,
  DatasetVersionResponse,
} from "./api";
import { formatBytes, shortHash } from "./datasetDisplay";
import { formatLocalDateTime } from "./dateFormat";
import { DatasetPreviewSection } from "./DatasetPreviewSection";
import { DatasetProfileSection } from "./DatasetProfileSection";
import { DatasetSchemaSection } from "./DatasetSchemaSection";
import type { SchemaDraftPatch } from "./datasetPreparationTypes";
import type { SchemaDraft } from "./schemaPresets";

interface DatasetVersionPanelProps {
  canApplyBayesianPreset: boolean;
  isLoadingPreview: boolean;
  isLoadingProfile: boolean;
  isSavingSchema: boolean;
  preview: DatasetRowsPreviewResponse | null;
  previewLimit: number;
  previewOffset: number;
  profile: DatasetProfileResponse | null;
  schemaDrafts: SchemaDraft[];
  version: DatasetVersionResponse;
  onApplyBayesianPreset: () => void;
  onCreateCellCorrection: (
    request: DatasetCellCorrectionRequest,
  ) => Promise<DatasetCellCorrectionResponse>;
  onCellEditDirtyChange: (dirty: boolean) => void;
  onLoadDatasetProfile: (versionId: string) => void;
  onLoadRowsPreview: (versionId: string, offset: number) => void;
  onPreviewLimitChange: (limit: number) => void;
  onSaveSchema: () => void;
  onSchemaDraftChange: (columnId: string, patch: SchemaDraftPatch) => void;
}

export function DatasetVersionPanel({
  canApplyBayesianPreset,
  isLoadingPreview,
  isLoadingProfile,
  isSavingSchema,
  preview,
  previewLimit,
  previewOffset,
  profile,
  schemaDrafts,
  version,
  onApplyBayesianPreset,
  onCreateCellCorrection,
  onCellEditDirtyChange,
  onLoadDatasetProfile,
  onLoadRowsPreview,
  onPreviewLimitChange,
  onSaveSchema,
  onSchemaDraftChange,
}: DatasetVersionPanelProps) {
  const createdAt = formatCreatedAt(version.created_at);

  return (
    <section
      className="version-panel"
      id="dataset-version"
      aria-labelledby="version-title"
      tabIndex={-1}
    >
      <div className="panel-heading">
        <div>
          <h3 id="version-title">데이터셋 v{version.version_number}</h3>
          <p>
            {version.row_count.toLocaleString()}행 · {version.column_count.toLocaleString()}열
            {createdAt === null ? "" : ` · 생성 ${createdAt}`}
          </p>
          {version.parent_version_id !== null ? (
            <p>
              v{Math.max(1, version.version_number - 1)}에서 셀{" "}
              {version.lineage_affected_cell_count ?? 1}건을 수정해 생성됨
            </p>
          ) : null}
        </div>
        <span className="status-pill status-ready">버전 생성됨</span>
      </div>
      <details className="dataset-technical-details">
        <summary>기술 정보 펼치기</summary>
        <dl className="dataset-technical-list">
          <div>
            <dt>Version ID</dt>
            <dd className="hash-text">{version.version_id}</dd>
          </div>
          <div>
            <dt>Dataset ID</dt>
            <dd className="hash-text">{version.dataset_id}</dd>
          </div>
          <div>
            <dt>Schema hash</dt>
            <dd className="hash-text">{version.schema_hash}</dd>
          </div>
          <div>
            <dt>Source SHA-256</dt>
            <dd className="hash-text">{version.source_sha256}</dd>
          </div>
          <div>
            <dt>Canonical artifact</dt>
            <dd className="hash-text">
              {version.canonical_artifact === null
                ? "없음"
                : `${shortHash(version.canonical_artifact.sha256)} · ${formatBytes(
                    version.canonical_artifact.size_bytes,
                  )}`}
            </dd>
          </div>
          {profile?.profile_artifact !== null && profile !== null ? (
            <div>
              <dt>Profile artifact</dt>
              <dd className="hash-text">
                {shortHash(profile.profile_artifact.sha256)} ·{" "}
                {formatBytes(profile.profile_artifact.size_bytes)}
              </dd>
            </div>
          ) : null}
          {profile !== null ? (
            <div>
              <dt>예상 메모리</dt>
              <dd>{formatBytes(profile.preflight.estimated_memory_bytes)}</dd>
            </div>
          ) : null}
        </dl>
      </details>
      <DatasetProfileSection
        isLoadingProfile={isLoadingProfile}
        profile={profile}
        versionId={version.version_id}
        onLoadDatasetProfile={onLoadDatasetProfile}
      />
      <DatasetSchemaSection
        canApplyBayesianPreset={canApplyBayesianPreset}
        isSavingSchema={isSavingSchema}
        schemaDrafts={schemaDrafts}
        version={version}
        onApplyBayesianPreset={onApplyBayesianPreset}
        onSaveSchema={onSaveSchema}
        onSchemaDraftChange={onSchemaDraftChange}
      />
      <DatasetPreviewSection
        isLoadingPreview={isLoadingPreview}
        preview={preview}
        previewLimit={previewLimit}
        previewOffset={previewOffset}
        version={version}
        onLoadRowsPreview={onLoadRowsPreview}
        onPreviewLimitChange={onPreviewLimitChange}
        onCreateCellCorrection={onCreateCellCorrection}
        onDirtyChange={onCellEditDirtyChange}
      />
    </section>
  );
}

function formatCreatedAt(value: string): string | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return formatLocalDateTime(value);
}
