import type {
  DatasetProfileResponse,
  DatasetRowsPreviewResponse,
  DatasetVersionResponse,
} from "./api";
import { formatBytes, shortHash } from "./datasetDisplay";
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
  onLoadDatasetProfile,
  onLoadRowsPreview,
  onPreviewLimitChange,
  onSaveSchema,
  onSchemaDraftChange,
}: DatasetVersionPanelProps) {
  return (
    <section className="version-panel" aria-labelledby="version-title">
      <div className="panel-heading">
        <div>
          <h3 id="version-title">Dataset version v{version.version_number}</h3>
          <p>{version.version_id}</p>
        </div>
        <span className="status-pill status-ready">버전 생성됨</span>
      </div>
      <div className="metadata-grid">
        <span>행</span>
        <strong>{version.row_count.toLocaleString()}</strong>
        <span>컬럼</span>
        <strong>{version.column_count.toLocaleString()}</strong>
        <span>Schema hash</span>
        <strong className="hash-text">{version.schema_hash}</strong>
        <span>Canonical</span>
        <strong className="hash-text">
          {version.canonical_artifact === null
            ? "대기"
            : `${shortHash(version.canonical_artifact.sha256)} · ${formatBytes(
                version.canonical_artifact.size_bytes,
              )}`}
        </strong>
      </div>
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
      />
    </section>
  );
}
