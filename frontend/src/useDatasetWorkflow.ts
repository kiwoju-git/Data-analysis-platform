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
import type { ActiveDatasetVersionSelectorProps } from "./ActiveDatasetVersionSelector";
import type { SchemaDraftPatch } from "./datasetPreparationTypes";
import { applyBayesianOptimizationPreset, type SchemaDraft } from "./schemaPresets";
import { useDatasetVersionCatalogState } from "./useDatasetVersionCatalogState";

const defaultPreviewLimit = 10;
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

function readDatasetVersionIdFromUrl(): string | null {
  if (typeof window === "undefined") return null;
  const value = new URLSearchParams(window.location.search).get("dataset_version_id");
  return value !== null && uuidPattern.test(value) ? value : null;
}

function updateActiveDatasetVersionQuery(versionId: string | null): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (versionId === null) url.searchParams.delete("dataset_version_id");
  else url.searchParams.set("dataset_version_id", versionId);
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
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
  activeDatasetSelectorProps: ActiveDatasetVersionSelectorProps;
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
  const [pastedHeaderPreference, setPastedHeaderPreference] = useState<boolean | null>(null);
  const [previewLimit, setPreviewLimit] = useState(defaultPreviewLimit);
  const [previewOffset, setPreviewOffset] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isPastingDataset, setIsPastingDataset] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isSavingSchema, setIsSavingSchema] = useState(false);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isSwitchingVersion, setIsSwitchingVersion] = useState(false);
  const [pendingVersionId, setPendingVersionId] = useState<string | null>(null);
  const [flowError, setFlowError] = useState<string | null>(null);
  const restoreRequestRef = useRef(0);
  const previewRequestRef = useRef(0);
  const profileRequestRef = useRef(0);
  const callbacksRef = useRef({ onDatasetColumnsChanged, onDatasetReset });
  callbacksRef.current = { onDatasetColumnsChanged, onDatasetReset };

  useEffect(() => {
    const versionId = readDatasetVersionIdFromUrl() ?? readStoredDatasetVersionId();
    if (versionId === null) return;

    const request = restoreRequestRef.current + 1;
    restoreRequestRef.current = request;
    setPendingVersionId(versionId);
    setIsSwitchingVersion(true);
    setIsLoadingPreview(true);
    setIsLoadingProfile(true);
    void Promise.all([
      fetchDatasetVersion(versionId),
      fetchRowsPreview(versionId, 0, defaultPreviewLimit),
      fetchDatasetProfile(versionId),
    ])
      .then(([restoredVersion, restoredPreview, restoredProfile]) => {
        if (restoreRequestRef.current !== request) return;
        setVersion(restoredVersion);
        setSchemaDrafts(schemaDraftsFromColumns(restoredVersion.columns));
        setPreview(restoredPreview);
        setPreviewOffset(0);
        setProfile(restoredProfile);
        setPendingVersionId(null);
        storeDatasetVersionId(restoredVersion.version_id);
        updateActiveDatasetVersionQuery(restoredVersion.version_id);
        callbacksRef.current.onDatasetColumnsChanged(restoredVersion.columns);
      })
      .catch((error) => {
        if (restoreRequestRef.current !== request) return;
        storeDatasetVersionId(null);
        updateActiveDatasetVersionQuery(null);
        setFlowError(
          error instanceof Error ? error.message : "dataset_version_restore_failed",
        );
      })
      .finally(() => {
        if (restoreRequestRef.current !== request) return;
        setIsLoadingPreview(false);
        setIsLoadingProfile(false);
        setIsSwitchingVersion(false);
      });

    return () => {
      if (restoreRequestRef.current === request) restoreRequestRef.current += 1;
    };
  }, []);

  const datasetVersionCatalogState = useDatasetVersionCatalogState(
    pendingVersionId ?? version?.version_id ?? null,
  );

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
    previewRequestRef.current += 1;
    profileRequestRef.current += 1;
    storeDatasetVersionId(null);
    updateActiveDatasetVersionQuery(null);
    setVersion(null);
    setPendingVersionId(null);
    setIsSwitchingVersion(false);
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
    setPastedHeaderPreference(null);
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
    setPastedHeaderPreference(null);
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

  async function handlePasteDataset(
    content: string,
    previewHasHeader: boolean,
  ): Promise<boolean> {
    if (content.trim() === "") {
      setFlowError("empty_pasted_data");
      return false;
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
      setPastedHeaderPreference(previewHasHeader);
      return true;
    } catch (error) {
      setUpload(null);
      setParsingOptions(null);
      setFlowError(error instanceof Error ? error.message : "dataset_paste_failed");
      return false;
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
      updateActiveDatasetVersionQuery(response.version_id);
      setPendingVersionId(null);
      setSchemaDrafts(schemaDraftsFromColumns(response.columns));
      onDatasetColumnsChanged(response.columns);
      setPreviewOffset(0);
      await Promise.all([
        loadRowsPreview(response.version_id, 0),
        loadDatasetProfile(response.version_id),
      ]);
      datasetVersionCatalogState.onRefresh();
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

  async function loadRowsPreview(
    versionId: string,
    offset: number,
    limit = previewLimit,
  ) {
    const request = previewRequestRef.current + 1;
    previewRequestRef.current = request;
    setIsLoadingPreview(true);
    try {
      const response = await fetchRowsPreview(versionId, offset, limit);
      if (previewRequestRef.current !== request) return;
      setPreview(response);
      setPreviewOffset(offset);
    } catch (error) {
      if (previewRequestRef.current !== request) return;
      setFlowError(error instanceof Error ? error.message : "rows_preview_failed");
    } finally {
      if (previewRequestRef.current === request) setIsLoadingPreview(false);
    }
  }

  async function loadDatasetProfile(versionId: string) {
    const request = profileRequestRef.current + 1;
    profileRequestRef.current = request;
    setIsLoadingProfile(true);
    try {
      const response = await fetchDatasetProfile(versionId);
      if (profileRequestRef.current !== request) return;
      setProfile(response);
    } catch (error) {
      if (profileRequestRef.current !== request) return;
      setProfile(null);
      setFlowError(error instanceof Error ? error.message : "dataset_profile_failed");
    } finally {
      if (profileRequestRef.current === request) setIsLoadingProfile(false);
    }
  }

  async function activateDatasetVersion(versionId: string) {
    if (versionId === "" || (version?.version_id === versionId && pendingVersionId === null)) {
      return;
    }
    const request = restoreRequestRef.current + 1;
    restoreRequestRef.current = request;
    previewRequestRef.current += 1;
    profileRequestRef.current += 1;
    setPendingVersionId(versionId);
    setIsSwitchingVersion(true);
    setIsLoadingPreview(true);
    setIsLoadingProfile(true);
    setFlowError(null);
    setVersion(null);
    setSchemaDrafts([]);
    setPreview(null);
    setProfile(null);
    setPreviewOffset(0);
    callbacksRef.current.onDatasetReset();
    try {
      const [nextVersion, nextPreview, nextProfile] = await Promise.all([
        fetchDatasetVersion(versionId),
        fetchRowsPreview(versionId, 0, defaultPreviewLimit),
        fetchDatasetProfile(versionId),
      ]);
      if (restoreRequestRef.current !== request) return;
      setVersion(nextVersion);
      setSchemaDrafts(schemaDraftsFromColumns(nextVersion.columns));
      setPreview(nextPreview);
      setProfile(nextProfile);
      setPreviewLimit(defaultPreviewLimit);
      setPendingVersionId(null);
      storeDatasetVersionId(nextVersion.version_id);
      updateActiveDatasetVersionQuery(nextVersion.version_id);
      callbacksRef.current.onDatasetColumnsChanged(nextVersion.columns);
    } catch (error) {
      if (restoreRequestRef.current !== request) return;
      storeDatasetVersionId(null);
      updateActiveDatasetVersionQuery(null);
      setFlowError(error instanceof Error ? error.message : "dataset_version_restore_failed");
    } finally {
      if (restoreRequestRef.current === request) {
        setIsLoadingPreview(false);
        setIsLoadingProfile(false);
        setIsSwitchingVersion(false);
      }
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

  function handlePreviewLimitChange(limit: number) {
    if (version === null || ![10, 25, 50, 100].includes(limit)) return;
    const lastAlignedOffset =
      version.row_count === 0 ? 0 : Math.floor((version.row_count - 1) / limit) * limit;
    const nextOffset = Math.min(Math.floor(previewOffset / limit) * limit, lastAlignedOffset);
    setPreviewLimit(limit);
    void loadRowsPreview(version.version_id, nextOffset, limit);
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
    pastedHeaderPreference,
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
    onPreviewLimitChange: handlePreviewLimitChange,
    onParsingOptionsChange: (options: ConfirmedParsingOptions) => {
      setParsingOptions(options);
    },
    onPasteDataset: handlePasteDataset,
    onSaveSchema: () => {
      void handleSaveSchema();
    },
    onSchemaDraftChange: updateSchemaDraft,
    onUpload: (event: FormEvent<HTMLFormElement>) => {
      void handleUpload(event);
    },
  } satisfies DatasetPreparationPageProps;

  const activeDatasetSelectorProps = {
    catalogState: datasetVersionCatalogState,
    isSwitching: isSwitchingVersion,
    pendingVersionId,
    version,
    onRetrySwitch: () => {
      if (pendingVersionId !== null) void activateDatasetVersion(pendingVersionId);
    },
    onSelect: (versionId: string) => {
      void activateDatasetVersion(versionId);
    },
  } satisfies ActiveDatasetVersionSelectorProps;

  return {
    activeDatasetSelectorProps,
    datasetPageProps,
    flowError,
    profile,
    setFlowError,
    version,
  };
}

const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

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
