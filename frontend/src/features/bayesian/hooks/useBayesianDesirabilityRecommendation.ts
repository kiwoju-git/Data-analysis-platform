import { useEffect, useRef, useState } from "react";
import { confirmDesirabilityReview, createDesirabilityReview, fetchDesirabilityBatch, fetchLatestDesirabilityBatch } from "../../../api/bayesianDesirability";
import type { BayesianStudyResponse } from "../../../api/types/bayesian";
import type { DesirabilityBatch, DesirabilityReview } from "../../../api/types/bayesianDesirability";
import { createLatestRequestGuard } from "../../../latestRequest";
import { buildDesirabilityRequest, defaultDesirabilityDraft, type DesirabilityDraft, type DesirabilityDraftErrors } from "../bayesianDesirabilityDraft";
import { bayesianErrorCode } from "../bayesianDisplay";
import { vectorStudySourceKey } from "../bayesianVectorDraft";
import { sameDesirabilityJson as sameJson, validDesirabilityCalculation as validCalculation, validDesirabilitySaved as validSaved } from "../desirabilityResponseGuard";

function failureCode(caught: unknown, fallback: string) {
  const code = bayesianErrorCode(caught);
  return /^(bayesian_[a-z0-9_]{1,100}|api_unreachable|validation_error)$/.test(code) ? code : fallback;
}
interface Options {
  study: BayesianStudyResponse | null;
  requestedBatchId: string | null;
  onBatchSelected: (id: string | null) => void;
}
export function useBayesianDesirabilityRecommendation({ study: inputStudy, requestedBatchId, onBatchSelected }: Options) {
  const study = inputStudy?.objective.goal_type === "desirability" ? inputStudy : null;
  // A newly committed pending trial does not advance the observation history.
  const sourceKey = study === null ? "none" : `${vectorStudySourceKey(study)}:${study.trials.map(t => `${t.trial_id}:${t.state}`).join(",")}`;
  const contextKey = `${sourceKey}:${requestedBatchId}`;
  const generation = useRef({ key: contextKey, token: Symbol() });
  if (generation.current.key !== contextKey) generation.current = { key: contextKey, token: Symbol() };
  const token = generation.current.token;
  const mounted = useRef(false);
  const draftRevision = useRef(0);
  const renderedRevision = draftRevision.current;
  const current = () => mounted.current && generation.current.token === token;
  const mutationGuard = useRef(createLatestRequestGuard()).current;
  const restoreGuard = useRef(createLatestRequestGuard()).current;
  const activeReview = useRef<DesirabilityReview | null>(null);
  const busy = useRef(false);
  const confirming = useRef(false);
  const latestStudy = useRef(study); latestStudy.current = study;
  const selectedCallback = useRef(onBatchSelected); selectedCallback.current = onBatchSelected;
  const owner = study === null ? null : `${study.study_id}:${study.study_version_id}:${study.definition_sha256}`;
  const previousOwner = useRef(owner);
  const [draft, setDraft] = useState(() => defaultDesirabilityDraft(study));
  const [review, setReview] = useState<DesirabilityReview | null>(null);
  const [saved, setSaved] = useState<DesirabilityBatch | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<DesirabilityDraftErrors>({});
  const [mayHaveCommitted, setMayHaveCommitted] = useState(false);
  const [restoreRevision, setRestoreRevision] = useState(0);

  useEffect(() => {
    mounted.current = true;
    mutationGuard.cancel(); restoreGuard.cancel(); busy.current = false; confirming.current = false; activeReview.current = null;
    setIsReviewing(false); setIsConfirming(false); setReview(null); setError(null); setErrors({}); setMayHaveCommitted(false);
    if (previousOwner.current !== owner) {
      previousOwner.current = owner;
      draftRevision.current += 1;
      setDraft(defaultDesirabilityDraft(latestStudy.current));
    }
    setSaved(null);
    const source = latestStudy.current;
    if (source === null) { setIsRestoring(false); return () => { mounted.current = false; }; }
    const request = restoreGuard.begin();
    const active = () => restoreGuard.isCurrent(request) && generation.current.token === token;
    setIsRestoring(true);
    void (async () => {
      try {
        const result = requestedBatchId === null ? (await fetchLatestDesirabilityBatch(source.study_id)).item
          : await fetchDesirabilityBatch(source.study_id, requestedBatchId);
        if (!active()) return;
        if (result !== null && !validSaved(result, source, requestedBatchId)) { setError("bayesian_review_mismatch"); return; }
        setSaved(result);
      } catch (caught) {
        if (active()) setError(failureCode(caught, "bayesian_recommendation_batch_fetch_failed"));
      } finally { if (active()) setIsRestoring(false); }
    })();
    return () => { mounted.current = false; mutationGuard.cancel(); restoreGuard.cancel(); busy.current = false; confirming.current = false; };
  }, [contextKey, mutationGuard, owner, requestedBatchId, restoreGuard, restoreRevision, token]);

  function invalidate() {
    if (!current()) return;
    if (confirming.current) setMayHaveCommitted(true);
    mutationGuard.cancel(); busy.current = false; confirming.current = false; activeReview.current = null;
    setReview(null); setIsReviewing(false); setIsConfirming(false); setError(null); setErrors({});
  }
  function edit(next: DesirabilityDraft) {
    if (!current() || renderedRevision !== draftRevision.current) return;
    draftRevision.current += 1; invalidate(); setDraft(next);
  }
  async function requestReview() {
    if (!current() || renderedRevision !== draftRevision.current || study === null || busy.current ||
      study.status !== "active" || study.trials.some(t => t.state === "pending")) return false;
    const built = buildDesirabilityRequest(study, draft);
    setErrors(built.errors);
    if (built.request === null) { setError("bayesian_desirability_settings_invalid"); return false; }
    const snapshot = built.request;
    const revision = draftRevision.current;
    const request = mutationGuard.begin();
    const active = () => current() && mutationGuard.isCurrent(request) && draftRevision.current === revision;
    busy.current = true; activeReview.current = null; setReview(null); setError(null); setIsReviewing(true);
    try {
      const result = await createDesirabilityReview(study.study_id, snapshot);
      if (!active()) return false;
      if (result.schema_version !== (snapshot.schema_version === 4 ? 2 : snapshot.schema_version === 5 ? 3 : snapshot.schema_version === 6 ? 4 : 5) || result.study_id !== study.study_id || result.study_version_id !== study.study_version_id ||
        result.source_history_revision_id !== snapshot.expected_history_revision_id || result.source_observation_history_sha256 !== snapshot.expected_history_sha256 ||
        !validCalculation(result.calculation, study, snapshot)) { setError("bayesian_review_mismatch"); return false; }
      activeReview.current = result; setReview(result); setMayHaveCommitted(false); return true;
    } catch (caught) {
      if (active()) setError(failureCode(caught, "bayesian_recommendation_review_failed"));
      return false;
    } finally { if (active()) { busy.current = false; setIsReviewing(false); } }
  }
  async function confirm() {
    const snapshot = activeReview.current;
    if (!current() || study === null || busy.current || snapshot === null || snapshot !== review ||
      renderedRevision !== draftRevision.current || snapshot.source_history_revision_id !== study.observation_history.history_revision_id ||
      snapshot.source_observation_history_sha256 !== study.observation_history.observation_history_sha256) return false;
    const revision = draftRevision.current;
    const request = mutationGuard.begin();
    const active = () => current() && mutationGuard.isCurrent(request) && draftRevision.current === revision;
    busy.current = true; confirming.current = true; setIsConfirming(true); setError(null);
    try {
      const result = await confirmDesirabilityReview(study.study_id, snapshot.review_id, snapshot.config_sha256);
      if (!active()) return false;
      if (!validSaved(result, study, snapshot.review_id) || result.config_sha256 !== snapshot.config_sha256 ||
        result.source_history_revision_id !== snapshot.source_history_revision_id || result.source_observation_history_sha256 !== snapshot.source_observation_history_sha256 ||
        !sameJson(result.calculation, snapshot.calculation)) { setError("bayesian_review_mismatch"); setMayHaveCommitted(true); return false; }
      setSaved(result); activeReview.current = null; setReview(null); setMayHaveCommitted(false);
      selectedCallback.current(result.batch_id);
      return true;
    } catch (caught) {
      if (active()) { setError(failureCode(caught, "bayesian_recommendation_confirm_failed")); setMayHaveCommitted(true); }
      return false;
    } finally { if (active()) { busy.current = false; confirming.current = false; setIsConfirming(false); } }
  }
  function refresh() {
    if (!current()) return;
    invalidate(); restoreGuard.cancel(); setRestoreRevision(value => value + 1);
  }
  return { draft, edit, review, saved, requestReview, confirm, discard: invalidate, refresh, error, errors,
    isReviewing, isConfirming, isRestoring, mayHaveCommitted };
}
