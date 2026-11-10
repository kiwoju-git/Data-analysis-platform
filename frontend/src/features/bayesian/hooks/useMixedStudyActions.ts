import { useEffect, useRef, useState } from "react";
import * as api from "../../../api/boMixed";
import type { BayesianReplicateCreateRequest, BayesianStudyCloseRequest, BayesianTrialAbandonRequest } from "../../../api/types/bayesian";
import type { MixedObservationBatchRequest, MixedStudyResponse } from "../../../api/types/boMixed";
import { augmentationFailureCode } from "../boAugmentationDraft";
import { buildMixedObservations, mixedStudyKey, validMixedObservationCommit, validMixedStudy, validateMixedCoordinates } from "../boMixedDraft";
import { createPlanningCommitFence, createPlanningRequestFence, planningHash, planningId } from "../boPlanningDraft";
import { sameDesirabilityJson } from "../desirabilityResponseGuard";
import { bayesianRequestId } from "../bayesianRequestId";
import type { VectorObservationDraft } from "../bayesianVectorDraft";

type Mutation = { kind: "observations"; request: MixedObservationBatchRequest } |
  { kind: "replicates"; trialId: string; request: BayesianReplicateCreateRequest } |
  { kind: "abandon"; trialId: string; request: BayesianTrialAbandonRequest } |
  { kind: "close"; request: BayesianStudyCloseRequest };
interface Options { study: MixedStudyResponse; disabled: boolean; onCommitted: (study: MixedStudyResponse, expectedHistory: string) => void; onRefresh: () => void }

export function useMixedStudyActions({ study, disabled, onCommitted, onRefresh }: Options) {
  const key = mixedStudyKey(study), owner = `${study.study_id}:${study.study_version_id}:${study.definition_sha256}`;
  const generation = useRef({ key, token: Symbol() }); if (generation.current.key !== key) generation.current = { key, token: Symbol() };
  const token = generation.current.token, storedOwner = useRef(token), mounted = useRef(false);
  const guard = useRef(createPlanningRequestFence()).current; guard.source(key);
  const commit = useRef(createPlanningCommitFence()).current; commit.source(owner);
  const [draft, setDraft] = useState<VectorObservationDraft>({}), [preview, setPreview] = useState<Mutation | null>(null), [retry, setRetry] = useState<Mutation | null>(null);
  const [error, setError] = useState<string | null>(null), [busy, setBusy] = useState(false);
  const callbacks = useRef({ onCommitted, onRefresh }); callbacks.current = { onCommitted, onRefresh };
  const current = () => mounted.current && generation.current.token === token;
  useEffect(() => {
    mounted.current = true; storedOwner.current = token; guard.invalidate(); setDraft({}); setPreview(null); setRetry(null); setError(null);
    if (!commit.pending()) setBusy(false);
    return () => { mounted.current = false; guard.invalidate(); };
  }, [key, token, guard, commit]);
  useEffect(() => () => commit.cancel(), [commit]);
  function invalidate() { if (!current() || commit.pending()) return false; guard.invalidate(); setPreview(null); setRetry(null); setError(null); return true; }
  function update(trialId: string, responseId: string, value: string) {
    if (!invalidate() || study.status !== "active" || !study.trials.some(row => row.trial_id === trialId && row.state === "pending") || !study.objective.responses.some(row => row.response_id === responseId)) return;
    setDraft(rows => ({ ...rows, [trialId]: { ...rows[trialId], [responseId]: value } }));
  }
  function reviewObservations() {
    if (!invalidate() || disabled) return;
    try { const request = buildMixedObservations(study, draft, bayesianRequestId());
      if (typeof request === "string") setError(request); else setPreview({ kind: "observations", request });
    } catch (caught) { setError(augmentationFailureCode(caught)); }
  }
  async function mutate(snapshot: Mutation) {
    if (!current() || disabled || study.status !== "active" || commit.pending()) return;
    const identity = commit.begin(); if (identity === null) return;
    const active = () => mounted.current && commit.current(identity);
    setBusy(true); setError(null); setRetry(null);
    const history = study.observation_history.observation_history_sha256;
    try {
      if (snapshot.kind === "observations") {
        const value = await api.recordMixedObservations(study.study_id, snapshot.request);
        if (!active()) return;
        if (!validMixedObservationCommit(value, study, snapshot.request)) throw new Error("bayesian_mixed_observation_source_mismatch");
        callbacks.current.onCommitted(value.study, history);
      } else if (snapshot.kind === "replicates") {
        const value = await api.createMixedReplicates(study.study_id, snapshot.trialId, snapshot.request);
        if (!active()) return;
        const parent = study.trials.find(row => row.trial_id === snapshot.trialId);
        if (value.schema_version !== 2 || value.study_id !== study.study_id || value.study_version_id !== study.study_version_id || value.parent_trial_id !== snapshot.trialId ||
          value.request_id !== snapshot.request.request_id || value.source_history_revision_id !== study.observation_history.history_revision_id || value.source_history_sha256 !== history ||
          !planningHash(value.request_sha256) || value.trials.length !== snapshot.request.count || new Set(value.trials.map(row => row.trial_id)).size !== value.trials.length ||
          !parent || value.trials.some(row => !planningId(row.trial_id) || row.origin !== "replicate" || row.replicate_of_trial_id !== parent.trial_id || row.state !== "pending" || row.response_values !== null ||
            !sameDesirabilityJson(row.actual_coordinates, parent.actual_coordinates) || !validateMixedCoordinates(row.actual_coordinates, row.encoded_coordinates, study.factors))) throw new Error("bayesian_mixed_replicate_source_mismatch");
        callbacks.current.onRefresh();
      } else if (snapshot.kind === "abandon") {
        const value = await api.abandonMixedTrial(study.study_id, snapshot.trialId, snapshot.request);
        if (!active()) return;
        if (value.study_id !== study.study_id || value.trial.trial_id !== snapshot.trialId || value.trial.study_version_id !== study.study_version_id || value.trial.state !== "abandoned" ||
          !sameDesirabilityJson(value.trial.actual_coordinates, study.trials.find(row => row.trial_id === snapshot.trialId)?.actual_coordinates)) throw new Error("bayesian_mixed_trial_source_mismatch");
        callbacks.current.onRefresh();
      } else {
        const value = await api.closeMixedStudy(study.study_id, snapshot.request);
        if (!active()) return;
        if (!validMixedStudy(value.study, study.study_id) || value.study.study_version_id !== study.study_version_id || value.study.definition_sha256 !== study.definition_sha256 ||
          value.study.status !== snapshot.request.target_status || value.lifecycle_event.request_id !== snapshot.request.request_id || value.lifecycle_event.final_observation_history_sha256 !== history ||
          !planningHash(value.lifecycle_event.event_sha256)) throw new Error("bayesian_mixed_close_source_mismatch");
        callbacks.current.onCommitted(value.study, history);
      }
      if (active()) { setPreview(null); setDraft({}); }
    } catch (caught) { if (active()) { setError(augmentationFailureCode(caught)); setRetry(snapshot); } }
    finally { if (active()) setBusy(false); commit.finish(identity); }
  }
  function requestReplicates(trialId: string, count: number, budget: number, intent: boolean) {
    if (!invalidate() || disabled || study.status !== "active" || study.pending_trial_count !== 0 || !intent || !Number.isInteger(count) || count < 1 || count > 8 ||
      !Number.isInteger(budget) || budget < study.trial_count + count || budget > 200 || !study.trials.some(row => row.trial_id === trialId && row.state === "completed")) return;
    try { setPreview({ kind: "replicates", trialId, request: { request_id: bayesianRequestId(), expected_history_revision_id: study.observation_history.history_revision_id,
      expected_history_sha256: study.observation_history.observation_history_sha256, count, total_trial_budget: budget, confirm_replicate_intent: true } }); }
    catch (caught) { setError(augmentationFailureCode(caught)); }
  }
  function requestAbandon(trialId: string, closing: boolean) {
    if (!invalidate() || disabled || study.status !== "active" || !study.trials.some(row => row.trial_id === trialId && row.state === "pending")) return;
    setPreview({ kind: "abandon", trialId, request: { expected_history_revision_id: study.observation_history.history_revision_id, intent: closing ? "close_study" : "continue_study" } });
  }
  function requestClose(target: "completed" | "abandoned", reason: BayesianStudyCloseRequest["reason_code"], note: string) {
    if (!invalidate() || disabled || study.status !== "active" || study.pending_trial_count !== 0 || note.length > 2000) return;
    try { setPreview({ kind: "close", request: { request_id: bayesianRequestId(), target_status: target, reason_code: reason, note: note.trim() || null,
      expected_study_version_id: study.study_version_id, expected_history_revision_id: study.observation_history.history_revision_id,
      expected_observation_history_sha256: study.observation_history.observation_history_sha256 } }); }
    catch (caught) { setError(augmentationFailureCode(caught)); }
  }
  const own = storedOwner.current === token;
  return { draft: own ? draft : {}, preview: own ? preview : null, error: own ? error : null, canRetry: own && retry !== null, busy: busy || commit.pending(),
    update, reviewObservations, requestReplicates, requestAbandon, requestClose, cancel: invalidate,
    confirm: () => { if (preview && own) void mutate(preview); }, retry: () => { if (retry && own) void mutate(retry); } };
}
