import { useEffect, useRef, useState } from "react";
import * as api from "../../../api/boMixed";
import type { AutoStrategyView } from "../../../api/boAutoStrategy";
import type { AugmentationPolicy, AutoEvidenceRequest } from "../../../api/types/boAugmentation";
import type { EvaluatedMixedCandidateRow, MixedActualPoint, MixedCandidateCreateRequest, MixedCandidatePage, MixedCandidateSource, MixedCandidateSummary, MixedModelCreateRequest, MixedModelDetail, MixedModelSummary, MixedSelectionRequest, MixedSelectionResponse, MixedSelectionSummary, MixedStudyResponse } from "../../../api/types/boMixed";
import { bayesianRequestId } from "../bayesianRequestId";
import { augmentationFailureCode } from "../boAugmentationDraft";
import { mixedStudyKey } from "../boMixedDraft";
import { initialMixedFit, initialMixedSelection, mixedFitDraftFromModel, mixedFitOptions, mixedSelectionRequest, mixedSource, validMixedBatch, validMixedModel, validMixedPage, validMixedPrediction, validMixedSelection, type MixedFitDraft, type MixedSelectionDraft } from "../boMixedPlanningDraft";
import { createPlanningCommitFence, createPlanningRequestFence, planningId } from "../boPlanningDraft";
import { sameDesirabilityJson } from "../desirabilityResponseGuard";

type Mutation = { kind: "fit"; request: MixedModelCreateRequest } | { kind: "candidates"; request: MixedCandidateCreateRequest } | { kind: "review"; request: MixedSelectionRequest } | { kind: "confirm"; selection: MixedSelectionResponse };
export interface MixedProfile { modelId: string; modelHash: string; points: MixedActualPoint[]; axis: string | null; rows: EvaluatedMixedCandidateRow[] }
interface Options { study: MixedStudyResponse; disabled: boolean; onConfirmed: (id: string) => void }
export function useMixedPlanning({ study, disabled, onConfirmed }: Options) {
  const key = mixedStudyKey(study), owner = `${study.study_id}:${study.study_version_id}:${study.definition_sha256}`;
  const generation = useRef({ key, token: Symbol() });
  if (generation.current.key !== key) generation.current = { key, token: Symbol() };
  const token = generation.current.token, stateOwner = useRef(token), mounted = useRef(false), running = useRef(false), catalogLane = useRef(0);
  const fence = useRef(createPlanningRequestFence()).current; fence.source(key);
  const commit = useRef(createPlanningCommitFence()).current; commit.source(owner);
  const active = () => mounted.current && token === generation.current.token;
  const callback = useRef(onConfirmed); callback.current = onConfirmed;
  const [models, setModels] = useState<MixedModelSummary[]>([]), [candidates, setCandidates] = useState<MixedCandidateSummary[]>([]), [selections, setSelections] = useState<MixedSelectionSummary[]>([]);
  const [model, setModel] = useState<MixedModelDetail | null>(null), [page, setPage] = useState<MixedCandidatePage | null>(null), [selection, setSelection] = useState<MixedSelectionResponse | null>(null);
  const [fitDraft, setFitDraft] = useState(() => initialMixedFit(study)), [draft, setDraft] = useState(initialMixedSelection);
  const [autoReference, setAutoReference] = useState<AutoEvidenceRequest | null>(null);
  const [order, setOrder] = useState<{ past: string[][]; current: string[]; future: string[][] }>({ past: [], current: [], future: [] });
  const [profile, setProfile] = useState<MixedProfile | null>(null), [evaluatedPage, setEvaluatedPage] = useState<{ revision: string; offset: number; model: string; rows: EvaluatedMixedCandidateRow[] } | null>(null);
  const [busy, setBusy] = useState<Mutation["kind"] | "read" | "evaluate" | null>(null), [loading, setLoading] = useState(false), [error, setError] = useState<string | null>(null), [retry, setRetry] = useState<Mutation | null>(null);
  const own = stateOwner.current === token;
  async function refresh() {
    const lane = ++catalogLane.current, current = () => active() && lane === catalogLane.current;
    setLoading(true);
    try {
      const modelList = await api.listMixedModels(study.study_id); if (!current()) return;
      const candidateList = await api.listMixedCandidateSets(study.study_id); if (!current()) return;
      const selectionList = await api.listMixedSelections(study.study_id); if (!current()) return;
      if (modelList.items.some(item => item.schema_version !== 2 || item.study_id !== study.study_id || item.study_version_id !== study.study_version_id) ||
        candidateList.items.some(item => item.schema_version !== 3 || item.study_version_id !== study.study_version_id || item.definition_sha256 !== study.definition_sha256) ||
        selectionList.items.some(item => ![3, 5].includes(item.schema_version) || item.study_id !== study.study_id || item.study_version_id !== study.study_version_id)) throw new Error("bayesian_mixed_response_mismatch");
      setModels(modelList.items); setCandidates(candidateList.items); setSelections(selectionList.items);
    } catch (caught) { if (current()) setError(augmentationFailureCode(caught)); }
    finally { if (current()) setLoading(false); }
  }
  const latestRefresh = useRef(refresh); latestRefresh.current = refresh;
  useEffect(() => {
    mounted.current = true; stateOwner.current = token; fence.invalidate(); running.current = false;
    setAutoReference(null);
    setModel(null); setPage(null); setSelection(null); setProfile(null); setEvaluatedPage(null); setOrder({ past: [], current: [], future: [] }); setFitDraft(initialMixedFit(study)); setDraft(initialMixedSelection());
    setModels([]); setCandidates([]); setSelections([]); setError(null); setRetry(null); if (!commit.pending()) setBusy(null);
    void latestRefresh.current();
    return () => { mounted.current = false; fence.invalidate(); catalogLane.current += 1; };
    // Stable source identity, not locale or wrapper identity, owns these requests.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, token, fence, commit]);
  useEffect(() => () => commit.cancel(), [commit]);
  function invalidate(clearReview = true) {
    if (!active() || commit.pending()) return false;
    fence.invalidate(); running.current = false; setBusy(null); setError(null); setRetry(null); if (clearReview) setSelection(null);
    if (clearReview) setAutoReference(null);
    return true;
  }
  function applyAuto(policy: AugmentationPolicy, view: AutoStrategyView) {
    if (!model || !view.apply_allowed || view.decision.recommended_policy !== policy ||
      view.diagnostic.model_id !== model.model_id || view.diagnostic.model_sha256 !== model.snapshot_sha256 ||
      view.diagnostic.history_sha256 !== study.observation_history.observation_history_sha256 || !invalidate()) return;
    setDraft(current => ({ ...current, kind: "augmentation", policy }));
    setAutoReference({ schema_version: 1, routing_model_id: model.model_id,
      expected_model_sha256: model.snapshot_sha256, r_squared_threshold: view.decision.threshold,
      expected_decision_sha256: view.decision_sha256 });
  }
  async function mutate(snapshot: Mutation) {
    if (!active() || disabled || running.current || commit.pending()) return;
    const committed = snapshot.kind === "confirm" ? commit.begin() : null;
    if (snapshot.kind === "confirm" && committed === null) return;
    const requestToken = fence.begin(), current = () => active() && fence.current(requestToken), ownerCurrent = () => committed === null ? current() : mounted.current && commit.current(committed);
    running.current = true; setBusy(snapshot.kind); setError(null); setRetry(null);
    if (snapshot.kind === "fit" || snapshot.kind === "candidates") setAutoReference(null);
    try {
      if (snapshot.kind === "fit") {
        const value = await api.createMixedModel(study.study_id, snapshot.request); if (!current()) return;
        if (!validMixedModel(value, study) || !sameDesirabilityJson(value.fit, snapshot.request.fit)) throw new Error("bayesian_mixed_response_mismatch");
        setModel(value); setProfile(null); setEvaluatedPage(null); setSelection(null);
      } else if (snapshot.kind === "candidates") {
        const value = await api.createMixedCandidateRevision(study.study_id, snapshot.request); if (!current()) return;
        if (!validMixedPage(value, study) || value.revision.candidate_set_id !== snapshot.request.candidate_set_id || value.revision.parent_revision_id !== snapshot.request.expected_head_revision_id ||
          value.revision.ordinal_rank_distance !== snapshot.request.ordinal_rank_distance || value.revision.duplicate_tolerance !== snapshot.request.duplicate_tolerance) throw new Error("bayesian_mixed_response_mismatch");
        setPage(value); setSelection(null); setEvaluatedPage(null); setOrder({ past: [], current: [], future: [] });
      } else if (snapshot.kind === "review") {
        const value = await api.createMixedSelection(study.study_id, snapshot.request); if (!current()) return;
        if (!validMixedSelection(value, study, snapshot.request)) throw new Error("bayesian_mixed_response_mismatch");
        setSelection(value);
      } else {
        const saved = snapshot.selection;
        const value = await api.confirmMixedSelection(study.study_id, saved.selection_id, { expected_config_sha256: saved.config_sha256, expected_result_sha256: saved.result_sha256 });
        if (!ownerCurrent()) return;
        if (!validMixedBatch(value, study, saved.selection_id) || value.source.selection_config_sha256 !== saved.config_sha256 || value.source.selection_result_sha256 !== saved.result_sha256 || !sameDesirabilityJson(value.calculation, saved.calculation)) throw new Error("bayesian_mixed_response_mismatch");
        if (current()) setSelection({ ...saved, confirmed_batch_id: value.batch_id });
        callback.current(value.batch_id);
      }
      if (ownerCurrent()) void latestRefresh.current();
    } catch (caught) { if (ownerCurrent()) { setError(augmentationFailureCode(caught)); setRetry(snapshot); } }
    finally { if (ownerCurrent()) { setBusy(null); running.current = false; } if (committed !== null) commit.finish(committed); }
  }
  async function read(kind: "page" | "model" | "selection", id: string, offset = 0) {
    if (!planningId(id) || !invalidate(kind !== "page" || page?.revision.revision_id !== id)) return;
    const requestToken = fence.begin(), current = () => active() && fence.current(requestToken); setBusy("read");
    try {
      if (kind === "model") {
        const value = await api.fetchMixedModel(study.study_id, id); if (!current()) return;
        if (!validMixedModel(value, study) || value.model_id !== id) throw new Error("bayesian_mixed_response_mismatch");
        setModel(value); setFitDraft(mixedFitDraftFromModel(value)); setProfile(null); setEvaluatedPage(null);
      } else if (kind === "page") {
        const value = await api.fetchMixedCandidatePage(study.study_id, id, offset); if (!current()) return;
        if (!validMixedPage(value, study) || value.revision.revision_id !== id || value.offset !== offset) throw new Error("bayesian_mixed_response_mismatch");
        if (page?.revision.revision_id !== id) setOrder({ past: [], current: [], future: [] });
        setPage(value); setEvaluatedPage(null);
      } else {
        const value = await api.fetchMixedSelection(study.study_id, id); if (!current()) return;
        if (!validMixedSelection(value, study) || value.selection_id !== id) throw new Error("bayesian_mixed_response_mismatch");
        const candidatePage = await api.fetchMixedCandidatePage(study.study_id, value.candidate_revision_id); if (!current()) return;
        if (!validMixedPage(candidatePage, study) || candidatePage.revision.rows_sha256 !== value.request.expected_rows_sha256) throw new Error("bayesian_mixed_response_mismatch");
        let fitted: MixedModelDetail | null = null;
        if (value.model_id) { fitted = await api.fetchMixedModel(study.study_id, value.model_id); if (!current()) return; if (!validMixedModel(fitted, study) || fitted.snapshot_sha256 !== value.request.expected_model_sha256) throw new Error("bayesian_mixed_response_mismatch"); }
        setPage(candidatePage); setModel(fitted); if (fitted) setFitDraft(mixedFitDraftFromModel(fitted)); setSelection(value); setProfile(null); setEvaluatedPage(null);
        setOrder({ past: [], current: [...value.request.row_ids], future: [] });
        setDraft({ kind: value.request.kind, policy: value.request.policy ?? "greedy_mixed_maximin_v1", batchSize: String(value.request.batch_size), budget: String(value.request.total_trial_budget), distance: String(value.request.min_batch_distance),
          samples: String(value.request.sample_count), evaluations: String(value.request.max_evaluations), moments: String(value.request.max_moment_evaluations), seconds: String(value.request.time_budget_ms / 1000) });
      }
    } catch (caught) { if (current()) setError(augmentationFailureCode(caught)); }
    finally { if (current()) setBusy(null); }
  }
  async function evaluate(points: MixedActualPoint[], axis: string | null, forPage = false) {
    if (!model || disabled || running.current || !invalidate(false)) return;
    const saved = model, savedPage = page, requestToken = fence.begin(), current = () => active() && fence.current(requestToken);
    running.current = true; setBusy("evaluate");
    try {
      const value = await api.evaluateMixedModel(study.study_id, saved.model_id, { expected_model_sha256: saved.snapshot_sha256, points, time_budget_ms: 60000, max_moment_evaluations: 65536 });
      if (!current()) return;
      if (value.model_id !== saved.model_id || value.snapshot_sha256 !== saved.snapshot_sha256 || value.model_refit !== false || value.items.length !== points.length ||
        value.items.some((row, index) => !validMixedPrediction(row, study) || !sameDesirabilityJson(row.input_coordinates, points[index]))) throw new Error("bayesian_mixed_response_mismatch");
      if (forPage && savedPage) setEvaluatedPage({ revision: savedPage.revision.revision_id, offset: savedPage.offset, model: saved.model_id, rows: value.items });
      else setProfile({ modelId: saved.model_id, modelHash: saved.snapshot_sha256, points, axis, rows: value.items });
    } catch (caught) { if (current()) setError(augmentationFailureCode(caught)); }
    finally { if (current()) { running.current = false; setBusy(null); } }
  }
  function reorder(next: string[]) {
    if (!invalidate() || next.length > 8 || new Set(next).size !== next.length) return;
    setOrder(value => ({ past: [...value.past.slice(-49), value.current], current: [...next], future: [] }));
  }
  function submit(make: () => Mutation) {
    try { void mutate(make()); } catch (caught) { if (active()) setError(augmentationFailureCode(caught)); }
  }
  const fit = mixedFitOptions(study, fitDraft), preview = own ? mixedSelectionRequest(study, page, model, order.current, draft, "00000000-0000-0000-0000-000000000000", autoReference) : null;
  const canConfirm = own && selection !== null && selection.source_is_current && selection.confirmed_batch_id === null && study.status === "active" && study.pending_trial_count === 0 && selection.request.expected_history_revision_id === study.observation_history.history_revision_id && selection.request.expected_history_sha256 === study.observation_history.observation_history_sha256 && selection.request.expected_trial_count === study.trial_count;
  return { key, model: own ? model : null, page: own ? page : null, selection: own ? selection : null, fitDraft, draft, models: own ? models : [], candidates: own ? candidates : [], selections: own ? selections : [],
    selectedIds: own ? order.current : [], canUndo: own && order.past.length > 0, canRedo: own && order.future.length > 0, profile: own ? profile : null, evaluatedPage: own ? evaluatedPage : null,
    busy: own ? busy : null, loading, error: own ? error : null, canFit: fit !== null && study.status === "active" && study.completed_trial_count >= Math.max(2, study.factors.length + 1), canReview: preview !== null, canConfirm, canRetry: own && retry !== null, isConfirming: commit.pending(),
    refresh, invalidate, applyAuto, autoReference: own ? autoReference : null, updateFit: (next: MixedFitDraft) => { if (invalidate()) setFitDraft(next); }, updateDraft: (next: MixedSelectionDraft) => { if (invalidate()) setDraft(next); },
    fit: () => { if (fit) submit(() => ({ kind: "fit", request: { ...mixedSource(study), request_id: bayesianRequestId(), fit } })); },
    createCandidates: (name: string, source: MixedCandidateSource, tolerance: number, ordinal: boolean, append = false) => {
      if (!name.trim() || name.trim().length > 120 || !Number.isFinite(tolerance) || tolerance < 1e-12 || tolerance > .1 || (append && !page) || study.status !== "active") return;
      submit(() => ({ kind: "candidates", request: { ...mixedSource(study), schema_version: 3, request_id: bayesianRequestId(), candidate_set_id: append && page ? page.revision.candidate_set_id : bayesianRequestId(), name: name.trim(), expected_head_revision_id: append && page ? page.revision.revision_id : null,
        model_id: null, expected_model_sha256: null, duplicate_tolerance: tolerance, ordinal_rank_distance: ordinal, include_constraint_violations: true, source } }));
    },
    openModel: (id: string) => void read("model", id), openPage: (id: string, offset = 0) => void read("page", id, offset), openSelection: (id: string) => void read("selection", id),
    evaluate, evaluatePage: () => { if (page) void evaluate(page.items.map(row => row.actual_coordinates), null, true); },
    reorder, undo: () => { if (order.past.length && invalidate()) setOrder(value => ({ past: value.past.slice(0, -1), current: value.past[value.past.length - 1], future: [value.current, ...value.future] })); },
    redo: () => { if (order.future.length && invalidate()) setOrder(value => ({ past: [...value.past, value.current], current: value.future[0], future: value.future.slice(1) })); },
    review: () => { if (preview) submit(() => ({ kind: "review", request: { ...preview, request_id: bayesianRequestId() } })); },
    confirm: () => { if (canConfirm && selection) void mutate({ kind: "confirm", selection }); }, retry: () => { if (retry) void mutate(retry); },
  };
}
