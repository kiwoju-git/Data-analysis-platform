import { useEffect, useRef, useState } from "react";
import type { BayesianReplicateCreateRequest, BayesianReplicateCreateResponse, BayesianStudyResponse } from "../../../api";
import { createBayesianReplicates } from "../../../api/bayesian";
import { createLatestRequestGuard } from "../../../latestRequest";
import { bayesianRequestId } from "../bayesianRequestId";
import { strictBoNumber } from "../boNoisePolicy";
import { bayesianErrorCode } from "../bayesianDisplay";

type Snapshot = { studyId: string; studyVersionId: string; parentId: string; sourceKey: string; payload: BayesianReplicateCreateRequest };

export function useBayesianReplicateState(study: BayesianStudyResponse | null) {
  const [parentId, setParentId] = useState("");
  const [count, setCount] = useState("1");
  const [confirmed, setConfirmed] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retrySnapshot, setRetrySnapshot] = useState<Snapshot | null>(null);
  const [created, setCreated] = useState<BayesianReplicateCreateResponse | null>(null);
  const guard = useRef(createLatestRequestGuard()).current;
  const sourceKey = study === null ? null : `${study.study_id}:${study.observation_history.history_revision_id}:${study.observation_history.observation_history_sha256}`;
  const source = useRef(sourceKey);
  source.current = sourceKey;
  useEffect(() => {
    guard.cancel(); setIsRunning(false); setRetrySnapshot(null); setError(null); setConfirmed(false);
    return () => guard.cancel();
  }, [guard, sourceKey]);

  function edit(change: () => void) {
    guard.cancel(); setIsRunning(false); setRetrySnapshot(null); setError(null); change();
  }

  async function submit(totalBudget: string, retry = false): Promise<boolean> {
    let snapshot = retry ? retrySnapshot : null;
    if (snapshot === null) {
      const n = strictBoNumber(count), budget = strictBoNumber(totalBudget);
      if (study === null || sourceKey === null || study.status !== "active" ||
        study.trials.some(trial => trial.state === "pending") ||
        study.trials.find(trial => trial.trial_id === parentId)?.state !== "completed" ||
        n === null || !Number.isInteger(n) || n < 1 || n > 8 || !confirmed ||
        budget === null || !Number.isInteger(budget) || budget < 2 || budget > 200 || study.trials.length + n > budget) {
        setError("bayesian_replicate_input_invalid"); return false;
      }
      try {
        snapshot = { studyId: study.study_id, studyVersionId: study.study_version_id, parentId, sourceKey, payload: {
          expected_history_revision_id: study.observation_history.history_revision_id,
          expected_history_sha256: study.observation_history.observation_history_sha256,
          request_id: bayesianRequestId(), count: n, confirm_replicate_intent: true, total_trial_budget: budget,
        } };
      } catch { setError("bayesian_secure_random_unavailable"); return false; }
    }
    if (snapshot.sourceKey !== source.current) return false;
    const request = guard.begin();
    const current = () => guard.isCurrent(request) && snapshot.sourceKey === source.current;
    setIsRunning(true); setError(null); setRetrySnapshot(snapshot);
    try {
      const result = await createBayesianReplicates(snapshot.studyId, snapshot.parentId, snapshot.payload);
      if (!current()) return false;
      if (result.study_id !== snapshot.studyId || result.study_version_id !== snapshot.studyVersionId || result.parent_trial_id !== snapshot.parentId ||
        result.request_id !== snapshot.payload.request_id || result.source_history_revision_id !== snapshot.payload.expected_history_revision_id ||
        result.source_history_sha256 !== snapshot.payload.expected_history_sha256 || result.trials.length !== snapshot.payload.count ||
        new Set(result.trials.map(trial => trial.trial_id)).size !== result.trials.length ||
        result.trials.some(trial => trial.origin !== "replicate" || trial.study_version_id !== snapshot.studyVersionId ||
          trial.replicate_of_trial_id !== snapshot.parentId ||
          (!result.replayed && trial.state !== "pending") ||
          !["pending", "completed", "abandoned"].includes(trial.state) ||
          (trial.state === "completed" ? trial.objective_value === null || !Number.isFinite(trial.objective_value) : trial.objective_value !== null))) {
        setError("bayesian_replicate_response_mismatch"); return false;
      }
      setCreated(result); setRetrySnapshot(null); setConfirmed(false); return true;
    } catch (caught) {
      if (current()) setError(bayesianErrorCode(caught));
      return false;
    } finally { if (current()) setIsRunning(false); }
  }

  return {
    parentId, count, confirmed, isRunning, error,
    canRetry: retrySnapshot !== null && !isRunning,
    created: created?.study_id === study?.study_id ? created : null,
    setParentId: (value: string) => edit(() => setParentId(value)),
    setCount: (value: string) => edit(() => setCount(value)),
    setConfirmed: (value: boolean) => edit(() => setConfirmed(value)), submit,
  };
}
