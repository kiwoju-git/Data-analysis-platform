import { useEffect, useRef, useState } from "react";
import { createGaussianProcessPointPredictions } from "./api/regression";
import {
  captureGpPredictionRequest,
  completeGpPredictionSnapshot,
  gpPredictionSourceKey,
  GP_POINT_PREDICTION_ROW_LIMIT,
  type GpCompletedPredictionSnapshot,
  type GpPredictionDraftRow,
  type GpPredictionSource,
} from "./gpPredictionSnapshot";
import { createLatestRequestGuard } from "./latestRequest";
import { createSourceContextGuard, type SourceContextToken } from "./sourceContextGuard";

interface Ownership {
  source: SourceContextToken<string>;
  draft: number;
}

export function useGpPointPrediction(source: GpPredictionSource) {
  const sourceKey = gpPredictionSourceKey(source);
  const context = useRef(createSourceContextGuard(sourceKey)).current;
  const guard = useRef(createLatestRequestGuard()).current;
  const draft = useRef(0);
  const nextId = useRef(2);
  const mounted = useRef(true);
  if (context.capture().source !== sourceKey) {
    context.advance(sourceKey);
    guard.cancel();
  }
  const currentSource = context.capture();
  const initialRows = [emptyRow("gp-row-1", source.predictorColumnIds)];
  const [rowState, setRowState] = useState({ source: currentSource, rows: initialRows });
  const [completed, setCompleted] = useState<{ owner: Ownership; snapshot: GpCompletedPredictionSnapshot } | null>(null);
  const [failure, setFailure] = useState<{ owner: Ownership; cause: unknown } | null>(null);
  const [staleOwner, setStaleOwner] = useState<Ownership | null>(null);
  const [pending, setPending] = useState<(Ownership & { request: symbol }) | null>(null);
  const rows = rowState.source === currentSource ? rowState.rows : initialRows;
  const owns = (owner: Ownership) => mounted.current && context.isCurrent(owner.source) && owner.draft === draft.current;
  const snapshot = completed !== null && owns(completed.owner) ? completed.snapshot : null;
  const error = failure !== null && owns(failure.owner) ? failure : null;
  const isRunning = pending !== null && owns(pending) && guard.isCurrent(pending.request);
  const isStale = staleOwner !== null && owns(staleOwner);
  const valid = rows.length > 0 && rows.length <= GP_POINT_PREDICTION_ROW_LIMIT && rows.every((row) => source.predictorColumnIds.every((id) => {
    const value = row.values[id];
    return value !== undefined && value.trim() !== "" && Number.isFinite(Number(value));
  }));

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; guard.cancel(); };
  }, [guard]);

  function changeRows(change: (current: GpPredictionDraftRow[]) => GpPredictionDraftRow[]) {
    if (!context.isCurrent(currentSource)) return;
    const invalidated = snapshot !== null || isRunning || isStale;
    draft.current += 1;
    guard.cancel();
    setStaleOwner(invalidated ? { source: currentSource, draft: draft.current } : null);
    setCompleted(null); setFailure(null); setPending(null);
    setRowState((current) => ({ source: currentSource, rows: change(current.source === currentSource ? current.rows : initialRows) }));
  }

  async function run(): Promise<void> {
    if (!valid || !context.isCurrent(currentSource)) return;
    const owner = { source: currentSource, draft: draft.current };
    const token = guard.begin();
    const current = () => owns(owner) && guard.isCurrent(token);
    setCompleted(null); setFailure(null); setStaleOwner(null); setPending({ ...owner, request: token });
    try {
      const captured = captureGpPredictionRequest(source, rows);
      const response = await createGaussianProcessPointPredictions(captured.source.modelId, captured.request);
      if (!current()) return;
      const result = completeGpPredictionSnapshot(captured, response, new Date().toISOString());
      setCompleted({ owner, snapshot: result });
    } catch (cause) {
      if (current()) setFailure({ owner, cause });
    } finally {
      if (current()) setPending(null);
    }
  }

  return {
    rows, snapshot, error, isRunning, isStale, valid, run,
    editCell: (rowId: string, columnId: string, value: string) => changeRows((current) => current.map((row) => row.id === rowId ? { ...row, values: { ...row.values, [columnId]: value } } : row)),
    addRow: () => { if (rows.length < GP_POINT_PREDICTION_ROW_LIMIT) changeRows((current) => [...current, emptyRow(`gp-row-${nextId.current++}`, source.predictorColumnIds)]); },
    removeRow: (rowId: string) => changeRows((current) => current.length === 1 ? [emptyRow(`gp-row-${nextId.current++}`, source.predictorColumnIds)] : current.filter((row) => row.id !== rowId)),
  };
}

function emptyRow(id: string, columnIds: readonly string[]): GpPredictionDraftRow {
  return { id, values: Object.fromEntries(columnIds.map((columnId) => [columnId, ""])) };
}
