import { useEffect, useRef, useState } from "react";
import type { AnyBayesianStudyResponse } from "../../../api/types/boMixed";
import type { DatasetImportPreflightResponse, DatasetImportRequest } from "../../../api/types/boDatasetImport";
import { createDatasetStudy, preflightDatasetImport } from "../../../api/boDatasetImport";
import { createDatasetImportSession } from "../boDatasetImportSession";
import { bayesianRequestId } from "../bayesianRequestId";
import { validDatasetImportedInitialDesign } from "../boDatasetSource";
import { planningHash } from "../boPlanningDraft";
import { sameDesirabilityJson } from "../desirabilityResponseGuard";

const normalizedFilter = (filter: DatasetImportRequest["filter_snapshot"]) => ({
  ...filter, conditions: filter.conditions.map(condition => ({ ...condition, value: condition.value ?? null })),
});

export function useDatasetImport(onCreated: (study: AnyBayesianStudyResponse) => void) {
  const session = useRef(createDatasetImportSession()).current;
  const abort = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState<"preflight" | "create" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [review, setReview] = useState<{ request: DatasetImportRequest; result: DatasetImportPreflightResponse } | null>(null);
  const [retryAvailable, setRetryAvailable] = useState(false);
  useEffect(() => () => { session.invalidate(); abort.current?.abort(); }, [session]);
  function invalidate() {
    session.invalidate(); abort.current?.abort(); setBusy(null); setError(null); setReview(null); setRetryAvailable(false);
  }
  async function preflight(request: DatasetImportRequest | string) {
    invalidate();
    if (typeof request === "string") { setError(request); return; }
    const token = session.begin();
    const controller = new AbortController(); abort.current = controller;
    setBusy("preflight");
    try {
      const result = await preflightDatasetImport(request, controller.signal);
      if (result.schema_version !== 1 || result.source?.dataset_version_id !== request.dataset_version_id ||
        result.source.schema_hash !== request.expected_schema_hash || !planningHash(result.preflight_sha256)) throw new Error("bayesian_import_source_mismatch");
      if (session.current(token)) setReview({ request: structuredClone(request), result });
    } catch (cause) {
      if (session.current(token)) setError(errorCode(cause));
    } finally { if (session.current(token)) setBusy(null); }
  }
  async function create(retry = false) {
    if (review === null || busy !== null) return;
    const token = session.begin(); setBusy("create"); setError(null);
    try {
      const request = retry ? session.retry() : { ...review.request, request_id: bayesianRequestId(), expected_preflight_sha256: review.result.preflight_sha256 };
      if (request === null) throw new Error("bayesian_import_review_required");
      session.remember(request);
      const created = await createDatasetStudy(request);
      const receipt = created.initial_design;
      if (!validDatasetImportedInitialDesign(receipt) || receipt.request_id !== request.request_id ||
        receipt.preflight_sha256 !== request.expected_preflight_sha256 || receipt.source.dataset_version_id !== request.dataset_version_id ||
        receipt.source.schema_hash !== request.expected_schema_hash || !sameDesirabilityJson(receipt.source, review.result.source) ||
        receipt.missing_policy !== request.missing_policy || !sameDesirabilityJson(normalizedFilter(receipt.filter_snapshot), normalizedFilter(request.filter_snapshot)) ||
        !sameDesirabilityJson(receipt.factor_columns, Object.fromEntries(request.factor_mappings.map(row => [row.factor.factor_id, row.column_id]))) ||
        !sameDesirabilityJson(receipt.response_columns, Object.fromEntries(request.response_mappings.map(row => [row.response_id ?? "objective", row.column_id])))) throw new Error("bayesian_import_source_mismatch");
      if (session.current(token)) { setRetryAvailable(false); onCreated(created); }
    } catch (cause) {
      if (session.current(token)) { setError(errorCode(cause)); setRetryAvailable(session.retry() !== null); }
    } finally { if (session.current(token)) setBusy(null); }
  }
  return { busy, error, review, retryAvailable, invalidate, preflight, create };
}
function errorCode(cause: unknown): string {
  const code = cause instanceof Error ? cause.message : "";
  return /^bayesian_[a-z0-9_]+$/.test(code) ? code : "bayesian_import_failed";
}
