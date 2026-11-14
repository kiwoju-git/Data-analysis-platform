import { useEffect, useRef, useState } from "react";
import { evaluateBoView, type BoViewEvaluationRequest, type BoViewReceipt } from "../../../api/boViews";
import { validBoViewReceipt, type BoViewExpected } from "../boSavedViews";

export function useBoDiagnosticView(sourceKey: string) {
  const identity = useRef({ key: sourceKey, generation: Symbol() });
  if (identity.current.key !== sourceKey) identity.current = { key: sourceKey, generation: Symbol() };
  const generation = identity.current.generation, mounted = useRef(true), lane = useRef(0);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const [pending, setPending] = useState(0);
  const [state, setState] = useState<{ generation: symbol; busy: boolean; receipt: BoViewReceipt | null; error: boolean }>({ generation, busy: false, receipt: null, error: false });
  useEffect(() => { mounted.current = true; lane.current++; return () => { mounted.current = false; }; }, []);
  async function run(expected: BoViewExpected, request: BoViewEvaluationRequest) {
    const snapshot = structuredClone({ expected, request }), owner = ++lane.current;
    const current = () => mounted.current && identity.current.generation === generation && lane.current === owner;
    const previous = queue.current;
    let release!: () => void;
    queue.current = new Promise<void>(resolve => { release = resolve; });
    setPending(value => value + 1); setState({ generation, busy: true, receipt: null, error: false });
    try {
      await previous;
      if (!current()) return;
      const receipt = await evaluateBoView(snapshot.expected.studyId, snapshot.expected.modelId, snapshot.request);
      if (!current()) return;
      if (!validBoViewReceipt(receipt, snapshot.expected, snapshot.request)) throw Error("bayesian_view_source_mismatch");
      setState({ generation, busy: false, receipt, error: false });
    } catch {
      if (current()) setState({ generation, busy: false, receipt: null, error: true });
    } finally { release(); if (mounted.current) setPending(value => value - 1); }
  }
  return { run, pending: pending > 0, busy: state.generation === generation && state.busy, error: state.generation === generation && state.error, receipt: state.generation === generation ? state.receipt : null };
}
