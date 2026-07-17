import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";

import {
  confirmDatasetParsing,
  createDatasetFromPastedText,
  fetchDatasetProfile,
  fetchDatasetVersion,
  fetchRowsPreview,
  uploadDataset,
  updateDatasetSchema,
  type ConfirmedParsingOptions,
  type DatasetColumnResponse,
  type DatasetProfileResponse,
  type DatasetRowsPreviewResponse,
  type DatasetUploadResponse,
  type DatasetVersionResponse,
} from "./api";
import type { DatasetPreparationPageProps } from "./DatasetPreparationPage";
import type { SchemaDraftPatch } from "./datasetPreparationTypes";
import { applyBayesianOptimizationPreset, type SchemaDraft } from "./schemaPresets";

const previewLimit = 10;
const defaultMissingTokens = ["", "NA", "N/A", "null", "N/T"];
const currentDatasetVersionStorageKey = "datalab.current_dataset_version_id";

function readStoredDatasetVersionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(currentDatasetVersionStorageKey);
  } catch {
    return null;
  }
}

function storeDatasetVersionId(versionId: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (versionId === null) {
      window.sessionStorage.removeItem(currentDatasetVersionStorageKey);
    } else {
      window.sessionStorage.setItem(currentDatasetVersionStorageKey, versionId);
    }
  } catch {
    // Browser storage availability must not block the local analysis workflow.
  }
}

export interface DatasetWorkflowCallbacks {
  onDatasetReset: () => void;
  onDatasetColumnsChanged: (columns: DatasetColumnResponse[]) => void;
  onSchemaChanged: (columns: DatasetColumnResponse[]) => void;
}

export interface DatasetWorkflow {
  datasetPageProps: DatasetPreparationPageProps;
  flowError: string | null;
  profile: DatasetProfileResponse | null;
  setFlowError: (error: string | null) => void;
  version: DatasetVersionResponse | null;
}

export function useDatasetWorkflow({
  onDatasetColumnsChanged,
  onDatasetReset,
  onSchemaChanged,
}: DatasetWorkflowCallbacks): DatasetWorkflow {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<DatasetUploadResponse | null>(null);
  const [parsingOptions, setParsingOptions] = useState<ConfirmedParsingOptions | null>(null);
  const [version, setVersion] = useState<DatasetVersionResponse | null>(null);
  const [schemaDrafts, setSchemaDrafts] = useState<SchemaDraft[]>([]);
  const [preview, setPreview] = useState<DatasetRowsPreviewResponse | null>(null);
  const [profile, setProfile] = useState<DatasetProfileResponse | null>(null);
  const pasteTextAreaRef = useRef<HTMLTextAreaElement | null>(null);
  const [pastedTextLength, setPastedTextLength] = useState(0);
  const [previewOffset, setPreviewOffset] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isPastingDataset, setIsPastingDataset] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isSavingSchema, setIsSavingSchema] = useState(false);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [flowError, setFlowError] = useState<string | null>(null);
  const restoreRequestRef = useRef(0);
  const callbacksRef = useRef({ onDatasetColumnsChanged });
  callbacksRef.current = { onDatasetColumnsChanged };

  useEffect(() => {
    const versionId = readStoredDatasetVersionId();
    if (versionId === null) return;

    const request = restoreRequestRef.current + 1;
    restoreRequestRef.current = request;
    setIsLoadingPreview(true);
    setIsLoadingProfile(true);
    void Promise.all([
      fetchDatasetVersion(versionId),
      fetchRowsPreview(versionId, 0, previewLimit),
      fetchDatasetProfile(versionId),
    ])
      .then(([restoredVersion, restoredPreview, restoredProfile]) => {
        if (restoreRequestRef.current !== request) return;
        setVersion(restoredVersion);
        setSchemaDrafts(schemaDraftsFromColumns(restoredVersion.columns));
        setPreview(restoredPreview);
        setPreviewOffset(0);
        setProfile(restoredProfile);
        callbacksRef.current.onDatasetColumnsChanged(restoredVersion.columns);
      })
      .catch((error) => {
        if (restoreRequestRef.current !== request) return;
        storeDatasetVersionId(null);
        setFlowError(
          error instanceof Error ? error.message : "dataset_version_restore_failed",
        );
      })
      .finally(() => {
        if (restoreRequestRef.current !== request) return;
        setIsLoadingPreview(false);
        setIsLoadingProfile(false);
      });

    return () => {
      if (restoreRequestRef.current === request) restoreRequestRef.current += 1;
    };
  }, []);

  const delimiterOptions = useMemo(() => {
    const candidates =
      upload?.parsing.delimiter_candidates.map((candidate) => candidate.delimiter) ?? [];
    return Array.from(new Set([",", "\t", ";", "|", ...candidates]));
  }, [upload]);

  const canConfirm =
    upload !== null &&
    parsingOptions !== null &&
    canConfirmParsingOptions(parsingOptions) &&
    !isConfirming;

  const canApplyBayesianPreset =
    version !== null &&
    version.parsing.has_header === false &&
    schemaDrafts.length >= 34 &&
    version.columns
      .slice(0, 34)
      .every((column, index) => column.original_name === `column_${index + 1}`);

  function resetDatasetDerivedState() {
    restoreRequestRef.current += 1;
    storeDatasetVersionId(null);
    setVersion(null);
    setSchemaDrafts([]);
    setPreview(null);
    setProfile(null);
    setPreviewOffset(0);
    onDatasetReset();
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.currentTarget.files?.[0] ?? null);
    setUpload(null);
    setParsingOptions(null);
    resetDatasetDerivedState();
    setFlowError(null);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedFile === null) {
      setFlowError("업로드할 파일을 선택하세요.");
      return;
    }

    setIsUploading(true);
    setFlowError(null);
    resetDatasetDerivedState();
    try {
      const response = await uploadDataset(selectedFile);
      setUpload(response);
      setParsingOptions(parsingSuggestionToConfirmation(response));
    } catch (error) {
      setUpload(null);
      setParsingOptions(null);
      setFlowError(error instanceof Error ? error.message : "dataset_upload_failed");
    } finally {
      setIsUploading(false);
    }
  }

  async function handlePasteDataset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = pasteTextAreaRef.current?.value ?? "";
    if (content.trim() === "") {
      setFlowError("empty_pasted_data");
      return;
    }

    setIsPastingDataset(true);
    setFlowError(null);
    setSelectedFile(null);
    setUpload(null);
    setParsingOptions(null);
    resetDatasetDerivedState();
    try {
      const response = await createDatasetFromPastedText({
        content,
        original_filename: "pasted-data.txt",
      });
      setUpload(response);
      setParsingOptions(parsingSuggestionToConfirmation(response));
      if (pasteTextAreaRef.current !== null) {
        pasteTextAreaRef.current.value = "";
      }
      setPastedTextLength(0);
    } catch (error) {
      setUpload(null);
      setParsingOptions(null);
      setFlowError(error instanceof Error ? error.message : "dataset_paste_failed");
    } finally {
      setIsPastingDataset(false);
    }
  }

  async function handleConfirmParsing() {
    if (upload === null || parsingOptions === null) {
      return;
    }

    setIsConfirming(true);
    setFlowError(null);
    try {
      const response = await confirmDatasetParsing(upload.dataset_id, {
        parsing: parsingOptions,
        columns: [],
      });
      setVersion(response);
      storeDatasetVersionId(response.version_id);
      setSchemaDrafts(schemaDraftsFromColumns(response.columns));
      onDatasetColumnsChanged(response.columns);
      setPreviewOffset(0);
      await Promise.all([
        loadRowsPreview(response.version_id, 0),
        loadDatasetProfile(response.version_id),
      ]);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "parsing_confirmation_failed");
    } finally {
      setIsConfirming(false);
    }
  }

  async function handleSaveSchema() {
    if (version === null) {
      return;
    }

    setIsSavingSchema(true);
    setFlowError(null);
    try {
      const response = await updateDatasetSchema(version.version_id, {
        columns: schemaDrafts.map((draft) => ({
          column_id: draft.column_id,
          display_name: draft.display_name,
          measurement_level: draft.measurement_level,
          role: draft.role,
          unit: draft.unit.trim() === "" ? null : draft.unit.trim(),
        })),
      });
      const updatedVersion: DatasetVersionResponse = {
        ...version,
        schema_hash: response.schema_hash,
        columns: response.columns,
      };
      setVersion(updatedVersion);
      setSchemaDrafts(schemaDraftsFromColumns(response.columns));
      onSchemaChanged(response.columns);
      await Promise.all([
        loadRowsPreview(version.version_id, previewOffset),
        loadDatasetProfile(version.version_id),
      ]);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "schema_update_failed");
    } finally {
      setIsSavingSchema(false);
    }
  }

  async function loadRowsPreview(versionId: string, offset: number) {
    setIsLoadingPreview(true);
    try {
      const response = await fetchRowsPreview(versionId, offset, previewLimit);
      setPreview(response);
      setPreviewOffset(offset);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "rows_preview_failed");
    } finally {
      setIsLoadingPreview(false);
    }
  }

  async function loadDatasetProfile(versionId: string) {
    setIsLoadingProfile(true);
    try {
      const response = await fetchDatasetProfile(versionId);
      setProfile(response);
    } catch (error) {
      setProfile(null);
      setFlowError(error instanceof Error ? error.message : "dataset_profile_failed");
    } finally {
      setIsLoadingProfile(false);
    }
  }

  function updateSchemaDraft(columnId: string, patch: SchemaDraftPatch) {
    setSchemaDrafts((current) =>
      current.map((draft) => (draft.column_id === columnId ? { ...draft, ...patch } : draft)),
    );
  }

  function handleApplyBayesianPreset() {
    setSchemaDrafts((current) => applyBayesianOptimizationPreset(current));
  }

  const datasetPageProps = {
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
    pasteTextAreaRef,
    pastedTextLength,
    preview,
    previewLimit,
    previewOffset,
    profile,
    schemaDrafts,
    selectedFile,
    upload,
    version,
    onApplyBayesianPreset: handleApplyBayesianPreset,
    onConfirmParsing: () => {
      void handleConfirmParsing();
    },
    onFileChange: handleFileChange,
    onLoadDatasetProfile: (versionId: string) => {
      void loadDatasetProfile(versionId);
    },
    onLoadRowsPreview: (versionId: string, offset: number) => {
      void loadRowsPreview(versionId, offset);
    },
    onParsingOptionsChange: (options: ConfirmedParsingOptions) => {
      setParsingOptions(options);
    },
    onPasteDataset: (event: FormEvent<HTMLFormElement>) => {
      void handlePasteDataset(event);
    },
    onPastedTextLengthChange: setPastedTextLength,
    onSaveSchema: () => {
      void handleSaveSchema();
    },
    onSchemaDraftChange: updateSchemaDraft,
    onUpload: (event: FormEvent<HTMLFormElement>) => {
      void handleUpload(event);
    },
  } satisfies DatasetPreparationPageProps;

  return {
    datasetPageProps,
    flowError,
    profile,
    setFlowError,
    version,
  };
}

export function canConfirmParsingOptions(options: ConfirmedParsingOptions): boolean {
  if (!(options.has_header || options.data_start_row !== null)) {
    return false;
  }
  if (options.kind === "delimited_text") {
    return options.encoding !== null && options.delimiter !== null;
  }
  return options.kind === "xlsx";
}

export function parsingSuggestionToConfirmation(
  upload: DatasetUploadResponse,
): ConfirmedParsingOptions {
  return {
    kind: upload.parsing.kind,
    encoding: upload.parsing.suggested_encoding,
    delimiter: upload.parsing.suggested_delimiter,
    quote_char: upload.parsing.quote_char,
    decimal: upload.parsing.decimal,
    thousands: upload.parsing.thousands,
    has_header: upload.parsing.has_header,
    header_row: upload.parsing.header_row,
    data_start_row: upload.parsing.data_start_row,
    missing_tokens: defaultMissingTokens,
    xlsx_sheet_name: null,
  };
}

function schemaDraftsFromColumns(columns: DatasetColumnResponse[]): SchemaDraft[] {
  return columns.map((column) => ({
    column_id: column.column_id,
    display_name: column.display_name,
    measurement_level: column.measurement_level,
    role: column.role,
    unit: column.unit ?? "",
  }));
}
