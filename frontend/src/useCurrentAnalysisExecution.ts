import { useCallback, useEffect, useRef, useState } from "react";
import { createAnalysisRun, fetchAnalysisRunStatus, type AnalysisResultEnvelope, type AnalysisRunRequest } from "./api";
import { analysisCompletionMatches, analysisExecutionErrorCode, analysisExecutionSourceKey, analysisStatusMatches, type AnalysisExecutionSource } from "./analysisExecutionContext";
import { createLatestRequestGuard } from "./latestRequest";

interface Owner { token: symbol; epoch: number; sourceKey: string }
interface Completion { owner: Owner; result: AnalysisResultEnvelope }
interface Failure { owner: Owner; code: string; analysisId: string | null; cause?: unknown }

export function useCurrentAnalysisExecution(source: AnalysisExecutionSource, onExecutionIntent?: () => void) {
  const guard = useRef(createLatestRequestGuard()).current;
  const mounted = useRef(true);
  const live = useRef({ source, key: analysisExecutionSourceKey(source), epoch: 0 });
  const key = analysisExecutionSourceKey(source);
  if (live.current.key !== key) {
    live.current = { source, key, epoch: live.current.epoch + 1 };
    guard.cancel();
  } else live.current.source = source;
  const [completed, setCompleted] = useState<Completion | null>(null);
  const [pending, setPending] = useState<Owner | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const verification = useRef<Completion | null>(null);

  const owns = useCallback((owner: Owner) => mounted.current && guard.isCurrent(owner.token) &&
    owner.epoch === live.current.epoch && owner.sourceKey === live.current.key, [guard]);
  const belongs = (owner: Owner) => owner.epoch === live.current.epoch && owner.sourceKey === key;

  const invalidate = useCallback((clearResult = true) => {
    live.current.epoch += 1;
    guard.cancel();
    verification.current = null;
    setPending(null);
    setFailure(null);
    if (clearResult) setCompleted(null);
    else setCompleted((previous) => previous === null ? null : {
      ...previous, owner: { ...previous.owner, epoch: live.current.epoch, sourceKey: live.current.key },
    });
  }, [guard]);

  async function verify(completion: Completion) {
    const { owner, result } = completion;
    if (!owns(owner)) return;
    setPending(owner);
    setFailure(null);
    try {
      const status = await fetchAnalysisRunStatus(result.analysis_id);
      if (!owns(owner)) return;
      if (!analysisStatusMatches(status, result)) {
        setCompleted(null);
        setFailure({ owner, code: "analysis_completion_verification_failed", analysisId: result.analysis_id });
      } else if (status.stale) {
        setCompleted(null);
        verification.current = null;
        setFailure({ owner, code: "analysis_completion_source_changed", analysisId: result.analysis_id });
      } else {
        verification.current = null;
        setCompleted(completion);
      }
    } catch (cause) {
      if (owns(owner)) setFailure({ owner, code: "analysis_completion_verification_failed", analysisId: result.analysis_id, cause });
    } finally {
      if (owns(owner)) setPending(null);
    }
  }

  async function execute(input: AnalysisRunRequest) {
    if (!mounted.current) return;
    const captured = live.current;
    const owner = { token: guard.begin(), epoch: captured.epoch, sourceKey: captured.key };
    verification.current = null;
    setFailure(null);
    setPending(owner);
    try {
      onExecutionIntent?.();
      const request = structuredClone(input);
      const schemaHash = captured.source.schemaHash;
      if (captured.source.sourceChanging || schemaHash === null || !/^[0-9a-f]{64}$/.test(schemaHash) ||
          request.dataset_version_id !== captured.source.datasetVersionId ||
          request.method_id !== captured.source.methodId || request.method_version !== captured.source.methodVersion) {
        setFailure({ owner, code: "analysis_completion_source_changed", analysisId: null });
        return;
      }
      const result = await createAnalysisRun(request);
      if (!owns(owner)) return;
      if (!analysisCompletionMatches(result, request, schemaHash)) {
        setCompleted(null);
        setFailure({ owner, code: "analysis_completion_source_changed", analysisId: null });
        return;
      }
      verification.current = { owner, result };
      await verify(verification.current);
    } catch (error) {
      if (owns(owner)) setFailure({ owner, code: analysisExecutionErrorCode(error), analysisId: null, cause: error });
    } finally {
      if (owns(owner)) setPending(null);
    }
  }

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; guard.cancel(); verification.current = null; };
  }, [guard]);

  return {
    result: completed !== null && completed.result.dataset_version_id === source.datasetVersionId &&
      completed.result.provenance.source_schema_hash === source.schemaHash &&
      completed.result.method_id === source.methodId && completed.result.method_version === source.methodVersion
      ? completed.result : null,
    isRunning: pending !== null && owns(pending),
    error: failure !== null && belongs(failure.owner) ? failure.code : null,
    errorCause: failure !== null && belongs(failure.owner) ? failure.cause : undefined,
    savedAnalysisId: failure !== null && belongs(failure.owner) ? failure.analysisId : null,
    canRetryVerification: verification.current !== null && owns(verification.current.owner),
    execute,
    invalidate,
    setValidationError: (code: string | null) => {
      if (!mounted.current) return;
      if (code === null) { setFailure(null); return; }
      invalidate(false);
      const owner = { token: guard.begin(), epoch: live.current.epoch, sourceKey: live.current.key };
      setFailure({ owner, code, analysisId: null });
    },
    retryVerification: async () => { if (verification.current !== null) await verify(verification.current); },
  };
}
