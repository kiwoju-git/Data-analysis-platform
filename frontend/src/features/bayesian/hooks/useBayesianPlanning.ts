import { useEffect, useRef, useState } from "react";
import * as api from "../../../api/boPlanning";
import type { BayesianStudyResponse } from "../../../api/types/bayesian";
import type { DesirabilityReviewRequest } from "../../../api/types/bayesianDesirability";
import type { CandidatePage, CandidateRevisionCreateRequest, CandidateRevisionSummary, CandidateRow, CandidateSource,
  PlanningConfirmRequest, PlanningEvaluationResponse, PlanningModelCreateRequest, PlanningModelDetail, PlanningModelSummary,
  PlanningSelectionCreateRequest, PlanningSelectionResponse, PlanningSelectionSummary } from "../../../api/types/boPlanning";
import { bayesianRequestId } from "../bayesianRequestId";
import { bayesianErrorCode } from "../bayesianDisplay";
import { sameDesirabilityJson } from "../desirabilityResponseGuard";
import { createPlanningCommitFence, createPlanningRequestFence, currentPlanningModel, emptyPlanningOrder, planningStudyKey, redoPlanningOrder, undoPlanningOrder,
  updatePlanningOrder, validPlanningBatch, validPlanningEvaluation, validPlanningModel, validPlanningPage, validPlanningSelection } from "../boPlanningDraft";

type Mutation = { kind: "fit"; request: PlanningModelCreateRequest }
  | { kind: "candidates"; request: CandidateRevisionCreateRequest; model: PlanningModelDetail }
  | { kind: "selection"; request: PlanningSelectionCreateRequest; model: PlanningModelDetail }
  | { kind: "confirm"; request: PlanningConfirmRequest; selection: PlanningSelectionResponse };
type Busy = Mutation["kind"] | "read" | "evaluate" | null;
type Profile = { axis: string | null; points: Record<string, number>[]; response: PlanningEvaluationResponse };
interface Options { study: BayesianStudyResponse; fitRequest: DesirabilityReviewRequest | null; disabled: boolean; onConfirmed: (batchId: string) => void }
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T;
const failure = (caught: unknown) => {
  const code = bayesianErrorCode(caught);
  return /^(bayesian_[a-z0-9_]{1,100}|api_unreachable|api_contract_mismatch|validation_error)$/.test(code) ? code : "bayesian_planning_request_failed";
};

export function useBayesianPlanning({ study, fitRequest, disabled, onConfirmed }: Options) {
  const sourceKey = planningStudyKey(study);
  const generation = useRef({ key: sourceKey, token: Symbol() });
  if (generation.current.key !== sourceKey) generation.current = { key: sourceKey, token: Symbol() };
  const token = generation.current.token;
  const mounted = useRef(false), catalogOperation = useRef(0);
  const operation = useRef(createPlanningRequestFence()).current;
  const confirmation = useRef(createPlanningCommitFence()).current;
  confirmation.source(`${study.study_id}:${study.study_version_id}:${study.definition_sha256}`);
  const mutationBusy = useRef(false);
  const current = () => mounted.current && generation.current.token === token;
  const [catalog, setCatalog] = useState<{ models: PlanningModelSummary[]; candidates: CandidateRevisionSummary[]; selections: PlanningSelectionSummary[] }>({ models: [], candidates: [], selections: [] });
  const [model, setModel] = useState<PlanningModelDetail | null>(null);
  const [page, setPage] = useState<CandidatePage | null>(null);
  const [order, setOrder] = useState(emptyPlanningOrder);
  const [selection, setSelection] = useState<PlanningSelectionResponse | null>(null);
  const [pageEvaluation, setPageEvaluation] = useState<PlanningEvaluationResponse | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [busy, setBusy] = useState<Busy>(null);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState<Mutation | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const stateOwner = useRef(token);
  const isOwner = stateOwner.current === token;
  const callback = useRef(onConfirmed); callback.current = onConfirmed;
  const fitFingerprint = JSON.stringify(fitRequest);
  operation.source(`${sourceKey}:${fitFingerprint}`);
  const fitEpoch = useRef(0);

  async function refreshCatalog() {
    if (!current()) return;
    const id = ++catalogOperation.current, active = () => current() && id === catalogOperation.current;
    setCatalogLoading(true);
    try {
      const models = await api.listPlanningModels(study.study_id);
      if (!active()) return;
      const candidates = await api.listCandidateSets(study.study_id);
      if (!active()) return;
      const selections = await api.listPlanningSelections(study.study_id);
      if (!active()) return;
      if (models.items.some(item => item.study_id !== study.study_id || item.study_version_id !== study.study_version_id) || selections.items.some(item => item.study_id !== study.study_id || item.study_version_id !== study.study_version_id || !Number.isInteger(item.selected_count) || item.selected_count < 1 || item.selected_count > 8)) throw new Error("bayesian_planning_response_mismatch");
      setCatalog({ models: models.items, candidates: candidates.items.filter(item => item.schema_version === 1), selections: selections.items });
    } catch (caught) { if (active()) setError(failure(caught)); }
    finally { if (active()) setCatalogLoading(false); }
  }
  const latestRefresh = useRef(refreshCatalog); latestRefresh.current = refreshCatalog;
  useEffect(() => {
    mounted.current = true; operation.invalidate(); catalogOperation.current += 1; mutationBusy.current = false; stateOwner.current = token;
    setModel(null); setPage(null); setOrder(emptyPlanningOrder()); setSelection(null); setPageEvaluation(null); setProfile(null);
    setBusy(null); setError(null); setRetry(null); setUncertain(false); setCatalog({ models: [], candidates: [], selections: [] });
    if (study.objective.goal_type === "desirability" && [5, 6].includes(study.study_schema_version)) void latestRefresh.current();
    return () => { mounted.current = false; operation.invalidate(); catalogOperation.current += 1; };
  }, [sourceKey, token, study.objective.goal_type, study.study_schema_version, operation]);
  useEffect(() => {
    fitEpoch.current += 1;
    if (!confirmation.pending()) { mutationBusy.current = false; setBusy(null); setRetry(null); setSelection(null); }
  }, [fitFingerprint, confirmation]);
  useEffect(() => () => confirmation.cancel(), [confirmation]);

  function invalidate() {
    if (confirmation.pending()) return false;
    operation.invalidate(); mutationBusy.current = false; setBusy(null); setError(null); setRetry(null);
    return true;
  }
  function editOrder(next: typeof order) {
    if (!current() || !isOwner) return;
    if (invalidate()) { setOrder(next); setSelection(null); }
  }
  function selectRow(row: CandidateRow) {
    const next = order.current.some(item => item.row_id === row.row_id) ? order.current.filter(item => item.row_id !== row.row_id) : [...order.current, row];
    editOrder(updatePlanningOrder(order, next));
  }
  function moveRow(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= order.current.length) return;
    const next = [...order.current]; [next[index], next[target]] = [next[target], next[index]];
    editOrder(updatePlanningOrder(order, next));
  }
  const canMutate = isOwner && currentPlanningModelSafe(model, study) && study.status === "active" && study.pending_trial_count === 0 && !disabled && !confirmation.pending();
  function sourceRequest() {
    if (!model || !canMutate) return null;
    return { model_id: model.model_id, expected_model_sha256: model.snapshot_sha256,
      expected_history_revision_id: study.observation_history.history_revision_id,
      expected_history_sha256: study.observation_history.observation_history_sha256, expected_trial_count: study.trial_count };
  }
  async function mutate(snapshot: Mutation) {
    if (!current() || disabled || mutationBusy.current || confirmation.pending()) return false;
    const commit = snapshot.kind === "confirm" ? confirmation.begin() : null;
    if (snapshot.kind === "confirm" && commit === null) return false;
    mutationBusy.current = true;
    const id = operation.begin(), epoch = fitEpoch.current;
    const computationCurrent = () => current() && operation.current(id) && epoch === fitEpoch.current;
    // A committed write belongs to its study, not to mutable candidate/profiler drafts.
    const active = () => commit === null ? computationCurrent() : mounted.current && confirmation.current(commit);
    setBusy(snapshot.kind); setError(null); setRetry(null);
    try {
      if (snapshot.kind === "fit") {
        const value = await api.createPlanningModel(study.study_id, snapshot.request);
        if (!active()) return false;
        if (!validPlanningModel(value, study) || !sameDesirabilityJson(value.fit, snapshot.request.fit)) throw new Error("bayesian_planning_response_mismatch");
        setModel(value); setPage(null); setOrder(emptyPlanningOrder()); setSelection(null); setPageEvaluation(null); setProfile(null);
      } else if (snapshot.kind === "candidates") {
        const value = await api.createCandidateRevision(study.study_id, snapshot.request);
        if (!active()) return false;
        if (!validPlanningPage(value, snapshot.model, study.factors) || value.revision.candidate_set_id !== snapshot.request.candidate_set_id || value.revision.parent_revision_id !== snapshot.request.expected_head_revision_id) throw new Error("bayesian_planning_response_mismatch");
        setPage(value); setOrder(emptyPlanningOrder()); setSelection(null); setPageEvaluation(null);
      } else if (snapshot.kind === "selection") {
        const value = await api.createPlanningSelection(study.study_id, snapshot.request);
        if (!active()) return false;
        if (!validPlanningSelection(value, snapshot.model, snapshot.request.candidate_revision_id, snapshot.request.expected_rows_sha256, snapshot.request.row_ids) || !sameDesirabilityJson(value.request, snapshot.request)) throw new Error("bayesian_planning_response_mismatch");
        setSelection(value);
      } else {
        const value = await api.confirmPlanningSelection(study.study_id, snapshot.selection.selection_id, snapshot.request);
        if (!active()) return false;
        if (!validPlanningBatch(value, study, snapshot.selection.selection_id) ||
          value.source.selection_id !== snapshot.selection.selection_id || value.source.selection_config_sha256 !== snapshot.selection.config_sha256 ||
          value.source.selection_result_sha256 !== snapshot.selection.result_sha256 || !sameDesirabilityJson(value.calculation, snapshot.selection.calculation)) throw new Error("bayesian_planning_response_mismatch");
        if (computationCurrent()) setSelection({ ...snapshot.selection, confirmed_batch_id: value.batch_id });
        callback.current(value.batch_id);
      }
      if (active()) { setUncertain(false); void latestRefresh.current(); }
      return true;
    } catch (caught) {
      if (active()) { setError(failure(caught)); setRetry(snapshot); setUncertain(true); }
      return false;
    } finally {
      if (active()) { mutationBusy.current = false; setBusy(null); }
      if (commit !== null) confirmation.finish(commit);
    }
  }
  function createModel() {
    if (!fitRequest || fitRequest.schema_version === 4 || study.objective.goal_type !== "desirability" || ![5, 6].includes(study.study_schema_version) || study.status !== "active" ||
      fitRequest.expected_history_revision_id !== study.observation_history.history_revision_id || fitRequest.expected_history_sha256 !== study.observation_history.observation_history_sha256) return;
    try { void mutate({ kind: "fit", request: { request_id: bayesianRequestId(), fit: clone(fitRequest) } }); }
    catch (caught) { setError(failure(caught)); }
  }
  function createCandidates(name: string, source: CandidateSource, replace: boolean) {
    const owner = sourceRequest();
    if (!owner || !model || !name.trim() || name.trim().length > 120 || (replace && !page) || ((source.kind === "append_rows" || source.kind === "remove_rows") && !replace)) return;
    try { void mutate({ kind: "candidates", model, request: { ...owner, request_id: bayesianRequestId(),
      candidate_set_id: replace && page ? page.revision.candidate_set_id : bayesianRequestId(), name: name.trim(),
      expected_head_revision_id: replace && page ? page.revision.revision_id : null, source: clone(source), include_constraint_violations: true } }); }
    catch (caught) { setError(failure(caught)); }
  }
  function saveSelection(totalBudget: number) {
    const owner = sourceRequest();
    if (!owner || !model || !page || !page.revision.source_is_current || page.revision.source_trial_count !== study.trial_count || order.current.length < 1 || order.current.length > 8 ||
      !Number.isInteger(totalBudget) || totalBudget > 200 || totalBudget < Math.max(2, study.trial_count + order.current.length)) return;
    try { void mutate({ kind: "selection", model, request: { ...owner, request_id: bayesianRequestId(), candidate_revision_id: page.revision.revision_id,
      expected_rows_sha256: page.revision.rows_sha256, row_ids: order.current.map(row => row.row_id), total_trial_budget: totalBudget } }); }
    catch (caught) { setError(failure(caught)); }
  }
  function confirm() {
    if (!selection || !canMutate || !selection.source_is_current || selection.confirmed_batch_id || selection.request.expected_trial_count !== study.trial_count || selection.request.row_ids.join() !== order.current.map(row => row.row_id).join()) return;
    void mutate({ kind: "confirm", selection, request: { expected_config_sha256: selection.config_sha256, expected_result_sha256: selection.result_sha256 } });
  }
  async function read(kind: "model" | "page" | "selection", identifier: string, offset = 0) {
    if (!current() || !invalidate()) return;
    const id = operation.begin(), active = () => current() && operation.current(id);
    setBusy("read");
    try {
      if (kind === "model") {
        const value = await api.fetchPlanningModel(study.study_id, identifier);
        if (!active()) return;
        if (!validPlanningModel(value, study) || value.model_id !== identifier) throw new Error("bayesian_planning_response_mismatch");
        setModel(value); setPage(null); setOrder(emptyPlanningOrder()); setSelection(null); setPageEvaluation(null); setProfile(null);
      } else if (kind === "page") {
        const value = await api.fetchCandidatePage(study.study_id, identifier, offset);
        if (!active()) return;
        if (value.revision.model_id === null) throw new Error("bayesian_planning_model_required");
        const owner = model?.model_id === value.revision.model_id ? model : await api.fetchPlanningModel(study.study_id, value.revision.model_id);
        if (!active()) return;
        if (!validPlanningModel(owner, study) || !validPlanningPage(value, owner, study.factors) || value.revision.revision_id !== identifier || value.offset !== offset) throw new Error("bayesian_planning_response_mismatch");
        if (page?.revision.revision_id !== identifier) { setOrder(emptyPlanningOrder()); setSelection(null); }
        if (model?.model_id !== owner.model_id) setProfile(null);
        setModel(owner); setPage(value); setPageEvaluation(null);
      } else {
        const value = await api.fetchPlanningSelection(study.study_id, identifier);
        if (!active()) return;
        const owner = await api.fetchPlanningModel(study.study_id, value.model_id);
        if (!active()) return;
        const candidates = await api.fetchCandidatePage(study.study_id, value.candidate_revision_id);
        if (!active()) return;
        if (value.selection_id !== identifier || !validPlanningModel(owner, study) || !validPlanningPage(candidates, owner, study.factors) || !validPlanningSelection(value, owner, candidates.revision.revision_id, candidates.revision.rows_sha256, value.request.row_ids)) throw new Error("bayesian_planning_response_mismatch");
        setModel(owner); setPage(candidates); setOrder({ past: [], current: value.calculation.items, future: [] }); setSelection(value); setPageEvaluation(null); setProfile(null);
      }
    } catch (caught) { if (active()) setError(failure(caught)); }
    finally { if (active()) setBusy(null); }
  }
  async function evaluate(points: Record<string, number>[], axis: string | null, target: "page" | "profile") {
    if (!current() || !model || disabled || points.length < 1 || points.length > 100) return;
    if (!invalidate()) return;
    const id = operation.begin(), active = () => current() && operation.current(id);
    const snapshot = clone(points), owner = model;
    setBusy("evaluate"); if (target === "profile") setProfile(null); else setPageEvaluation(null);
    try {
      const value = await api.evaluatePlanningModel(study.study_id, owner.model_id, { expected_model_sha256: owner.snapshot_sha256, points: snapshot, time_budget_ms: 60000 });
      if (!active()) return;
      if (!validPlanningEvaluation(value, owner, snapshot)) throw new Error("bayesian_planning_response_mismatch");
      if (target === "profile") setProfile({ axis, points: snapshot, response: value }); else setPageEvaluation(value);
    } catch (caught) { if (active()) setError(failure(caught)); }
    finally { if (active()) setBusy(null); }
  }
  async function startManual(modelId: string, points: Record<string, number>[], name: string) {
    if (!current() || disabled || study.status !== "active" || study.pending_trial_count !== 0 || points.length < 1 || points.length > 8 || !invalidate()) return;
    const id = operation.begin(), active = () => current() && operation.current(id);
    setBusy("read");
    try {
      const owner = await api.fetchPlanningModel(study.study_id, modelId);
      if (!active()) return;
      if (!currentPlanningModel(owner, study)) throw new Error("bayesian_planning_response_mismatch");
      setModel(owner); setPage(null); setOrder(emptyPlanningOrder()); setSelection(null); setPageEvaluation(null); setProfile(null);
      await mutate({ kind: "candidates", model: owner, request: { model_id: owner.model_id, expected_model_sha256: owner.snapshot_sha256,
        expected_history_revision_id: study.observation_history.history_revision_id, expected_history_sha256: study.observation_history.observation_history_sha256,
        expected_trial_count: study.trial_count, request_id: bayesianRequestId(), candidate_set_id: bayesianRequestId(), name, expected_head_revision_id: null,
        source: { kind: "explicit_rows", points: clone(points) }, include_constraint_violations: true } });
    } catch (caught) { if (active()) setError(failure(caught)); }
    finally { if (active()) setBusy(null); }
  }
  return { model: isOwner ? model : null, page: isOwner ? page : null, order: isOwner ? order : emptyPlanningOrder(),
    selection: isOwner ? selection : null, pageEvaluation: isOwner ? pageEvaluation : null, profile: isOwner ? profile : null,
    catalog: isOwner ? catalog : { models: [], candidates: [], selections: [] }, busy: isOwner ? busy : null, catalogLoading,
    isConfirming: confirmation.pending(),
    error: isOwner ? error : null, uncertain: isOwner && uncertain, canRetry: isOwner && retry !== null, canMutate,
    refreshCatalog, createModel, createCandidates, saveSelection, confirm, selectRow, moveRow, startManual,
    clearSelection: () => editOrder(updatePlanningOrder(order, [])), undo: () => editOrder(undoPlanningOrder(order)), redo: () => editOrder(redoPlanningOrder(order)),
    openModel: (id: string) => void read("model", id), openPage: (id: string, offset = 0) => void read("page", id, offset), openSelection: (id: string) => void read("selection", id),
    evaluatePage: () => page && void evaluate(page.items.map(row => row.actual_coordinates), null, "page"),
    evaluateProfile: (points: Record<string, number>[], axis: string | null) => void evaluate(points, axis, "profile"),
    invalidateDraft: () => { if (!invalidate()) return false; setSelection(null); return true; },
    invalidateProfile: () => { if (!invalidate()) return false; setProfile(null); return true; },
    retry: () => { if (retry) void mutate(retry); },
  };
}
function currentPlanningModelSafe(value: PlanningModelDetail | null, study: BayesianStudyResponse) {
  return value !== null && currentPlanningModel(value, study);
}
