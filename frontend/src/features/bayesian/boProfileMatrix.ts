export interface ProfileAxisInput<P> { factorId: string; points: P[] }
export interface ProfileAxisResult<R> { factorId: string; rows: R[] }

// Each chunk is awaited before the next; an incomplete matrix never escapes.
export async function executeProfileMatrix<P, R>(axes: ProfileAxisInput<P>[], evaluate: (points: P[], budget: number) => Promise<R[]>, current: () => boolean, now = () => Date.now()): Promise<ProfileAxisResult<R>[]> {
  const snapshot = structuredClone(axes), started = now();
  if (!snapshot.length || snapshot.length > 10 || new Set(snapshot.map(axis => axis.factorId)).size !== snapshot.length || snapshot.some(axis => !axis.points.length) || snapshot.reduce((total, axis) => total + axis.points.length, 0) > 1000) throw Error("bayesian_profile_budget");
  function remaining() {
    if (!current()) throw Error("bayesian_profile_stale");
    const value = Math.floor(120000 - (now() - started));
    if (value <= 0) throw Error("bayesian_profile_budget");
    return Math.min(60000, value);
  }
  const result: ProfileAxisResult<R>[] = [];
  for (const axis of snapshot) {
    const rows: R[] = [];
    for (let offset = 0; offset < axis.points.length; offset += 100) {
      const chunk = axis.points.slice(offset, offset + 100), values = await evaluate(chunk, remaining());
      remaining();
      if (values.length !== chunk.length) throw Error("bayesian_profile_response_mismatch");
      rows.push(...values);
    }
    result.push({ factorId: axis.factorId, rows });
  }
  return result;
}

export interface ProfileMatrixRow {
  row_id: string; actual_coordinates: Record<string, string | number>; constraints_satisfied: boolean;
  response_predictions: { response_id: string; mean_raw: number; latent_standard_deviation_raw: number; predictive_standard_deviation_raw: number }[];
  desirability_moments: { mean: number };
}
export interface ProfileMatrixAxis { factor_id: string; name: string; unit: string | null; category: boolean; range?: { min: number; max: number }; pathPolicy?: string; unavailableReason?: string }
export interface ProfileMatrixView {
  modelId: string; modelHash: string; historyHash: string; holds: Record<string, string | number>;
  axes: (ProfileMatrixAxis & { rows: ProfileMatrixRow[] })[];
  responses: { response_id: string; name: string; unit: string | null }[];
}
