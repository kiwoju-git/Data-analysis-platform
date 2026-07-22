import { useCallback, useEffect, useRef, useState } from "react";

import { fetchRuntimeInfo, type RuntimeInfoResponse } from "./api";
import { ApiRequestError } from "./api/client";
import { createLatestRequestGuard } from "./latestRequest";
import {
  evaluateRuntimeCompatibility,
  type RuntimeCompatibilityResult,
} from "./runtimeCompatibility";

export type RuntimeCompatibilityState =
  | { kind: "checking"; runtime: null; result: null; error: null }
  | {
      kind: "compatible";
      runtime: RuntimeInfoResponse;
      result: RuntimeCompatibilityResult;
      error: null;
    }
  | {
      kind: "blocked";
      runtime: RuntimeInfoResponse | null;
      result: RuntimeCompatibilityResult | null;
      error: string;
    };

export function useRuntimeCompatibilityState() {
  const [state, setState] = useState<RuntimeCompatibilityState>({
    kind: "checking",
    runtime: null,
    result: null,
    error: null,
  });
  const requestGuard = useRef(createLatestRequestGuard()).current;

  const check = useCallback(() => {
    const request = requestGuard.begin();
    setState({ kind: "checking", runtime: null, result: null, error: null });
    void fetchRuntimeInfo()
      .then((runtime) => {
        if (!requestGuard.isCurrent(request)) return;
        const result = evaluateRuntimeCompatibility(runtime);
        setState(
          result.compatible
            ? { kind: "compatible", runtime, result, error: null }
            : { kind: "blocked", runtime, result, error: result.code ?? "runtime_mismatch" },
        );
      })
      .catch((error) => {
        if (!requestGuard.isCurrent(request)) return;
        const code =
          error instanceof ApiRequestError && error.routeNotFound
            ? "runtime_info_route_missing"
            : error instanceof Error
              ? error.message
              : "runtime_info_failed";
        setState({ kind: "blocked", runtime: null, result: null, error: code });
      });
  }, [requestGuard]);

  useEffect(() => {
    check();
    return () => requestGuard.cancel();
  }, [check, requestGuard]);

  return { state, retry: check };
}
