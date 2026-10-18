import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { apiRequestError, fetchApi } from "./api/client";
import { apiRoutes } from "./api/routes";
import type { DatasetIntakeLimitsResponse } from "./api/types/datasets";
import { useI18n } from "./i18n/LocaleProvider";

export function DatasetIntakeLimitsSummary({ limits }: { limits: DatasetIntakeLimitsResponse }) {
  const { t, formatNumber } = useI18n();
  return <p className="muted dataset-intake-limits">
    {t("intake.limits", {
      file: formatNumber(limits.file_bytes), paste: formatNumber(limits.paste_utf8_bytes),
      request: formatNumber(limits.json_request_bytes),
      rows: formatNumber(limits.parsed_rows), columns: formatNumber(limits.parsed_columns),
    })}
  </p>;
}

export function DatasetIntakeLimits() {
  const { t } = useI18n();
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<
    { kind: "loading" } | { kind: "failed" } | { kind: "ready"; limits: DatasetIntakeLimitsResponse }
  >({ kind: "loading" });
  useEffect(() => {
    let current = true;
    const load = async () => {
      setState({ kind: "loading" });
      try {
        const response = await fetchApi(apiRoutes.datasetIntakeLimits());
        if (!response.ok) throw await apiRequestError(response, "intake_limits_unavailable");
        const limits = await response.json() as DatasetIntakeLimitsResponse;
        if (current) setState({ kind: "ready", limits });
      } catch {
        if (current) setState({ kind: "failed" });
      }
    };
    void load();
    return () => { current = false; };
  }, [attempt]);
  if (state.kind === "ready") return <DatasetIntakeLimitsSummary limits={state.limits} />;
  if (state.kind === "loading") return <p className="muted" role="status">{t("intake.limitsLoading")}</p>;
  return <div className="notice-box" role="status">
    {t("intake.limitsUnavailable")}
    <button type="button" className="secondary-button" title={t("intake.retry")} aria-label={t("intake.retry")}
      onClick={() => setAttempt((value) => value + 1)}><RefreshCw size={16} aria-hidden="true" /></button>
  </div>;
}
