import type { ChangeEvent, FormEvent } from "react";

import type {
  ConfirmedParsingOptions,
  DatasetProfileResponse,
  DatasetRowsPreviewResponse,
  DatasetUploadResponse,
  DatasetVersionResponse,
} from "./api";
import { ParsingConfirmationPanel } from "./DatasetParsingPanel";
import { DatasetVersionPanel } from "./DatasetVersionPanel";
import type { SchemaDraftPatch } from "./datasetPreparationTypes";
import { PasteDatasetPanel } from "./PasteDatasetPanel";
import type { SchemaDraft } from "./schemaPresets";

export interface DatasetPreparationPageProps {
  canApplyBayesianPreset: boolean;
  canConfirm: boolean;
  delimiterOptions: string[];
  flowError: string | null;
  isConfirming: boolean;
  isLoadingPreview: boolean;
  isLoadingProfile: boolean;
  isPastingDataset: boolean;
  isSavingSchema: boolean;
  isUploading: boolean;
  parsingOptions: ConfirmedParsingOptions | null;
  pastedHeaderPreference: boolean | null;
  preview: DatasetRowsPreviewResponse | null;
  previewLimit: number;
  previewOffset: number;
  profile: DatasetProfileResponse | null;
  schemaDrafts: SchemaDraft[];
  selectedFile: File | null;
  upload: DatasetUploadResponse | null;
  version: DatasetVersionResponse | null;
  onApplyBayesianPreset: () => void;
  onConfirmParsing: () => void;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onLoadDatasetProfile: (versionId: string) => void;
  onLoadRowsPreview: (versionId: string, offset: number) => void;
  onParsingOptionsChange: (options: ConfirmedParsingOptions) => void;
  onPasteDataset: (content: string, previewHasHeader: boolean) => Promise<boolean>;
  onPreviewLimitChange: (limit: number) => void;
  onSaveSchema: () => void;
  onSchemaDraftChange: (columnId: string, patch: SchemaDraftPatch) => void;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
}

const workflowSteps = [
  ["업로드", "CSV, TSV, XLSX 원본을 보존하고 해시와 파싱 옵션을 기록합니다."],
  ["파싱 확정", "인코딩, 구분자, 헤더 유무, 데이터 시작 행, 결측 토큰을 명시적으로 저장합니다."],
  ["스키마 확인", "표시명, 측정 수준, 역할, 단위를 명시적으로 저장합니다."],
  ["미리보기", "서버 페이지네이션으로 현재 행 범위만 불러옵니다."],
] as const;

export function DatasetPreparationPage({
  canApplyBayesianPreset,
  canConfirm,
  delimiterOptions,
  flowError,
  isConfirming,
  isLoadingPreview,
  isLoadingProfile,
  isPastingDataset,
  isSavingSchema,
  isUploading,
  parsingOptions,
  pastedHeaderPreference,
  preview,
  previewLimit,
  previewOffset,
  profile,
  schemaDrafts,
  selectedFile,
  upload,
  version,
  onApplyBayesianPreset,
  onConfirmParsing,
  onFileChange,
  onLoadDatasetProfile,
  onLoadRowsPreview,
  onParsingOptionsChange,
  onPasteDataset,
  onPreviewLimitChange,
  onSaveSchema,
  onSchemaDraftChange,
  onUpload,
}: DatasetPreparationPageProps) {
  return (
    <>
      <div className="section">
        <h2 id="workspace-title">데이터셋 파싱 확정</h2>
        <p>
          Gate B0에서는 원본 업로드를 불변 데이터셋 버전으로 확정하고, 스키마와 행
          미리보기를 서버 페이지 단위로 확인합니다.
        </p>
      </div>
      <form
        className="upload-panel"
        onSubmit={(event) => {
          onUpload(event);
        }}
      >
        <label className="file-control">
          <span>원본 데이터 파일</span>
          <input accept=".csv,.tsv,.txt,.xlsx" onChange={onFileChange} type="file" />
        </label>
        <button
          className="primary-button"
          disabled={selectedFile === null || isUploading}
          type="submit"
        >
          {isUploading ? "업로드 중" : "업로드"}
        </button>
      </form>
      <PasteDatasetPanel isSubmitting={isPastingDataset} onRegister={onPasteDataset} />
      {flowError !== null ? (
        <div className="error-box" role="alert">
          오류 코드: {flowError}
        </div>
      ) : null}
      {upload !== null && parsingOptions !== null ? (
        <ParsingConfirmationPanel
          canConfirm={canConfirm}
          delimiterOptions={delimiterOptions}
          isConfirming={isConfirming}
          parsingOptions={parsingOptions}
          pastedHeaderPreference={pastedHeaderPreference}
          upload={upload}
          onConfirmParsing={onConfirmParsing}
          onParsingOptionsChange={onParsingOptionsChange}
        />
      ) : null}
      {version !== null ? (
        <DatasetVersionPanel
          canApplyBayesianPreset={canApplyBayesianPreset}
          isLoadingPreview={isLoadingPreview}
          isLoadingProfile={isLoadingProfile}
          isSavingSchema={isSavingSchema}
          preview={preview}
          previewLimit={previewLimit}
          previewOffset={previewOffset}
          profile={profile}
          schemaDrafts={schemaDrafts}
          version={version}
          onApplyBayesianPreset={onApplyBayesianPreset}
          onLoadDatasetProfile={onLoadDatasetProfile}
          onLoadRowsPreview={onLoadRowsPreview}
          onPreviewLimitChange={onPreviewLimitChange}
          onSaveSchema={onSaveSchema}
          onSchemaDraftChange={onSchemaDraftChange}
        />
      ) : null}
      <div className="workflow-grid" aria-label="작업 흐름">
        {workflowSteps.map(([title, description]) => (
          <div className="workflow-step" key={title}>
            <strong>{title}</strong>
            <span>{description}</span>
          </div>
        ))}
      </div>
    </>
  );
}
