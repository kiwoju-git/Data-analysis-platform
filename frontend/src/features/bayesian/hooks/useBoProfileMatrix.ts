import { useEffect, useRef, useState } from "react";
import { executeProfileMatrix, type ProfileAxisInput, type ProfileMatrixRow, type ProfileMatrixView } from "../boProfileMatrix";

export function useBoProfileMatrix(sourceKey: string) {
  const identity = useRef({ sourceKey, token: Symbol() });
  if (identity.current.sourceKey !== sourceKey) identity.current = { sourceKey, token: Symbol() };
  const token = identity.current.token, mounted = useRef(true), lane = useRef(0);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const [pending, setPending] = useState(0);
  const [state, setState] = useState<{ token: symbol; busy: boolean; view: ProfileMatrixView | null; error: string | null }>(() => ({ token, busy: false, view: null, error: null }));
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function run<P>(view: Omit<ProfileMatrixView, "axes">, axes: ProfileMatrixView["axes"], inputs: ProfileAxisInput<P>[], evaluate: (points: P[], budget: number) => Promise<ProfileMatrixRow[]>) {
    const owner = ++lane.current, current = () => mounted.current && identity.current.token === token && lane.current === owner;
    const snapshot = structuredClone({ view, axes, inputs });
    setPending(value => value + 1);
    setState({ token, busy: true, view: null, error: null });
    const previous = queue.current;
    let release!: () => void;
    queue.current = new Promise<void>(resolve => { release = resolve; });
    try {
      await previous;
      if (!current()) return;
      const result = await executeProfileMatrix(snapshot.inputs, evaluate, current);
      if (current()) setState({ token, busy: false, error: null, view: { ...snapshot.view, axes: snapshot.axes.map(axis => ({ ...axis, rows: result.find(row => row.factorId === axis.factor_id)!.rows })) } });
    } catch (caught) {
      const code = caught instanceof Error && ["bayesian_profile_budget", "bayesian_profile_response_mismatch"].includes(caught.message) ? caught.message : "bayesian_profile_matrix_failed";
      if (current()) setState({ token, busy: false, view: null, error: code });
    }
    finally { release(); if (mounted.current) setPending(value => value - 1); }
    // No stale finally mutation: only the owning generation may clear its busy state.
  }
  return { pending: pending > 0, busy: state.token === token && state.busy, view: state.token === token ? state.view : null, error: state.token === token ? state.error : null, run };
}
