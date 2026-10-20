import { t, type TranslationKey } from "../i18n/translate";

const reasons: Record<string, TranslationKey> = {
  no_replicated_design_points: "doe.lof.noReplication",
  no_lack_of_fit_df: "doe.lof.noDf",
  pure_error_variance_zero: "doe.lof.zeroVariance",
  numerical_decomposition_failure: "doe.lof.numerical",
};
export function DoeLackOfFitNotice({ lack }: {
  lack: { available: boolean; reason?: string | null; replication_grouping_policy?: string | null; non_curvature_reason?: string | null };
}) {
  return <div className="doe-lof-notice">
    {!lack.available ? <p className="notice-box notice-warning">{lack.reason && reasons[lack.reason] ? t(reasons[lack.reason]) : t("doe.lof.legacyUnavailable")}</p> : null}
    {lack.non_curvature_reason && reasons[lack.non_curvature_reason] ? <p className="field-help">{t("doe.terms.otherLackOfFit")}: {t(reasons[lack.non_curvature_reason])}</p> : null}
    {lack.replication_grouping_policy ? <p className="field-help">{t("doe.lof.replicationPolicy")}</p> : null}
  </div>;
}
