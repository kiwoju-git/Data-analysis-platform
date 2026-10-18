import { useManagedReports } from "./useManagedReports";
import { useI18n } from "./i18n/LocaleProvider";
import { REPORT_SOURCE_KINDS, safeReportOpenTarget } from "./managedReportSource";
import type { ManagedReportDescriptor, ReportSourceKind, StoredSourceSnapshot } from "./api/types/reports";
import { StoredReportCapabilityPanel } from "./AnalysisReportCapabilityPanel";
import { formatDateTime } from "./analysisWorkbenchUtils";

export function ManagedReportsBrowser({ workspaceRevision }: { workspaceRevision: number }) {
  const { locale, t } = useI18n();
  const state = useManagedReports(locale, workspaceRevision);
  const cap = state.capability.value;
  const target = state.selected?.open_target === undefined ? null : safeReportOpenTarget(state.selected.open_target);
  const reports = [...(state.artifacts.value?.items ?? [])];
  if (state.linkedReport !== null && !reports.some((report) => report.export_id === state.linkedReport?.export_id)) reports.unshift(state.linkedReport);
  return <div className="report-browser-workspace managed-reports-browser">
    <section className="report-browser" aria-labelledby="managed-report-sources-title">
      <div className="panel-heading"><h3 id="managed-report-sources-title">{t("managedReports.sources")}</h3>
        <button className="secondary-button" type="button" disabled={state.list.loading} onClick={() => void state.refreshList()}>{t("managedReports.refresh")}</button></div>
      <label className="managed-report-kind">{t("managedReports.kind")}<select value={state.kind} data-report-source-kind onChange={(event) => state.changeKind(event.currentTarget.value as ReportSourceKind)}>
        {REPORT_SOURCE_KINDS.map((kind) => <option key={kind} value={kind}>{t(`managedReports.kind.${kind}`)}</option>)}
      </select></label>
      {state.routeError !== null ? <Feedback error={state.routeError} retry={state.retryRoute} /> : null}
      {state.routeLoading ? <p role="status">{t("managedReports.loading")}</p> : null}
      {state.list.error !== null ? <Feedback error={state.list.error} retry={() => void state.refreshList()} /> : null}
      {state.list.loading ? <p role="status">{t("managedReports.loading")}</p> : null}
      {state.list.value?.items.length === 0 ? <p>{t("managedReports.emptySources")}</p> : null}
      <div className="report-run-list">{state.list.value?.items.map((item) => <article key={item.source_ref_sha256} className="report-run-item">
        <button type="button" className={state.selected?.source_ref_sha256 === item.source_ref_sha256 ? "report-run-row is-selected" : "report-run-row"}
          aria-current={state.selected?.source_ref_sha256 === item.source_ref_sha256 ? "true" : undefined} data-report-source={item.source_ref_sha256} onClick={() => state.select(item)}>
          <span><strong>{item.title}</strong><code>{item.source_ref_sha256}</code></span>
          <span>{t(`managedReports.kind.${item.source.kind}`)}</span><span>{formatDateTime(item.created_at)}</span>
          <span>{t(item.stale ? "managedReports.stale" : "managedReports.notMarkedStale")}</span>
        </button>
      </article>)}</div>
      {state.list.value !== null ? <div className="analysis-history-pagination"><span>{state.list.value.items.length === 0 ? 0 : state.offset + 1} - {state.offset + state.list.value.items.length}</span><div>
        <button type="button" className="secondary-button compact-button" disabled={state.offset === 0} onClick={() => state.changeOffset(state.offset - 20)}>{t("managedReports.previous")}</button>
        <button type="button" className="secondary-button compact-button" disabled={!state.list.value.has_more} onClick={() => state.changeOffset(state.offset + 20)}>{t("managedReports.next")}</button>
      </div></div> : null}
    </section>
    {state.selected !== null ? <section className="report-selected-result" data-managed-report-selection={state.selected.source_ref_sha256}>
      <div className="panel-heading"><h3>{cap?.title ?? state.selected.title}</h3>{target === null ? null : <a href={target}>{t("managedReports.openSource")}</a>}</div>
      <p>{t(`managedReports.kind.${state.selected.source.kind}`)}</p>
      <details><summary>{t("managedReports.exactSource")}</summary><pre className="managed-report-source-json">{JSON.stringify(state.selected.source, null, 2)}</pre></details>
      <div><button type="button" className="secondary-button compact-button" data-view-stored-source disabled={state.snapshot.loading} onClick={() => void state.loadSnapshot()}>{t(state.snapshot.loading ? "managedReports.loading" : "managedReports.viewSnapshot")}</button></div>
      {state.snapshot.error !== null ? <Feedback error={state.snapshot.error} retry={() => void state.loadSnapshot()} /> : null}
      {state.snapshot.value !== null ? <StoredSourceSnapshotView snapshot={state.snapshot.value} /> : null}
      <StoredReportCapabilityPanel capability={cap} loading={state.capability.loading} error={state.capability.error} onRetry={() => void state.refreshCapability()} />
      <div className="button-row"><button type="button" className="primary-button" data-create-managed-report disabled={state.action.busy || cap === null || !cap.html_available || cap.report_level === "unsupported"} onClick={state.createReport}>{t(state.action.busy ? "managedReports.working" : "managedReports.create")}</button></div>
      {state.action.error !== null ? <Feedback error={state.action.error} /> : null}
      {state.action.completed !== null ? <p role="status">{t(`managedReports.${state.action.completed}`)}</p> : null}
      <div className="panel-heading"><h4>{t("managedReports.artifacts")}</h4><button type="button" className="secondary-button compact-button" disabled={state.artifacts.loading} onClick={() => void state.refreshArtifacts()}>{t("managedReports.refresh")}</button></div>
      {state.artifacts.loading ? <p role="status">{t("managedReports.loading")}</p> : null}
      {state.artifacts.error !== null ? <Feedback error={state.artifacts.error} retry={() => void state.refreshArtifacts()} /> : null}
      {!state.artifacts.loading && state.artifacts.error === null && reports.length === 0 ? <p>{t("managedReports.emptyReports")}</p> : null}
      <div className="table-wrap"><table><thead><tr><th>{t("managedReports.artifact")}</th><th>{t("managedReports.locale")}</th><th>{t("reportCapability.title")}</th><th>{t("managedReports.createdAt")}</th><th>{t("managedReports.actions")}</th></tr></thead>
        <tbody>{reports.map((report) => <tr key={report.export_id} data-managed-report={report.export_id}><td><code>{report.export_id}</code><details><summary>SHA-256</summary><code>{report.sha256}</code></details></td>
          <td>{report.locale.toUpperCase()}</td><td>{t(`managedReports.level.${report.report_level}`)}{report.stale ? <span className="stale-badge">{t("managedReports.stale")}</span> : null}</td><td>{formatDateTime(report.created_at)}</td><td><div className="button-row">
            <button type="button" className="secondary-button compact-button" disabled={state.action.busy} onClick={() => state.downloadReport(report)}>{t("managedReports.download")}</button>
            <button type="button" className="secondary-button compact-button" disabled={state.action.busy} onClick={() => state.setDeleteTarget(report)}>{t("managedReports.delete")}</button>
          </div></td></tr>)}</tbody></table></div>
      {state.deleteTarget !== null ? <DeleteConfirmation report={state.deleteTarget} busy={state.action.busy} cancel={() => state.setDeleteTarget(null)} confirm={() => state.deleteReport(state.deleteTarget!)} /> : null}
    </section> : null}
  </div>;
}

export function StoredSourceSnapshotView({ snapshot }: { snapshot: StoredSourceSnapshot }) {
  const { t } = useI18n();
  return <section className="stored-source-snapshot" data-stored-source-snapshot={snapshot.source_ref_sha256} aria-label={t("managedReports.snapshotTitle")}>
    <h4>{t("managedReports.snapshotTitle")}</h4><p className="field-help">{t("managedReports.snapshotHelp")}</p>
    <dl className="result-provenance"><dt>{t("managedReports.createdAt")}</dt><dd>{formatDateTime(snapshot.created_at)}</dd>
      <dt>{t("managedReports.referenceHash")}</dt><dd><code>{snapshot.source_ref_sha256}</code></dd></dl>
    {snapshot.stale ? <p className="notice-box">{t("managedReports.staleSource")}</p> : null}
    <pre className="managed-report-source-json managed-report-snapshot-json" tabIndex={0} aria-label={t("managedReports.snapshotPayload")}>{JSON.stringify(snapshot.payload, null, 2)}</pre>
  </section>;
}

function Feedback({ error, retry }: { error: string; retry?: () => void }) {
  const { t } = useI18n();
  return <div className="error-box" role="alert"><p>{t("managedReports.error")}</p><code>{error}</code>{retry === undefined ? null : <button type="button" className="secondary-button compact-button" onClick={retry}>{t("reportCenter.retry")}</button>}</div>;
}
function DeleteConfirmation({ report, busy, cancel, confirm }: { report: ManagedReportDescriptor; busy: boolean; cancel: () => void; confirm: () => void }) {
  const { t } = useI18n();
  return <div className="notice-box warning" role="region" aria-label={t("managedReports.confirmDelete")}><p>{t("managedReports.deleteOnlyReport")}</p><code>{report.export_id}</code>
    <div className="button-row"><button className="secondary-button" type="button" disabled={busy} onClick={cancel}>{t("managedReports.cancel")}</button><button className="secondary-button" type="button" disabled={busy} onClick={confirm}>{t("managedReports.confirmDelete")}</button></div>
  </div>;
}
