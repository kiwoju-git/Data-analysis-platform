import type {
  GaussianProcessPointPredictionRequest,
  GaussianProcessPointPredictionResponse,
} from "./api/types/regression";

export const GP_POINT_PREDICTION_ROW_LIMIT = 2000;

export interface GpPredictionSource {
  readonly analysisId: string;
  readonly modelId: string;
  readonly manifestSha256: string;
  readonly responseColumnId: string;
  readonly predictorColumnIds: readonly string[];
}

export interface GpPredictionDraftRow {
  readonly id: string;
  readonly values: Readonly<Record<string, string>>;
}

export interface GpPredictionRequestSnapshot {
  readonly source: GpPredictionSource;
  readonly request: GaussianProcessPointPredictionRequest;
}

export interface GpCompletedPredictionSnapshot {
  readonly schema_version: 1;
  readonly artifact_kind: "gaussian_process_point_prediction_snapshot";
  readonly source_analysis_id: string;
  readonly predictor_column_ids: readonly string[];
  readonly client_received_at: string;
  readonly prediction_recalculated_on_export: false;
  readonly request: GaussianProcessPointPredictionRequest;
  readonly response: GaussianProcessPointPredictionResponse;
}

export function gpPredictionSourceKey(source: GpPredictionSource): string {
  return JSON.stringify([
    source.analysisId,
    source.modelId,
    source.manifestSha256,
    source.responseColumnId,
    source.predictorColumnIds,
  ]);
}

export function captureGpPredictionRequest(
  source: GpPredictionSource,
  rows: readonly GpPredictionDraftRow[],
): GpPredictionRequestSnapshot {
  validateSource(source);
  if (!Array.isArray(rows) || rows.length < 1 || rows.length > GP_POINT_PREDICTION_ROW_LIMIT) {
    throw new Error("gp_prediction_input_invalid");
  }
  const ids = new Set<string>();
  const requestRows = rows.map((row) => {
    if (!isRecord(row) || !validRowId(row.id) || ids.has(row.id) || !isRecord(row.values)
      || !sameKeys(row.values, source.predictorColumnIds)) {
      throw new Error("gp_prediction_input_invalid");
    }
    ids.add(row.id);
    const draftValues = row.values;
    const values = Object.fromEntries(source.predictorColumnIds.map((id) => {
      const value: unknown = draftValues[id];
      if (typeof value !== "string" || value.trim() === "" || !Number.isFinite(Number(value))) {
        throw new Error("gp_prediction_input_invalid");
      }
      return [id, Number(value)];
    }));
    return { client_row_id: row.id, values };
  });
  return {
    source: { ...source, predictorColumnIds: [...source.predictorColumnIds] },
    request: { expected_model_manifest_sha256: source.manifestSha256, rows: requestRows },
  };
}

export function completeGpPredictionSnapshot(
  captured: GpPredictionRequestSnapshot,
  response: unknown,
  receivedAt: string,
): GpCompletedPredictionSnapshot {
  const fail = (): never => { throw new Error("gp_prediction_response_invalid"); };
  const requestedIds = new Set(captured.request.rows.map((row) => row.client_row_id));
  if (captured.request.expected_model_manifest_sha256 !== captured.source.manifestSha256
    || requestedIds.size !== captured.request.rows.length
    || captured.request.rows.length < 1
    || captured.request.rows.length > GP_POINT_PREDICTION_ROW_LIMIT
    || !isRecord(response)
    || response.model_id !== captured.source.modelId
    || response.model_manifest_sha256 !== captured.source.manifestSha256
    || response.response_column_id !== captured.source.responseColumnId
    || response.interval_kind !== "latent_and_new_observation"
    || response.confidence_level !== 0.95
    || response.row_count !== captured.request.rows.length
    || !Array.isArray(response.rows)
    || response.rows.length !== captured.request.rows.length) {
    return fail();
  }
  const seen = new Set<string>();
  const rows = response.rows.map((row: unknown) => {
    if (!isRecord(row) || !validRowId(row.client_row_id) || !requestedIds.has(row.client_row_id)
      || seen.has(row.client_row_id) || !finiteNumber(row.predicted_mean)
      || !nonnegativeNumber(row.latent_standard_deviation)
      || !nonnegativeNumber(row.predictive_standard_deviation)
      || !validInterval(row.latent_interval_95) || !validInterval(row.predictive_interval_95)
      || !Array.isArray(row.warnings) || !row.warnings.every((warning: unknown) => typeof warning === "string")) {
      return fail();
    }
    seen.add(row.client_row_id);
    return {
      client_row_id: row.client_row_id,
      predicted_mean: row.predicted_mean,
      latent_standard_deviation: row.latent_standard_deviation,
      latent_interval_95: { ...row.latent_interval_95 },
      predictive_standard_deviation: row.predictive_standard_deviation,
      predictive_interval_95: { ...row.predictive_interval_95 },
      warnings: [...row.warnings] as string[],
    };
  });
  // Keep the received order in the export; the grid joins these validated rows by ID.
  return {
    schema_version: 1,
    artifact_kind: "gaussian_process_point_prediction_snapshot",
    source_analysis_id: captured.source.analysisId,
    predictor_column_ids: [...captured.source.predictorColumnIds],
    client_received_at: receivedAt,
    prediction_recalculated_on_export: false,
    request: {
      expected_model_manifest_sha256: captured.request.expected_model_manifest_sha256,
      rows: captured.request.rows.map((row) => ({ client_row_id: row.client_row_id, values: { ...row.values } })),
    },
    response: {
      model_id: captured.source.modelId,
      model_manifest_sha256: captured.source.manifestSha256,
      response_column_id: captured.source.responseColumnId,
      row_count: rows.length,
      interval_kind: "latent_and_new_observation",
      confidence_level: 0.95,
      rows,
    },
  };
}

function validateSource(source: GpPredictionSource): void {
  if (![source.analysisId, source.modelId, source.responseColumnId].every((id) => typeof id === "string" && id.length > 0)
    || !/^[a-f0-9]{64}$/u.test(source.manifestSha256)
    || !Array.isArray(source.predictorColumnIds) || source.predictorColumnIds.length === 0
    || !source.predictorColumnIds.every((id) => typeof id === "string" && id.length > 0)
    || new Set(source.predictorColumnIds).size !== source.predictorColumnIds.length) {
    throw new Error("gp_model_manifest_invalid");
  }
}

function sameKeys(values: Record<string, unknown>, keys: readonly string[]): boolean {
  return Object.keys(values).length === keys.length && keys.every((key) => Object.prototype.hasOwnProperty.call(values, key));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validRowId(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 120;
}

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function nonnegativeNumber(value: unknown): value is number {
  return finiteNumber(value) && value >= 0;
}

function validInterval(value: unknown): value is { lower: number; upper: number } {
  return isRecord(value) && finiteNumber(value.lower) && finiteNumber(value.upper) && value.lower <= value.upper;
}
