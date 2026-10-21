import type { BayesianFactorResponse, BayesianNoiseBatchCreateRequest, BayesianObservationPolicyRequest, BayesianSurrogatePolicyRequest } from "../../api";
import type { AppLocale } from "../../i18n/types";

export const boText = (locale: AppLocale, ko: string, en: string) => locale === "ko" ? ko : en;

export interface BayesianNoiseDraft {
  noiseMode: BayesianSurrogatePolicyRequest["noise_mode"];
  noiseInitial: string;
  noiseLower: string;
  noiseUpper: string;
  fixedNoiseSd: string;
  observationMode: BayesianObservationPolicyRequest["mode"];
  nearbyUnits: "actual" | "normalized";
  nearbyTolerances: Record<string, string>;
  sampleCount: string;
  minBatchDistance: string;
}

export const defaultNoiseDraft: BayesianNoiseDraft = {
  noiseMode: "estimate", noiseInitial: "0.01", noiseLower: "0.000001", noiseUpper: "1", fixedNoiseSd: "",
  observationMode: "retain_raw", nearbyUnits: "actual", nearbyTolerances: {}, sampleCount: "64", minBatchDistance: "0",
};

export function strictBoNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) return null;
  const number = Number(trimmed);
  return Number.isFinite(number) ? number : null;
}

type NoisePayload = Pick<BayesianNoiseBatchCreateRequest, "surrogate" | "observation_policy" | "batch_options">;
export function buildNoisePolicy(draft: BayesianNoiseDraft, factors: readonly Pick<BayesianFactorResponse, "factor_id">[]):
  { payload: NoisePayload | null; errors: Record<string, string> } {
  const errors: Record<string, string> = {};
  const initial = strictBoNumber(draft.noiseInitial), lower = strictBoNumber(draft.noiseLower), upper = strictBoNumber(draft.noiseUpper);
  if (initial === null || initial <= 0) errors.noiseInitial = "positive";
  if (lower === null || lower <= 0) errors.noiseLower = "positive";
  if (upper === null || upper <= 0) errors.noiseUpper = "positive";
  if (lower !== null && upper !== null && lower >= upper) {
    errors.noiseLower = "bounds";
    errors.noiseUpper = "bounds";
  }
  if (initial !== null && lower !== null && upper !== null && !(lower < upper && lower <= initial && initial <= upper)) errors.noiseInitial = "bounds";
  const fixed = draft.noiseMode === "fixed" ? strictBoNumber(draft.fixedNoiseSd) : null;
  if (draft.noiseMode === "fixed" && (fixed === null || fixed <= 0)) errors.fixedNoiseSd = "positive";
  const samples = strictBoNumber(draft.sampleCount), distance = strictBoNumber(draft.minBatchDistance);
  if (samples === null || !Number.isInteger(samples) || samples < 16 || samples > 256) errors.sampleCount = "samples";
  if (distance === null || distance < 0) errors.minBatchDistance = "nonnegative";
  const tolerances: Array<[string, number]> = [];
  if (draft.observationMode === "nearby_diagnostics") for (const factor of factors) {
    const tolerance = strictBoNumber(draft.nearbyTolerances[factor.factor_id] ?? "");
    if (tolerance === null || tolerance < 0) errors[`tolerance:${factor.factor_id}`] = "nonnegative";
    else tolerances.push([factor.factor_id, tolerance]);
  }
  if (Object.keys(errors).length) return { payload: null, errors };
  return { errors, payload: {
    surrogate: { noise_mode: draft.noiseMode, initial_noise_variance_scaled: initial!, lower_noise_variance_scaled: lower!, upper_noise_variance_scaled: upper!, fixed_noise_sd: fixed },
    observation_policy: { mode: draft.observationMode, nearby_units: draft.nearbyUnits,
      nearby_tolerances: draft.observationMode === "nearby_diagnostics" ? Object.fromEntries(tolerances) : null },
    batch_options: { posterior_sample_count: samples!, min_batch_distance_normalized: distance! },
  } };
}

export function noiseInputError(code: string, locale: AppLocale): string {
  if (code === "bounds") return boText(locale, "양수 하한 < 상한이며, 초기값은 두 경계 안이어야 합니다.", "Positive lower < upper; initial variance must be within both bounds.");
  if (code === "samples") return boText(locale, "16~256 사이의 정수를 입력하세요.", "Enter an integer from 16 through 256.");
  return code === "positive" ? boText(locale, "유한한 양수를 입력하세요.", "Enter a finite positive value.") : boText(locale, "0 이상의 유한한 값을 입력하세요.", "Enter a finite nonnegative value.");
}
