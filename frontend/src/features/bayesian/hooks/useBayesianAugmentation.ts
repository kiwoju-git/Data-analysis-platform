import { useEffect, useRef, useState } from "react";
import * as api from "../../../api/boAugmentation";
import * as planning from "../../../api/boPlanning";
import type { AutoStrategyView } from "../../../api/boAutoStrategy";
import type { AutoEvidenceRequest, AugmentationPolicy } from "../../../api/types/boAugmentation";
import type { BayesianStudyResponse } from "../../../api/types/bayesian";
import type { AugmentationSelectionRequest, AugmentationSelectionResponse, CandidateRevisionCreateRequestV2 } from "../../../api/types/boAugmentation";
import type { CandidatePage, CandidateRevisionSummaryV2, CandidateSource, PlanningModelDetail, PlanningModelSummary } from "../../../api/types/boPlanning";
import { parseDoeResponseNumber } from "../../../doe/doeResponsePaste";
import { bayesianRequestId } from "../bayesianRequestId";
import { augmentationFailureCode as errorCode, augmentationRequest, augmentationSource, initialAugmentationDraft, validAugmentationBatch, validAugmentationPage, validAugmentationSelection, type AugmentationDraft } from "../boAugmentationDraft";
import { createPlanningCommitFence, createPlanningRequestFence, planningId, planningStudyKey, validPlanningModel } from "../boPlanningDraft";
import { sameDesirabilityJson } from "../desirabilityResponseGuard";

type Mutation = { kind: "candidates"; request: CandidateRevisionCreateRequestV2 } |
  { kind: "review"; request: AugmentationSelectionRequest } | { kind: "confirm"; selection: AugmentationSelectionResponse };
interface Options { study: BayesianStudyResponse; disabled: boolean; onConfirmed: (batchId: string) => void }

export function useBayesianAugmentation({ study, disabled, onConfirmed }: Options) {
  const key = planningStudyKey(study), ownerKey = `${study.study_id}:${study.study_version_id}:${study.definition_sha256}`;
  const generation = useRef({ key, token: Symbol() });
  if (generation.current.key !== key) generation.current = { key, token: Symbol() };
  const token = generation.current.token, stateOwner = useRef(token), mounted = useRef(false);
  const operation = useRef(createPlanningRequestFence()).current; operation.source(key);
  const confirmation = useRef(createPlanningCommitFence()).current; confirmation.source(ownerKey);
  const active = () => mounted.current && generation.current.token === token;
  const callback = useRef(onConfirmed); callback.current = onConfirmed;
  const catalogLane = useRef(0), running = useRef(false);
  const [catalog, setCatalog] = useState<{ candidates: CandidateRevisionSummaryV2[]; models: PlanningModelSummary[] }>({ candidates: [], models: [] });
  const [page, setPage] = useState<CandidatePage | null>(null), [model, setModel] = useState<PlanningModelDetail | null>(null);
  const [draft, setDraft] = useState(() => initialAugmentationDraft(study));
  const [autoReference, setAutoReference] = useState<AutoEvidenceRequest | null>(null);
  const [selection, setSelection] = useState<AugmentationSelectionResponse | null>(null);
  const [busy, setBusy] = useState<Mutation["kind"] | "read" | null>(null), [catalogLoading, setCatalogLoading] = useState(false);
  const [error, setError] = useState<string | null>(null), [retry, setRetry] = useState<Mutation | null>(null);
  const own = stateOwner.current === token;

  async function refresh() {
    const lane = ++catalogLane.current, current = () => active() && lane === catalogLane.current;
    setCatalogLoading(true);
    try {
      const candidates = await planning.listCandidateSets(study.study_id);
      if (!current()) return;
      const models = await planning.listPlanningModels(study.study_id);
      if (!current()) return;
      const rows = candidates.items.filter((item): item is CandidateRevisionSummaryV2 => item.schema_version === 2);
      if (rows.some(item => item.study_version_id !== study.study_version_id || item.definition_sha256 !== study.definition_sha256) ||
        models.items.some(item => item.study_id !== study.study_id || item.study_version_id !== study.study_version_id)) throw new Error("bayesian_augmentation_response_mismatch");
      setCatalog({ candidates: rows, models: models.items });
    } catch (caught) { if (current()) setError(errorCode(caught)); }
    finally { if (current()) setCatalogLoading(false); }
  }
  const latestRefresh = useRef(refresh); latestRefresh.current = refresh;
  useEffect(() => {
    mounted.current = true; stateOwner.current = token; operation.invalidate(); running.current = false;
    setAutoReference(null);
    setCatalog({ candidates: [], models: [] }); setPage(null); setModel(null); setDraft(initialAugmentationDraft(study)); setSelection(null); setError(null); setRetry(null);
    if (!confirmation.pending()) setBusy(null);
    void latestRefresh.current();
    return () => { mounted.current = false; operation.invalidate(); catalogLane.current += 1; };
    // The source key, not object identity or locale, owns this state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, token, operation, confirmation]);
  useEffect(() => () => confirmation.cancel(), [confirmation]);
  function invalidate(clearSelection = true) {
    if (!active() || confirmation.pending()) return false;
    operation.invalidate(); running.current = false; setBusy(null); setError(null); setRetry(null);
    if (clearSelection) setAutoReference(null);
    if (clearSelection) setSelection(null);
    return true;
  }
  function updateDraft<K extends keyof AugmentationDraft>(field: K, value: AugmentationDraft[K]) {
    if (invalidate()) setDraft(current => ({ ...current, [field]: value }));
  }
  function applyAuto(policy: AugmentationPolicy, view: AutoStrategyView) {
    if (!model || !view.apply_allowed || view.decision.recommended_policy !== policy ||
      view.diagnostic.model_id !== model.model_id || view.diagnostic.model_sha256 !== model.snapshot_sha256 ||
      view.diagnostic.history_sha256 !== study.observation_history.observation_history_sha256 || !invalidate()) return;
    setDraft(current => ({ ...current, policy }));
    setAutoReference({ schema_version: 1, routing_model_id: model.model_id,
      expected_model_sha256: model.snapshot_sha256, r_squared_threshold: view.decision.threshold,
      expected_decision_sha256: view.decision_sha256 });
  }
  async function mutate(snapshot: Mutation) {
    if (!active() || disabled || running.current || confirmation.pending()) return;
    const commit = snapshot.kind === "confirm" ? confirmation.begin() : null;
    if (snapshot.kind === "confirm" && commit === null) return;
    const requestToken = operation.begin(), current = () => active() && operation.current(requestToken);
    const ownerCurrent = () => commit === null ? current() : mounted.current && confirmation.current(commit);
    running.current = true; setBusy(snapshot.kind); setError(null); setRetry(null);
    try {
      if (snapshot.kind === "candidates") {
        setAutoReference(null);
        const value = await api.createAugmentationCandidates(study.study_id, snapshot.request);
        if (!ownerCurrent()) return;
        if (!validAugmentationPage(value, study) || value.revision.candidate_set_id !== snapshot.request.candidate_set_id || value.revision.parent_revision_id !== snapshot.request.expected_head_revision_id) throw new Error("bayesian_augmentation_response_mismatch");
        setPage(value); setSelection(null);
      } else if (snapshot.kind === "review") {
        const value = await api.createAugmentation(study.study_id, snapshot.request);
        if (!ownerCurrent()) return;
        if (!validAugmentationSelection(value, study, snapshot.request)) throw new Error("bayesian_augmentation_response_mismatch");
        setSelection(value);
      } else {
        const saved = snapshot.selection;
        const value = await api.confirmAugmentation(study.study_id, saved.selection_id, { expected_config_sha256: saved.config_sha256, expected_result_sha256: saved.result_sha256 });
        if (!ownerCurrent()) return;
        if (!validAugmentationBatch(value, study, saved.selection_id) || value.source.selection_config_sha256 !== saved.config_sha256 || value.source.selection_result_sha256 !== saved.result_sha256 ||
          !sameDesirabilityJson(value.calculation, saved.calculation)) throw new Error("bayesian_augmentation_response_mismatch");
        if (current()) setSelection({ ...saved, confirmed_batch_id: value.batch_id });
        callback.current(value.batch_id);
      }
      if (ownerCurrent()) void latestRefresh.current();
    } catch (caught) { if (ownerCurrent()) { setError(errorCode(caught)); setRetry(snapshot); } }
    finally {
      if (ownerCurrent()) { setBusy(null); running.current = false; }
      if (commit !== null) confirmation.finish(commit);
    }
  }
  function createCandidates(name: string, source: CandidateSource, toleranceDraft: string, replace = false) {
    const tolerance = parseDoeResponseNumber(toleranceDraft);
    if (!own || study.status !== "active" || tolerance === null || tolerance < 1e-12 || tolerance > .1 || !name.trim() || name.trim().length > 120 || (replace && !page)) return;
    try { void mutate({ kind: "candidates", request: { ...augmentationSource(study), schema_version: 2, request_id: bayesianRequestId(),
      candidate_set_id: replace && page ? page.revision.candidate_set_id : bayesianRequestId(), expected_head_revision_id: replace && page ? page.revision.revision_id : null,
      name: name.trim(), model_id: null, expected_model_sha256: null, duplicate_tolerance: tolerance, source: JSON.parse(JSON.stringify(source)) as CandidateSource, include_constraint_violations: true } }); }
    catch (caught) { setError(errorCode(caught)); }
  }
  async function read(kind: "page" | "model" | "selection", id: string, offset = 0) {
    if (!planningId(id) || !invalidate(kind !== "page" || page?.revision.revision_id !== id)) return;
    const requestToken = operation.begin(), current = () => active() && operation.current(requestToken);
    setBusy("read");
    try {
      if (kind === "page") {
        const value = await planning.fetchCandidatePage(study.study_id, id, offset);
        if (!current()) return;
        if (!validAugmentationPage(value, study) || value.revision.revision_id !== id || value.offset !== offset) throw new Error("bayesian_augmentation_response_mismatch");
        setPage(value);
      } else if (kind === "model") {
        const value = await planning.fetchPlanningModel(study.study_id, id);
        if (!current()) return;
        if (!validPlanningModel(value, study) || value.model_id !== id) throw new Error("bayesian_augmentation_response_mismatch");
        setModel(value);
      } else {
        const value = await api.fetchAugmentation(study.study_id, id);
        if (!current()) return;
        if (value.selection_id !== id || !validAugmentationSelection(value, study)) throw new Error("bayesian_augmentation_response_mismatch");
        const candidates = await planning.fetchCandidatePage(study.study_id, value.candidate_revision_id);
        if (!current()) return;
        if (!validAugmentationPage(candidates, study) || candidates.revision.rows_sha256 !== value.request.expected_rows_sha256) throw new Error("bayesian_augmentation_response_mismatch");
        let fitted: PlanningModelDetail | null = null;
        if (value.model_id !== null) {
          fitted = await planning.fetchPlanningModel(study.study_id, value.model_id);
          if (!current()) return;
          if (!validPlanningModel(fitted, study) || fitted.snapshot_sha256 !== value.request.expected_model_sha256) throw new Error("bayesian_augmentation_response_mismatch");
        }
        setPage(candidates); setModel(fitted); setSelection(value);
        setDraft({ policy: value.request.policy, batchSize: String(value.request.batch_size), budget: String(value.request.total_trial_budget), distance: String(value.request.min_batch_distance_normalized),
          evaluations: String(value.request.max_evaluations), moments: String(value.request.max_moment_evaluations), seconds: String(value.request.time_budget_ms / 1000) });
      }
    } catch (caught) { if (current()) setError(errorCode(caught)); }
    finally { if (current()) setBusy(null); }
  }
  const basePreview = own ? augmentationRequest(study, page, model, draft, "00000000-0000-0000-0000-000000000000") : null;
  const preview: AugmentationSelectionRequest | null = basePreview && autoReference
    ? { ...basePreview, schema_version: 4, auto_strategy: autoReference } : basePreview;
  const canConfirm = own && selection !== null && selection.source_is_current && selection.confirmed_batch_id === null && study.status === "active" && study.pending_trial_count === 0 &&
    selection.request.expected_history_revision_id === study.observation_history.history_revision_id && selection.request.expected_history_sha256 === study.observation_history.observation_history_sha256 && selection.request.expected_trial_count === study.trial_count;
  return { catalog: own ? catalog : { models: [], candidates: [] }, page: own ? page : null, model: own ? model : null,
    draft: own ? draft : initialAugmentationDraft(study), selection: own ? selection : null, busy: own ? busy : null, catalogLoading,
    error: own ? error : null, canRetry: own && retry !== null, isConfirming: confirmation.pending(), canReview: preview !== null, canConfirm,
    updateDraft, applyAuto, clearAuto: () => { if (autoReference) invalidate(); }, autoReference,
    invalidateDraft: invalidate, createCandidates, refresh,
    openPage: (id: string, offset = 0) => void read("page", id, offset), openModel: (id: string) => void read("model", id), openSelection: (id: string) => void read("selection", id),
    review: () => { if (preview) { try { void mutate({ kind: "review", request: { ...preview, request_id: bayesianRequestId() } }); } catch (caught) { setError(errorCode(caught)); } } },
    confirm: () => { if (canConfirm && selection) void mutate({ kind: "confirm", selection }); },
    retry: () => { if (retry) void mutate(retry); },
  };
}
