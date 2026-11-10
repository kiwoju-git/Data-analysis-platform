import { useEffect, useRef, useState } from "react";
import { recordBayesianObservationsBatch, type BayesianObservationBatchCreateRequest, type BayesianStudyResponse } from "../../../api";
import { createLatestRequestGuard } from "../../../latestRequest";
import { bayesianRequestId } from "../bayesianRequestId";
import { bayesianErrorCode } from "../bayesianDisplay";
import { vectorObservationEntries, vectorStudySourceKey, type VectorObservationDraft } from "../bayesianVectorDraft";

interface Review { sourceKey: string; request: BayesianObservationBatchCreateRequest }
export function useBayesianVectorEntry(study: BayesianStudyResponse, onCommitted: (study: BayesianStudyResponse, source: string) => void) {
  const sourceKey = vectorStudySourceKey(study);
  const liveSource = useRef(sourceKey);
  liveSource.current = sourceKey;
  const generation = useRef({ sourceKey, token: Symbol() });
  if (generation.current.sourceKey !== sourceKey) generation.current = { sourceKey, token: Symbol() };
  const token = generation.current.token;
  const mounted = useRef(false);
  const sourceIsCurrent = () => mounted.current && generation.current.token === token && liveSource.current === sourceKey;
  const previousOwner = useRef(study.study_id);
  const liveStudy = useRef(study);
  liveStudy.current = study;
  const guard = useRef(createLatestRequestGuard()).current;
  const reviewRef = useRef<Review | null>(null);
  const busy = useRef(false);
  const [draft, setDraft] = useState<VectorObservationDraft>({});
  const [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const [mayHaveCommitted, setMayHaveCommitted] = useState(false);
  useEffect(() => {
    mounted.current = true;
    guard.cancel(); busy.current = false; reviewRef.current = null;
    setIsSaving(false); setReview(null); setError(null); setFailed(false); setMayHaveCommitted(false);
    const source = liveStudy.current;
    const sameOwner = previousOwner.current === source.study_id;
    previousOwner.current = source.study_id;
    // A remote commit can close a trial with different values. Keep that local
    // draft for explicit comparison/discard rather than losing it on refresh.
    setDraft(current => sameOwner ? current : {});
    return () => { mounted.current = false; guard.cancel(); busy.current = false; };
    // The immutable source key, not a new wrapper object or locale, owns the draft.
  }, [guard, sourceKey]);

  function edit(trialId: string, responseId: string, value: string) {
    if (!sourceIsCurrent() || study.status !== "active" || study.objective.goal_type !== "desirability" ||
      !study.objective.responses.some(r => r.response_id === responseId) || !study.trials.some(t => t.trial_id === trialId && t.state === "pending")) return;
    if (busy.current || failed) setMayHaveCommitted(true);
    guard.cancel(); busy.current = false; reviewRef.current = null;
    setIsSaving(false); setReview(null); setFailed(false); setError(null);
    setDraft(current => ({ ...current, [trialId]: { ...current[trialId], [responseId]: value } }));
  }
  function preview() {
    if (!sourceIsCurrent() || study.status !== "active" || study.objective.goal_type !== "desirability" || busy.current) return;
    const observations = vectorObservationEntries(study.trials.filter(t => t.state === "pending").map(t => t.trial_id),
      study.objective.responses.map(r => r.response_id), draft);
    if (typeof observations === "string") { setError(observations); return; }
    try {
      const next = { sourceKey, request: { request_id: bayesianRequestId(), expected_study_version_id: study.study_version_id,
        expected_history_revision_id: study.observation_history.history_revision_id,
        expected_observation_history_sha256: study.observation_history.observation_history_sha256, observations } };
      reviewRef.current = next; setReview(next); setError(null); setFailed(false);
    } catch { setError("bayesian_secure_random_unavailable"); }
  }
  async function confirm() {
    const snapshot = reviewRef.current;
    if (!sourceIsCurrent() || !snapshot || snapshot !== review || liveSource.current !== snapshot.sourceKey || busy.current) return;
    const request = guard.begin(); busy.current = true; setIsSaving(true); setError(null);
    const current = () => guard.isCurrent(request) && liveSource.current === snapshot.sourceKey && reviewRef.current === snapshot;
    try {
      const response = await recordBayesianObservationsBatch(study.study_id, snapshot.request);
      if (!current()) return;
      setDraft(values => Object.fromEntries(Object.entries(values).filter(([id]) => !response.completed_trial_ids.includes(id))));
      onCommitted(response.study, snapshot.sourceKey);
      setReview(null); reviewRef.current = null; setFailed(false); setMayHaveCommitted(false);
    } catch (caught) {
      if (current()) {
        const code = bayesianErrorCode(caught);
        setError(/^(bayesian_[a-z0-9_]{1,100}|api_unreachable|validation_error)$/.test(code) ? code : "bayesian_observation_batch_failed");
        setFailed(true); setMayHaveCommitted(true);
      }
    } finally {
      if (guard.isCurrent(request) && liveSource.current === snapshot.sourceKey) { busy.current = false; setIsSaving(false); }
    }
  }
  function cancel() {
    if (!sourceIsCurrent()) return;
    if (busy.current || failed) setMayHaveCommitted(true);
    guard.cancel(); busy.current = false; reviewRef.current = null;
    setReview(null); setIsSaving(false); setFailed(false); setError(null);
  }
  function discardClosedDrafts() {
    if (!sourceIsCurrent() || busy.current) return;
    cancel();
    const pending = new Set(study.trials.filter(t => t.state === "pending").map(t => t.trial_id));
    setDraft(current => Object.fromEntries(Object.entries(current).filter(([id]) => pending.has(id))));
  }
  return { draft, edit, preview, review, confirm, cancel, discardClosedDrafts, error, isSaving, failed, mayHaveCommitted };
}
