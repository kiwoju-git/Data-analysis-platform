import type { AnalysisReportCapability } from "./api";
import type { StoredReportCapability } from "./api/types/reports";
import { useI18n } from "./i18n/LocaleProvider";

export function AnalysisReportCapabilityPanel({ capability, error, loading, onRetry }: {
  capability: AnalysisReportCapability | null;
  error: string | null;
  loading: boolean;
  onRetry?: () => void;
}) {
  return <ReportCapabilityContent capability={capability} sourceHash={capability?.source_result_sha256 ?? null} error={error} loading={loading} onRetry={onRetry} />;
}

export function StoredReportCapabilityPanel({ capability, error, loading, onRetry }: {
  capability: StoredReportCapability | null; error: string | null; loading: boolean; onRetry: () => void;
}) {
  return <ReportCapabilityContent capability={capability} sourceHash={capability?.source_ref_sha256 ?? null} error={error} loading={loading} onRetry={onRetry} dedicated />;
}

function ReportCapabilityContent({ capability, sourceHash, error, loading, onRetry, dedicated = false }: {
  capability: Pick<AnalysisReportCapability, "report_level" | "stale" | "reason" | "renderer_id" | "renderer_version" | "sections"> | null;
  sourceHash: string | null; error: string | null; loading: boolean; onRetry?: () => void; dedicated?: boolean;
}) {
  const { t } = useI18n();
  return (
    <section className="analysis-report-capability" data-report-capability={loading ? "loading" : capability?.report_level ?? "unknown"} aria-label={t("reportCapability.title")}>
      <strong>{t("reportCapability.title")}</strong>
      {capability === null ? (
        <div className={error === null ? "notice-box" : "error-box"} role={error === null ? "status" : "alert"}>
          <p>{t(loading ? "reportCapability.loading" : dedicated ? "managedReports.unknown" : "reportCapability.unknown")}</p>
          {error !== null ? <code>{error}</code> : null}
          {!loading && onRetry !== undefined ? <button type="button" className="secondary-button compact-button" onClick={onRetry}>{t("reportCenter.retry")}</button> : null}
        </div>
      ) : (
        <>
          <p><strong>{t(dedicated && capability.report_level === "unsupported" ? "managedReports.unsupported" : `reportCapability.${capability.report_level}`)}</strong></p>
          <p className="field-note">{t("reportCapability.storedOnly")}</p>
          {capability.stale ? <p className="notice-box">{t(dedicated ? "managedReports.staleSource" : "reportCapability.stale")}</p> : null}
          {capability.reason !== null ? <p><code>{capability.reason}</code></p> : null}
          <dl className="result-provenance">
            <dt>{t(dedicated ? "managedReports.referenceHash" : "reportCapability.source")}</dt><dd><code>{sourceHash}</code></dd>
            <dt>{t("reportCapability.renderer")}</dt><dd>{capability.renderer_id ?? "-"} / {capability.renderer_version ?? "-"}</dd>
          </dl>
          {capability.sections.length > 0 ? <details>
            <summary>{t("reportCapability.sections")}</summary>
            <div className="table-wrap"><table><thead><tr><th>{t("reportCapability.section")}</th><th>{t("reportCapability.status")}</th><th>{t("reportCapability.reason")}</th></tr></thead>
              <tbody>{capability.sections.map((section) => <tr key={section.section_id}>
                <td>{section.title}</td><td>{t(`reportCapability.${section.status}`)}</td><td>{section.reason === null ? "-" : <code>{section.reason}</code>}</td>
              </tr>)}</tbody>
            </table></div>
          </details> : null}
        </>
      )}
    </section>
  );
}
