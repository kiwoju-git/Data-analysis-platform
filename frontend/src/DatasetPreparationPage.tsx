import { useEffect, type ChangeEvent, type FormEvent } from "react";

import type {
  ConfirmedParsingOptions,
  DatasetProfileResponse,
  DatasetCellCorrectionRequest,
  DatasetCellCorrectionResponse,
  DatasetRowsPreviewResponse,
  DatasetUploadResponse,
  DatasetVersionResponse,
} from "./api";
import { ParsingConfirmationPanel } from "./DatasetParsingPanel";
import { DatasetVersionPanel } from "./DatasetVersionPanel";
import type { SchemaDraftPatch } from "./datasetPreparationTypes";
import { PasteDatasetPanel } from "./PasteDatasetPanel";
import type { SchemaDraft } from "./schemaPresets";
import { appLocationChangeEvent } from "./browserNavigation";

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
  onCreateCellCorrection?: (
    request: DatasetCellCorrectionRequest,
  ) => Promise<DatasetCellCorrectionResponse>;
  onCellEditDirtyChange?: (dirty: boolean) => void;
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
  onCreateCellCorrection = unavailableCellCorrection,
  onCellEditDirtyChange = () => undefined,
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
  useEffect(() => {
    const reveal = () => revealDatasetSection();
    window.addEventListener("popstate", reveal);
    window.addEventListener(appLocationChangeEvent, reveal);
    reveal();
    return () => {
      window.removeEventListener("popstate", reveal);
      window.removeEventListener(appLocationChangeEvent, reveal);
    };
  }, []);

  return (
    <>
      <div className="section" id="dataset-intake" tabIndex={-1}>
        <h2 id="workspace-title">데이터셋 등록</h2>
        <p>
          파일을 업로드하거나 표를 붙여넣고, 파싱과 변수 역할을 확인한 뒤 분석용
          데이터셋 버전을 생성합니다.
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
          onCreateCellCorrection={onCreateCellCorrection}
          onCellEditDirtyChange={onCellEditDirtyChange}
          onLoadDatasetProfile={onLoadDatasetProfile}
          onLoadRowsPreview={onLoadRowsPreview}
          onPreviewLimitChange={onPreviewLimitChange}
          onSaveSchema={onSaveSchema}
          onSchemaDraftChange={onSchemaDraftChange}
        />
      ) : null}
    </>
  );
}

function unavailableCellCorrection(
  request: DatasetCellCorrectionRequest,
): Promise<DatasetCellCorrectionResponse> {
  void request;
  return Promise.reject(new Error("dataset_cell_correction_unavailable"));
}

function revealDatasetSection(): void {
  if (typeof window === "undefined") return;
  const requested = new URL(window.location.href).searchParams.get("section");
  if (
    requested !== "dataset-intake" &&
    requested !== "dataset-parsing" &&
    requested !== "dataset-version"
  ) {
    return;
  }
  window.requestAnimationFrame(() => {
    const target =
      document.getElementById(requested) ??
      document.getElementById("dataset-intake");
    target?.scrollIntoView({ block: "start" });
    target?.focus({ preventScroll: true });
  });
}
