import { useI18n } from "./i18n/LocaleProvider";

export function ReportCenterFeedback({
  code,
  onRetry,
}: {
  code: string;
  onRetry?: () => void;
}) {
  const { t } = useI18n();
  const message = code === "report_center_analysis_id_invalid"
    ? t("reportCenter.invalidSelection")
    : code === "report_center_result_identity_mismatch"
      ? t("reportCenter.identityMismatch")
      : code === "report_center_current_dataset_required"
        ? t("reportCenter.datasetRequired")
        : code === "report_center_result_removed"
          ? t("reportCenter.resultRemoved")
          : code === "api_unreachable"
            ? t("reportCenter.apiUnavailable")
            : t("reportCenter.requestFailed");
  const informational = code === "report_center_current_dataset_required"
    || code === "report_center_result_removed";
  return (
    <div
      className={informational ? "notice-box" : "error-box"}
      data-report-feedback={code}
      role={informational ? "status" : "alert"}
    >
      <span>{message}</span>
      {!informational ? <code>{code}</code> : null}
      {onRetry !== undefined ? (
        <button className="secondary-button compact-button" onClick={onRetry} type="button">
          {t("reportCenter.retry")}
        </button>
      ) : null}
    </div>
  );
}
