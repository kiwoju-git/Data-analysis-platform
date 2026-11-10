import { useEffect, useRef, useState } from "react";
import { fetchPlanningBatch } from "../../../api/boPlanning";
import type { BayesianStudyResponse } from "../../../api/types/bayesian";
import type { PlanningBatchResponse } from "../../../api/types/boPlanning";
import { createPlanningRequestFence, planningStudyKey, validPlanningBatch } from "../boPlanningDraft";

export function usePlanningSavedBatch(study: BayesianStudyResponse, batchId: string) {
  const key = `${planningStudyKey(study)}:${batchId}`;
  const guard = useRef(createPlanningRequestFence()).current;
  guard.source(key);
  const latestStudy = useRef(study); latestStudy.current = study;
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<{ key: string; loading: boolean; batch: PlanningBatchResponse | null; error: string | null }>({ key: "", loading: true, batch: null, error: null });
  useEffect(() => {
    const token = guard.begin(), source = latestStudy.current;
    setState({ key, loading: true, batch: null, error: null });
    void fetchPlanningBatch(source.study_id, batchId).then(value => {
      if (!guard.current(token)) return;
      if (!validPlanningBatch(value, source, batchId)) throw new Error("bayesian_planning_response_mismatch");
      setState({ key, loading: false, batch: value, error: null });
    }).catch((caught: unknown) => {
      if (!guard.current(token)) return;
      const code = caught instanceof Error && /^[a-z][a-z0-9_]{1,100}$/.test(caught.message) ? caught.message : "bayesian_planning_batch_fetch_failed";
      setState({ key, loading: false, batch: null, error: code });
    });
    return () => guard.invalidate();
  }, [key, batchId, revision, guard]);
  return { ...(state.key === key ? state : { key, loading: true, batch: null, error: null }), refresh: () => { guard.invalidate(); setRevision(value => value + 1); } };
}
