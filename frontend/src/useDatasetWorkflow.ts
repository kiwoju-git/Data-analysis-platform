import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";

import {
  confirmDatasetParsing,
  createDatasetCellCorrection,
  createDatasetFromPastedText,
  fetchDatasetProfile,
  fetchDatasetVersion,
  fetchRowsPreview,
  uploadDataset,
  updateDatasetSchema,
  type ConfirmedParsingOptions,
  type DatasetCellCorrectionRequest,
  type DatasetVersionDeleteResponse,
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
import { createLatestRequestGuard } from "./latestRequest";
import { createSourceContextGuard } from "./sourceContextGuard";
import { appLocationChangeEvent } from "./browserNavigation";
import { t } from "./i18n/translate";
import { datasetRequestErrorCode as requestErrorCode } from "./datasetRequestErrors";
import {
  compareSchemaDraft, createSchemaDraftBase, datasetSchemaIsUnchanged, rebaseSchemaDraft, schemaDraftsFromColumns,
  validSchemaHash, type SchemaConflictState, type SchemaDraftBase,
} from "./datasetSchemaDraft";

const defaultPreviewLimit = 10;
const defaultMissingTokens = ["", "NA", "N/A", "null", "N/T"];
const currentDatasetVersionStorageKey = "datalab.current_dataset_version_id";

function readStoredDatasetVersionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.sessionStorage.getItem(currentDatasetVersionStorageKey);
    return value !== null && uuidPattern.test(value) ? value : null;
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
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
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
  onCommittedSourceIntent?: () => void;
  onDatasetReset: () => void;
  onDatasetColumnsChanged: (columns: DatasetColumnResponse[]) => void;
  onDatasetVersionCreated?: () => void;
  onSchemaChanged: (columns: DatasetColumnResponse[]) => void;
}

export interface DatasetWorkflow {
  activeDatasetSelectorProps: ActiveDatasetVersionSelectorProps;
  datasetPageProps: DatasetPreparationPageProps;
  flowError: string | null;
  profile: DatasetProfileResponse | null;
  setFlowError: (error: string | null) => void;
  version: DatasetVersionResponse | null;
  confirmNavigation: () => boolean;
  onDatasetDeleted: (response: DatasetVersionDeleteResponse) => void;
}

type DatasetSourceIdentity = Readonly<{
  versionId: string;
  schemaHash: string;
  canonicalSha256: string | null;
}>;

const requestLaneNames = ["activation", "intake", "confirmation", "schema", "cell", "preview", "profile"] as const;
type RequestLane = typeof requestLaneNames[number];

function sourceIdentity(version: DatasetVersionResponse | null): DatasetSourceIdentity | null {
  return version === null ? null : Object.freeze({
    versionId: version.version_id,
    schemaHash: version.schema_hash,
    canonicalSha256: version.canonical_artifact?.sha256 ?? null,
  });
}

function contextMismatch(): Error {
  return Object.assign(new Error("dataset_response_context_mismatch"), { code: "dataset_response_context_mismatch" });
}

export function useDatasetWorkflow({
  onCommittedSourceIntent,
  onDatasetColumnsChanged,
  onDatasetReset,
  onDatasetVersionCreated = () => undefined,
  onSchemaChanged,
}: DatasetWorkflowCallbacks): DatasetWorkflow {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<DatasetUploadResponse | null>(null);
  const [parsingOptions, setParsingOptions] = useState<ConfirmedParsingOptions | null>(null);
  const [version, setVersion] = useState<DatasetVersionResponse | null>(null);
  const [schemaDrafts, setSchemaDrafts] = useState<SchemaDraft[]>([]);
  const [schemaConflict, setSchemaConflict] = useState<SchemaConflictState | null>(null);
  const [schemaStaged, setSchemaStaged] = useState(false);
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
  const [activationError, setActivationError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [draftResetRevision, setDraftResetRevision] = useState(0);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const acceptedFileList = useRef<FileList | null>(null);
  const mounted = useRef(false);
  const committed = useRef<DatasetVersionResponse | null>(null);
  const committedGeneration = useRef(0);
  const schemaWriteSequence = useRef(0);
  const schemaBase = useRef<SchemaDraftBase | null>(null);
  const schemaComparisonGuard = useRef(createLatestRequestGuard());
  const latestSchema = useRef<DatasetVersionResponse | null>(null);
  const pending = useRef<string | null>(null);
  const activationInFlight = useRef(false);
  const readsInFlight = useRef({ preview: false, profile: false });
  const context = useRef(createSourceContextGuard<DatasetSourceIdentity | null>(null));
  const lanes = useRef(Object.fromEntries(requestLaneNames.map((name) => [name, createLatestRequestGuard()])) as Record<RequestLane, ReturnType<typeof createLatestRequestGuard>>);
  const callbacks = useRef({ onDatasetColumnsChanged, onDatasetReset, onDatasetVersionCreated, onSchemaChanged, onCommittedSourceIntent });
  callbacks.current = { onDatasetColumnsChanged, onDatasetReset, onDatasetVersionCreated, onSchemaChanged, onCommittedSourceIntent };
  const cellDirty = useRef(false);
  const pasteDirty = useRef(false);
  const schemaDirty = useRef(false);
  const schemaRevision = useRef(0);
  const schemaDraftsRef = useRef(schemaDrafts);
  schemaDraftsRef.current = schemaDrafts;
  const readPage = useRef({ offset: 0, limit: defaultPreviewLimit });
  const location = useRef(typeof window === "undefined" ? "" : window.location.href);
  const navigation = useRef({ activate: activateDatasetVersion, confirm: confirmNavigation, hasDirty: hasDirtyChanges });
  navigation.current = { activate: activateDatasetVersion, confirm: confirmNavigation, hasDirty: hasDirtyChanges };
  const datasetVersionCatalogState = useDatasetVersionCatalogState(pendingVersionId ?? version?.version_id ?? null);

  useEffect(() => {
    mounted.current = true;
    if (context.current.isDisposed()) context.current = createSourceContextGuard(sourceIdentity(committed.current));
    const ownedContext = context.current;
    const ownedLanes = lanes.current;
    const ownedComparisonGuard = schemaComparisonGuard.current;
    const restoredId = readDatasetVersionIdFromUrl() ?? readStoredDatasetVersionId();
    if (restoredId !== null) void navigation.current.activate(restoredId, true);
    const onLocationChange = (event: Event) => {
      const next = new URL(window.location.href);
      const previous = new URL(location.current);
      if (previous.pathname === "/datasets" && next.pathname !== "/datasets" && !navigation.current.confirm()) {
        window.history.replaceState(window.history.state, "", previous.href);
        event.stopImmediatePropagation();
        return;
      }
      const requested = readDatasetVersionIdFromUrl();
      if (requested !== null && requested !== committed.current?.version_id && requested !== pending.current) {
        void navigation.current.activate(requested);
      }
      location.current = window.location.href;
    };
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!navigation.current.hasDirty()) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener?.("popstate", onLocationChange);
    window.addEventListener?.(appLocationChangeEvent, onLocationChange);
    window.addEventListener?.("beforeunload", beforeUnload);
    return () => {
      mounted.current = false;
      ownedContext.dispose();
      for (const lane of Object.values(ownedLanes)) lane.cancel();
      ownedComparisonGuard.cancel();
      window.removeEventListener?.("popstate", onLocationChange);
      window.removeEventListener?.(appLocationChangeEvent, onLocationChange);
      window.removeEventListener?.("beforeunload", beforeUnload);
    };
  }, []);

  function begin(lane: RequestLane) {
    const guard = context.current;
    const source = guard.capture();
    const request = lanes.current[lane].begin();
    return { lane, guard, source, request, identity: sourceIdentity(committed.current) };
  }

  function isCurrent(ticket: ReturnType<typeof begin>) {
    return mounted.current && context.current === ticket.guard &&
      ticket.guard.isCurrent(ticket.source) && lanes.current[ticket.lane].isCurrent(ticket.request);
  }

  function advanceSource(next = committed.current) {
    if (next !== null && next === committed.current) {
      if (readsInFlight.current.preview) setPreviewError("dataset_request_interrupted");
      if (readsInFlight.current.profile) setProfileError("dataset_request_interrupted");
    }
    readsInFlight.current = { preview: false, profile: false };
    context.current.advance(sourceIdentity(next));
    for (const lane of Object.values(lanes.current)) lane.cancel();
    pending.current = null;
    activationInFlight.current = false;
    setPendingVersionId(null);
    setIsSwitchingVersion(false);
    setIsUploading(false);
    setIsPastingDataset(false);
    setIsConfirming(false);
    setIsSavingSchema(false);
    setIsLoadingPreview(false);
    setIsLoadingProfile(false);
  }

  function persist(next: DatasetVersionResponse | null) {
    storeDatasetVersionId(next?.version_id ?? null);
    updateActiveDatasetVersionQuery(next?.version_id ?? null);
    if (typeof window !== "undefined") location.current = window.location.href;
  }

  function clearFileSelection() {
    setSelectedFile(null);
    acceptedFileList.current = null;
    if (fileInput.current !== null) fileInput.current.value = "";
  }

  function clearIntake(preserveFileInput = false) {
    if (!preserveFileInput) clearFileSelection();
    setUpload(null);
    setParsingOptions(null);
    setPastedHeaderPreference(null);
    pasteDirty.current = false;
    setDraftResetRevision((value) => value + 1);
  }

  function hasDirtyChanges() {
    return cellDirty.current || schemaDirty.current || pasteDirty.current || selectedFile !== null || upload !== null;
  }

  function approveReplacement() {
    return !hasDirtyChanges() || window.confirm(t("dataset.workflow.discardUnsaved"));
  }

  function confirmNavigation() {
    if (!approveReplacement()) return false;
    if (hasDirtyChanges()) {
      advanceSource();
      clearIntake();
      cellDirty.current = false;
      schemaDirty.current = false;
      schemaRevision.current += 1;
      clearSchemaConflict();
      schemaBase.current = committed.current === null ? null : createSchemaDraftBase(committed.current);
      const drafts = schemaDraftsFromColumns(committed.current?.columns ?? []);
      schemaDraftsRef.current = drafts;
      setSchemaDrafts(drafts);
    }
    return true;
  }

  function publishVersion(next: DatasetVersionResponse) {
    clearSchemaConflict();
    schemaBase.current = createSchemaDraftBase(next);
    advanceSource(next);
    committedGeneration.current += 1;
    committed.current = next;
    setVersion(next);
    const drafts = schemaDraftsFromColumns(next.columns);
    schemaDraftsRef.current = drafts;
    setSchemaDrafts(drafts);
    schemaDirty.current = false;
    schemaRevision.current += 1;
    cellDirty.current = false;
    clearIntake();
    readPage.current = { offset: 0, limit: defaultPreviewLimit };
    setPreviewLimit(defaultPreviewLimit);
    setPreviewOffset(0);
    callbacks.current.onDatasetReset();
    callbacks.current.onDatasetColumnsChanged(next.columns);
    setPreview(null);
    setProfile(null);
    setPreviewError(null);
    setProfileError(null);
    setActivationError(null);
    setFlowError(null);
    persist(next);
    void loadRowsPreview(next.version_id, readPage.current.offset, readPage.current.limit);
    void loadDatasetProfile(next.version_id);
  }

  // A schema write mutates the retained version. Reconcile its acknowledged
  // metadata without replacing a newer intake draft or cancelling its request.
  function publishSchema(next: DatasetVersionResponse, preserveDraft: boolean) {
    const unchanged = datasetSchemaIsUnchanged(committed.current, next);
    if (!preserveDraft) {
      schemaBase.current = createSchemaDraftBase(next);
      const drafts = schemaDraftsFromColumns(next.columns);
      schemaDraftsRef.current = drafts;
      setSchemaDrafts(drafts);
      schemaDirty.current = false;
    }
    setIsSavingSchema(false);
    if (unchanged) return;
    committedGeneration.current += 1;
    committed.current = next;
    setVersion(next);
    for (const lane of ["schema", "cell", "preview", "profile"] as const) lanes.current[lane].cancel();
    readsInFlight.current = { preview: false, profile: false };
    setPreview(null);
    setProfile(null);
    setPreviewError(null);
    setProfileError(null);
    callbacks.current.onSchemaChanged(next.columns);
    void loadRowsPreview(next.version_id, readPage.current.offset, readPage.current.limit);
    void loadDatasetProfile(next.version_id);
  }

  // A superseded write can still create a valid stored version. Refresh its catalog,
  // but never activate it or publish source-bound UI callbacks.
  function notifyPersistedVersion() {
    if (!mounted.current) return;
    datasetVersionCatalogState.onRefresh();
    callbacks.current.onDatasetVersionCreated();
  }

  async function loadRowsPreview(versionId: string, offset: number, limit = previewLimit) {
    if (!mounted.current || committed.current?.version_id !== versionId) return;
    const ticket = begin("preview");
    readsInFlight.current.preview = true;
    if (readPage.current.offset !== offset || readPage.current.limit !== limit) setPreview(null);
    readPage.current = { offset, limit };
    setPreviewOffset(offset);
    setPreviewLimit(limit);
    setIsLoadingPreview(true);
    setPreviewError(null);
    try {
      const response = await fetchRowsPreview(versionId, offset, limit);
      if (!isCurrent(ticket)) return;
      if (response.version_id !== versionId || response.offset !== offset || response.limit !== limit) throw contextMismatch();
      setPreview(response);
      setPreviewOffset(offset);
      setPreviewLimit(limit);
    } catch (error) {
      if (!isCurrent(ticket)) return;
      setPreviewError(requestErrorCode(error, "rows_preview_failed"));
    } finally {
      if (isCurrent(ticket)) {
        readsInFlight.current.preview = false;
        setIsLoadingPreview(false);
      }
    }
  }

  async function loadDatasetProfile(versionId: string) {
    if (!mounted.current || committed.current?.version_id !== versionId) return;
    const ticket = begin("profile");
    readsInFlight.current.profile = true;
    setIsLoadingProfile(true);
    setProfileError(null);
    try {
      const response = await fetchDatasetProfile(versionId);
      if (!isCurrent(ticket)) return;
      const expected = ticket.identity;
      if (expected === null || response.version_id !== versionId || response.schema_hash !== expected.schemaHash ||
          (expected.canonicalSha256 !== null && response.canonical_artifact?.sha256 !== expected.canonicalSha256)) {
        throw contextMismatch();
      }
      setProfile(response);
    } catch (error) {
      if (!isCurrent(ticket)) return;
      setProfileError(requestErrorCode(error, "dataset_profile_failed"));
    } finally {
      if (isCurrent(ticket)) {
        readsInFlight.current.profile = false;
        setIsLoadingProfile(false);
      }
    }
  }

  async function activateDatasetVersion(versionId: string, bootstrap = false) {
    if (!mounted.current || !uuidPattern.test(versionId) ||
        (committed.current?.version_id === versionId && pending.current === null)) return;
    if (!bootstrap && !approveReplacement()) {
      persist(committed.current);
      return;
    }
    clearSchemaConflict();
    advanceSource();
    pending.current = versionId;
    callbacks.current.onCommittedSourceIntent?.();
    activationInFlight.current = true;
    setPendingVersionId(versionId);
    const ticket = begin("activation");
    setIsSwitchingVersion(true);
    setActivationError(null);
    setFlowError(null);
    try {
      const next = await fetchDatasetVersion(versionId);
      if (!isCurrent(ticket)) return;
      if (next.version_id !== versionId) throw contextMismatch();
      publishVersion(next);
    } catch (error) {
      if (!isCurrent(ticket)) return;
      const code = requestErrorCode(error, "dataset_version_restore_failed");
      setActivationError(code);
      if (committed.current !== null || code === "dataset_version_not_found") persist(committed.current);
    } finally {
      if (isCurrent(ticket)) {
        activationInFlight.current = false;
        setIsSwitchingVersion(false);
      }
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    if (!mounted.current) return;
    const input = event.currentTarget;
    fileInput.current = input;
    const nextFile = input.files?.[0] ?? null;
    if (nextFile === null || ((pasteDirty.current || upload !== null || selectedFile !== null) &&
        !window.confirm(t("dataset.workflow.discardUnsaved")))) {
      if (acceptedFileList.current !== null) input.files = acceptedFileList.current;
      else input.value = "";
      return;
    }
    if (typeof DataTransfer !== "undefined") {
      const snapshot = new DataTransfer();
      snapshot.items.add(nextFile);
      acceptedFileList.current = snapshot.files;
    } else {
      acceptedFileList.current = input.files;
    }
    advanceSource();
    clearIntake(true);
    setSelectedFile(nextFile);
    setFlowError(null);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!mounted.current || selectedFile === null) {
      if (mounted.current) setFlowError("dataset_file_required");
      return;
    }
    advanceSource();
    const ticket = begin("intake");
    setIsUploading(true);
    setFlowError(null);
    setPastedHeaderPreference(null);
    setUpload(null);
    setParsingOptions(null);
    try {
      const response = await uploadDataset(selectedFile);
      if (!isCurrent(ticket)) return;
      setUpload(response);
      setParsingOptions(parsingSuggestionToConfirmation(response));
    } catch (error) {
      if (isCurrent(ticket)) setFlowError(requestErrorCode(error, "dataset_upload_failed"));
    } finally {
      if (isCurrent(ticket)) setIsUploading(false);
    }
  }

  async function handlePasteDataset(content: string, previewHasHeader: boolean): Promise<boolean> {
    if (!mounted.current || content.trim() === "") {
      if (mounted.current) setFlowError("empty_pasted_data");
      return false;
    }
    advanceSource();
    const ticket = begin("intake");
    setIsPastingDataset(true);
    setFlowError(null);
    clearFileSelection();
    setUpload(null);
    setParsingOptions(null);
    try {
      const response = await createDatasetFromPastedText({ content, original_filename: "pasted-data.txt" });
      if (!isCurrent(ticket)) return false;
      setUpload(response);
      setParsingOptions(parsingSuggestionToConfirmation(response));
      setPastedHeaderPreference(previewHasHeader);
      return true;
    } catch (error) {
      if (isCurrent(ticket)) setFlowError(requestErrorCode(error, "dataset_paste_failed"));
      return false;
    } finally {
      if (isCurrent(ticket)) setIsPastingDataset(false);
    }
  }

  async function handleConfirmParsing() {
    if (!mounted.current || upload === null || parsingOptions === null) return;
    if ((cellDirty.current || schemaDirty.current) && !window.confirm(t("dataset.workflow.discardUnsaved"))) return;
    callbacks.current.onCommittedSourceIntent?.();
    advanceSource();
    const ticket = begin("confirmation");
    setIsConfirming(true);
    setFlowError(null);
    try {
      const response = await confirmDatasetParsing(upload.dataset_id, { parsing: parsingOptions, columns: [] });
      if (!isCurrent(ticket)) {
        notifyPersistedVersion();
        return;
      }
      if (response.dataset_id !== upload.dataset_id) throw contextMismatch();
      publishVersion(response);
      notifyPersistedVersion();
    } catch (error) {
      if (isCurrent(ticket)) setFlowError(requestErrorCode(error, "parsing_confirmation_failed"));
    } finally {
      if (isCurrent(ticket)) setIsConfirming(false);
    }
  }

  async function handleSaveSchema() {
    const current = committed.current;
    if (!mounted.current || current === null || activationInFlight.current) return;
    const base = schemaBase.current;
    if (base === null || base.versionId !== current.version_id || base.datasetId !== current.dataset_id || !validSchemaHash(base.schemaHash)) {
      setFlowError("dataset_schema_base_invalid");
      return;
    }
    clearSchemaConflict();
    const ticket = begin("schema");
    const generation = committedGeneration.current;
    const sequence = ++schemaWriteSequence.current;
    const revision = schemaRevision.current;
    const submitted = schemaDraftsRef.current;
    if (compareSchemaDraft(base, submitted, current).some((change) => change.localChanged)) {
      callbacks.current.onCommittedSourceIntent?.();
    }
    const ownsCommittedSchema = () => mounted.current && committedGeneration.current === generation &&
      schemaWriteSequence.current === sequence && committed.current?.version_id === current.version_id &&
      committed.current.dataset_id === current.dataset_id && committed.current.schema_hash === current.schema_hash;
    setIsSavingSchema(true);
    setFlowError(null);
    try {
      const response = await updateDatasetSchema(current.version_id, {
        expected_schema_hash: base.schemaHash,
        columns: submitted.map((draft) => ({
          column_id: draft.column_id, display_name: draft.display_name,
          measurement_level: draft.measurement_level, role: draft.role,
          unit: draft.unit.trim() === "" ? null : draft.unit.trim(),
        })),
      });
      if (!isCurrent(ticket) && !ownsCommittedSchema()) return;
      if (response.version_id !== current.version_id || response.dataset_id !== current.dataset_id || !validSchemaHash(response.schema_hash)) throw contextMismatch();
      publishSchema({ ...current, schema_hash: response.schema_hash, columns: response.columns }, revision !== schemaRevision.current);
    } catch (error) {
      if (!isCurrent(ticket) && !ownsCommittedSchema()) return;
      if (requestErrorCode(error, "schema_update_failed") === "dataset_schema_conflict" &&
          typeof error === "object" && error !== null && "status" in error && error.status === 409) {
        setIsSavingSchema(false);
        void loadSchemaComparison();
      } else {
        setFlowError(requestErrorCode(error, "schema_update_failed"));
      }
    } finally {
      if (isCurrent(ticket)) setIsSavingSchema(false);
    }
  }

  function clearSchemaConflict() {
    schemaComparisonGuard.current.cancel();
    latestSchema.current = null;
    setSchemaConflict(null);
    setSchemaStaged(false);
  }

  async function loadSchemaComparison() {
    const current = committed.current;
    const base = schemaBase.current;
    if (!mounted.current || current === null || base === null || activationInFlight.current) return;
    const token = schemaComparisonGuard.current.begin();
    const generation = committedGeneration.current;
    const sequence = schemaWriteSequence.current;
    const ownsComparison = () => mounted.current && schemaComparisonGuard.current.isCurrent(token) &&
      committedGeneration.current === generation && schemaWriteSequence.current === sequence && schemaBase.current === base;
    latestSchema.current = null;
    setSchemaConflict({ status: "loading", baseHash: base.schemaHash, latest: null, errorCode: null });
    try {
      const latest = await fetchDatasetVersion(current.version_id);
      if (!ownsComparison()) return;
      compareSchemaDraft(base, schemaDraftsRef.current, latest);
      publishSchema(latest, true);
      latestSchema.current = latest;
      setSchemaConflict({ status: "ready", baseHash: base.schemaHash, latest, errorCode: null });
    } catch (error) {
      if (!ownsComparison()) return;
      setSchemaConflict({ status: "failed", baseHash: base.schemaHash, latest: null,
        errorCode: requestErrorCode(error, "dataset_schema_comparison_failed") });
    }
  }

  function resolveSchemaConflict(apply: boolean) {
    const latest = latestSchema.current;
    const base = schemaBase.current;
    if (!mounted.current || latest === null || base === null || activationInFlight.current ||
        committed.current?.version_id !== latest.version_id || committed.current.schema_hash !== latest.schema_hash) return;
    if (!apply && !window.confirm(t("dataset.schemaConflict.confirmDiscard"))) return;
    const drafts = apply ? rebaseSchemaDraft(base, schemaDraftsRef.current, latest) : schemaDraftsFromColumns(latest.columns);
    schemaBase.current = createSchemaDraftBase(latest);
    schemaDraftsRef.current = drafts;
    setSchemaDrafts(drafts);
    schemaRevision.current += 1;
    schemaDirty.current = apply;
    clearSchemaConflict();
    setSchemaStaged(apply);
  }

  function updateSchemaDraft(columnId: string, patch: SchemaDraftPatch) {
    schemaRevision.current += 1;
    schemaDirty.current = true;
    setSchemaDrafts((current) => {
      const next = current.map((draft) => draft.column_id === columnId ? { ...draft, ...patch } : draft);
      schemaDraftsRef.current = next;
      return next;
    });
  }

  function handleApplyBayesianPreset() {
    schemaRevision.current += 1;
    schemaDirty.current = true;
    setSchemaDrafts((current) => {
      const next = applyBayesianOptimizationPreset(current);
      schemaDraftsRef.current = next;
      return next;
    });
  }

  function handlePreviewLimitChange(limit: number) {
    const current = committed.current;
    if (current === null || ![10, 25, 50, 100].includes(limit)) return;
    const lastAlignedOffset = current.row_count === 0 ? 0 : Math.floor((current.row_count - 1) / limit) * limit;
    const nextOffset = Math.min(Math.floor(previewOffset / limit) * limit, lastAlignedOffset);
    void loadRowsPreview(current.version_id, nextOffset, limit);
  }

  function onDatasetDeleted(response: DatasetVersionDeleteResponse) {
    if (!mounted.current) return;
    const current = committed.current;
    const deletesActive = current !== null && (current.version_id === response.version_id ||
      (response.deletion_scope === "dataset_root" && current.dataset_id === response.dataset_id));
    const deletesPending = pending.current === response.version_id;
    const deletesIntake = response.deletion_scope === "dataset_root" && upload?.dataset_id === response.dataset_id;
    datasetVersionCatalogState.onRefresh();
    if (!deletesActive && !deletesPending && !deletesIntake) return;
    advanceSource(deletesActive ? null : current);
    if (deletesIntake || deletesActive) clearIntake();
    if (deletesActive) {
      clearSchemaConflict();
      schemaBase.current = null;
      committedGeneration.current += 1;
      committed.current = null;
      setVersion(null);
      setPreview(null);
      setProfile(null);
      setSchemaDrafts([]);
      schemaDraftsRef.current = [];
      cellDirty.current = false;
      schemaDirty.current = false;
      callbacks.current.onDatasetReset();
    }
    setActivationError(null);
    setPreviewError(null);
    setProfileError(null);
    persist(committed.current);
  }

  const delimiterOptions = useMemo(() => Array.from(new Set([",", "\t", ";", "|",
    ...(upload?.parsing.delimiter_candidates.map((candidate) => candidate.delimiter) ?? [])])), [upload]);
  const canConfirm = upload !== null && parsingOptions !== null && canConfirmParsingOptions(parsingOptions) && !isConfirming;
  const canApplyBayesianPreset = version !== null && version.parsing.has_header === false &&
    schemaDrafts.length >= 34 && version.columns.slice(0, 34).every((column, index) => column.original_name === `column_${index + 1}`);

  const datasetPageProps = {
    canApplyBayesianPreset, canConfirm, delimiterOptions, flowError, isConfirming,
    isLoadingPreview, isLoadingProfile, isPastingDataset, isSavingSchema, isUploading,
    parsingOptions, pastedHeaderPreference, preview, previewLimit, previewOffset,
    profile, schemaDrafts, selectedFile, upload, version, previewError, profileError,
    isSwitchingVersion, draftResetRevision,
    schemaConflict, schemaStaged,
    schemaComparison: schemaConflict?.status === "ready" && schemaConflict.latest !== null && schemaBase.current !== null
      ? compareSchemaDraft(schemaBase.current, schemaDrafts, schemaConflict.latest) : [],
    onSchemaConflictApply: () => resolveSchemaConflict(true),
    onSchemaConflictDiscard: () => resolveSchemaConflict(false),
    onSchemaConflictEdit: () => { setSchemaStaged(false); },
    onSchemaConflictRetry: () => { void loadSchemaComparison(); },
    onApplyBayesianPreset: handleApplyBayesianPreset,
    onCellEditDirtyChange: (dirty: boolean) => { cellDirty.current = dirty; },
    onPasteDraftChange: (dirty: boolean, reason: "user" | "reset" = "user") => {
      pasteDirty.current = dirty;
      if (reason === "user") {
        advanceSource();
        setUpload(null);
        setParsingOptions(null);
      }
    },
    onCreateCellCorrection: async (request: DatasetCellCorrectionRequest) => {
      const current = committed.current;
      if (!mounted.current || current === null || activationInFlight.current) return null;
      if (request.confirmation_parent_version_id !== current.version_id || request.expected_parent_schema_hash !== current.schema_hash) throw contextMismatch();
      callbacks.current.onCommittedSourceIntent?.();
      const ticket = begin("cell");
      setFlowError(null);
      try {
        const response = await createDatasetCellCorrection(current.version_id, request);
        if (!isCurrent(ticket)) {
          notifyPersistedVersion();
          return null;
        }
        if (response.parent_version_id !== current.version_id || response.new_version.dataset_id !== current.dataset_id) throw contextMismatch();
        publishVersion(response.new_version);
        notifyPersistedVersion();
        return response;
      } catch (error) {
        if (!isCurrent(ticket)) return null;
        throw error;
      }
    },
    onConfirmParsing: () => { void handleConfirmParsing(); },
    onFileChange: handleFileChange,
    onLoadDatasetProfile: (versionId: string) => { void loadDatasetProfile(versionId); },
    onLoadRowsPreview: (versionId: string, offset: number) => { void loadRowsPreview(versionId, offset); },
    onPreviewLimitChange: handlePreviewLimitChange,
    onParsingOptionsChange: (options: ConfirmedParsingOptions) => {
      advanceSource();
      setParsingOptions(options);
    },
    onPasteDataset: handlePasteDataset,
    onSaveSchema: () => { void handleSaveSchema(); },
    onSchemaDraftChange: updateSchemaDraft,
    onUpload: (event: FormEvent<HTMLFormElement>) => { void handleUpload(event); },
  } satisfies DatasetPreparationPageProps;

  const activeDatasetSelectorProps = {
    catalogState: datasetVersionCatalogState, isSwitching: isSwitchingVersion,
    pendingVersionId, version, activationError,
    onRetrySwitch: () => { if (pending.current !== null) void activateDatasetVersion(pending.current); },
    onSelect: (versionId: string) => { void activateDatasetVersion(versionId); },
  } satisfies ActiveDatasetVersionSelectorProps;

  return { activeDatasetSelectorProps, datasetPageProps, flowError, profile, setFlowError, version, confirmNavigation, onDatasetDeleted };
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
