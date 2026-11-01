import { useEffect, useRef, useState } from "react";
import { createResponseOptimizer, type ResponseOptimizerCreateRequest, type ResponseOptimizerResponse } from "../api";
import { createLatestRequestGuard } from "../latestRequest";
import { createSourceContextGuard, type SourceContextToken } from "../sourceContextGuard";

interface Owner { source: SourceContextToken<string>; draft: number }

export function useResponseOptimizerRun(sourceKey: string) {
  const context = useRef(createSourceContextGuard(sourceKey)).current;
  const guard = useRef(createLatestRequestGuard()).current;
  const draft = useRef(0);
  const mounted = useRef(true);
  if (context.capture().source !== sourceKey) { context.advance(sourceKey); guard.cancel(); }
  const source = context.capture();
  const [completed, setCompleted] = useState<{ owner: Owner; value: ResponseOptimizerResponse } | null>(null);
  const [failure, setFailure] = useState<{ owner: Owner; code: string } | null>(null);
  const [pending, setPending] = useState<{ owner: Owner; token: symbol } | null>(null);
  const [stale, setStale] = useState<Owner | null>(null);
  const owns = (owner: Owner) => mounted.current && context.isCurrent(owner.source) && draft.current === owner.draft;
  const optimization = completed !== null && owns(completed.owner) ? completed.value : null;
  const isOptimizing = pending !== null && owns(pending.owner) && guard.isCurrent(pending.token);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; guard.cancel(); };
  }, [guard]);

  function invalidate() {
    if (!context.isCurrent(source)) return;
    const changed = optimization !== null || isOptimizing || (stale !== null && owns(stale));
    draft.current += 1; guard.cancel();
    setCompleted(null); setFailure(null); setPending(null);
    setStale(changed ? { source, draft: draft.current } : null);
  }
  function restore(value: ResponseOptimizerResponse | null) {
    guard.cancel(); setPending(null); setFailure(null); setStale(null);
    setCompleted(value === null ? null : { owner: { source, draft: draft.current }, value });
  }
  async function run(designId: string, request: ResponseOptimizerCreateRequest,
    onCreated?: (value: ResponseOptimizerResponse) => void) {
    if (!context.isCurrent(source)) return;
    const owner = { source, draft: draft.current }, token = guard.begin();
    const current = () => owns(owner) && guard.isCurrent(token);
    setPending({ owner, token }); setCompleted(null); setFailure(null); setStale(null);
    try {
      // The request contains only copied primitives/arrays and is never mutated by draft edits.
      const value = await createResponseOptimizer(designId, request);
      if (!current()) return;
      setCompleted({ owner, value }); onCreated?.(value);
    } catch (cause) {
      if (current()) setFailure({ owner, code: cause instanceof Error ? cause.message : "response_optimizer_unknown_error" });
    } finally { if (current()) setPending(null); }
  }
  return { optimization, isOptimizing, isStale: stale !== null && owns(stale), invalidate, restore, run,
    error: failure !== null && owns(failure.owner) ? failure.code : null };
}
