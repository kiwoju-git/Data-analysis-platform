import { useCallback, useEffect, useRef, useState } from "react";
import type { AppLocale } from "./i18n/types";
import type { ManagedReportDescriptor, ManagedReportList, ReportSourceDescriptor, ReportSourceKind, ReportSourceList, StoredReportCapability, StoredSourceSnapshot } from "./api/types/reports";
import { createManagedReport, deleteManagedReport, fetchManagedReport, fetchManagedReportDownload, fetchManagedReports, fetchReportSources, fetchStoredReportCapability, fetchStoredSourceSnapshot } from "./api/reports";
import { triggerBrowserDownload } from "./api/client";
import { appLocationChangeEvent, pushAppLocation } from "./browserNavigation";
import { createLatestRequestGuard } from "./latestRequest";
import { isManagedReport, isReportSourceDescriptor, isStoredReportCapability, isStoredSourceSnapshot, managedReportQuery, reportSourceKey } from "./managedReportSource";

interface QueryState<T> { key: string; value: T | null; error: string | null; loading: boolean }
type Selection = Pick<ReportSourceDescriptor, "source" | "source_ref_sha256" | "title"> & { open_target?: string };
const initialQuery = () => managedReportQuery(typeof window === "undefined" ? "" : window.location.search);
const errorCode = (error: unknown) => error instanceof Error && /^[a-z][a-z0-9_]*$/u.test(error.message) ? error.message : "managed_report_request_failed";

export function useManagedReports(locale: AppLocale, revision: number) {
  const [kind, setKind] = useState<ReportSourceKind>(() => initialQuery().kind);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [linkedReport, setLinkedReport] = useState<ManagedReportDescriptor | null>(null);
  const [routeError, setRouteError] = useState<string | null>(() => initialQuery().error);
  const [routeLoading, setRouteLoading] = useState(false);
  const invalidQuery = routeError === "managed_report_query_invalid";
  const listKey = JSON.stringify([kind, offset, revision, invalidQuery]);
  const detailKey = JSON.stringify([selected === null ? null : reportSourceKey(selected.source), selected?.source_ref_sha256, locale, revision]);
  const context = useRef({ listKey, detailKey });
  context.current = { listKey, detailKey };
  const epoch = useRef(0);
  const requests = useRef({ list: createLatestRequestGuard(), capability: createLatestRequestGuard(), artifacts: createLatestRequestGuard(), action: createLatestRequestGuard(), route: createLatestRequestGuard(), snapshot: createLatestRequestGuard() }).current;
  const [list, setList] = useState<QueryState<ReportSourceList>>({ key: "", value: null, error: null, loading: false });
  const [capability, setCapability] = useState<QueryState<StoredReportCapability>>({ key: "", value: null, error: null, loading: false });
  const [artifacts, setArtifacts] = useState<QueryState<ManagedReportList>>({ key: "", value: null, error: null, loading: false });
  const [snapshot, setSnapshot] = useState<QueryState<StoredSourceSnapshot>>({ key: "", value: null, error: null, loading: false });
  const [action, setAction] = useState<{ key: string; busy: boolean; error: string | null; completed: "created" | "deleted" | null }>({ key: "", busy: false, error: null, completed: null });
  const [deleteTarget, setDeleteTarget] = useState<ManagedReportDescriptor | null>(null);
  const lastRoute = useRef<string | null>(null);

  const choose = useCallback((source: Selection | null) => {
    epoch.current += 1;
    requests.capability.cancel(); requests.artifacts.cancel(); requests.action.cancel(); requests.route.cancel();
    setSelected(source); setLinkedReport(null); setDeleteTarget(null); setRouteError(null); setRouteLoading(false);
    setAction({ key: "", busy: false, error: null, completed: null });
    requests.snapshot.cancel(); setSnapshot({ key: "", value: null, error: null, loading: false });
  }, [requests]);

  const refreshList = useCallback(async () => {
    const token = requests.list.begin();
    const current = () => context.current.listKey === listKey && requests.list.isCurrent(token);
    setList({ key: listKey, value: null, error: null, loading: !invalidQuery });
    if (invalidQuery) return;
    try {
      const result = await fetchReportSources(kind, offset);
      if (!current()) return;
      if (!Array.isArray(result.items) || result.items.some((item) => !isReportSourceDescriptor(item) || item.source.kind !== kind)) throw new Error("managed_report_source_invalid");
      setList({ key: listKey, value: result, error: null, loading: false });
    } catch (error) { if (current()) setList({ key: listKey, value: null, error: errorCode(error), loading: false }); }
  }, [invalidQuery, kind, listKey, offset, requests]);

  const refreshCapability = useCallback(async () => {
    const token = requests.capability.begin(), ownerEpoch = epoch.current;
    const current = () => epoch.current === ownerEpoch && context.current.detailKey === detailKey && requests.capability.isCurrent(token);
    setCapability({ key: detailKey, value: null, error: null, loading: selected !== null });
    if (selected === null) return;
    try {
      const result = await fetchStoredReportCapability(selected.source, locale);
      if (!current()) return;
      if (!isStoredReportCapability(result) || reportSourceKey(result.source) !== reportSourceKey(selected.source) || result.source_ref_sha256 !== selected.source_ref_sha256 || result.locale !== locale) throw new Error("managed_report_source_invalid");
      setCapability({ key: detailKey, value: result, error: null, loading: false });
    } catch (error) { if (current()) setCapability({ key: detailKey, value: null, error: errorCode(error), loading: false }); }
  }, [detailKey, locale, requests, selected]);

  const loadSnapshot = useCallback(async () => {
    if (selected === null) return;
    const token = requests.snapshot.begin(), ownerEpoch = epoch.current;
    const current = () => epoch.current === ownerEpoch && context.current.detailKey === detailKey && requests.snapshot.isCurrent(token);
    setSnapshot({ key: detailKey, value: null, error: null, loading: true });
    try {
      const result = await fetchStoredSourceSnapshot(selected.source, locale);
      if (!current()) return;
      if (!isStoredSourceSnapshot(result) || reportSourceKey(result.source) !== reportSourceKey(selected.source) || result.source_ref_sha256 !== selected.source_ref_sha256 || result.locale !== locale) throw new Error("managed_report_source_invalid");
      setSnapshot({ key: detailKey, value: result, error: null, loading: false });
    } catch (error) { if (current()) setSnapshot({ key: detailKey, value: null, error: errorCode(error), loading: false }); }
  }, [detailKey, locale, requests, selected]);

  const refreshArtifacts = useCallback(async () => {
    const token = requests.artifacts.begin(), ownerEpoch = epoch.current;
    const current = () => epoch.current === ownerEpoch && context.current.detailKey === detailKey && requests.artifacts.isCurrent(token);
    setArtifacts({ key: detailKey, value: null, error: null, loading: selected !== null });
    if (selected === null) return;
    try {
      const result = await fetchManagedReports(selected.source, locale);
      if (!current()) return;
      if (!Array.isArray(result.items) || result.items.some((item) => !isManagedReport(item) || reportSourceKey(item.source) !== reportSourceKey(selected.source) || item.source_ref_sha256 !== selected.source_ref_sha256 || item.locale !== locale)) throw new Error("managed_report_source_invalid");
      setArtifacts({ key: detailKey, value: result, error: null, loading: false });
    } catch (error) { if (current()) setArtifacts({ key: detailKey, value: null, error: errorCode(error), loading: false }); }
  }, [detailKey, locale, requests, selected]);

  useEffect(() => { void refreshList(); return () => requests.list.cancel(); }, [refreshList, requests]);
  useEffect(() => {
    setAction({ key: detailKey, busy: false, error: null, completed: null });
    setSnapshot({ key: detailKey, value: null, error: null, loading: false });
    void refreshCapability(); void refreshArtifacts();
    return () => { requests.capability.cancel(); requests.artifacts.cancel(); requests.action.cancel(); requests.snapshot.cancel(); };
  }, [detailKey, refreshArtifacts, refreshCapability, requests]);

  useEffect(() => {
    const sync = () => {
      const query = initialQuery();
      setKind(query.kind); setOffset(0);
      const queryKey = JSON.stringify([query.reportId, query.error]);
      if (lastRoute.current === queryKey) return;
      lastRoute.current = queryKey;
      choose(null); setRouteError(query.error);
      if (query.error !== null || query.reportId === null) return;
      const token = requests.route.begin();
      setRouteLoading(true);
      void fetchManagedReport(query.reportId).then((result) => {
        if (!requests.route.isCurrent(token)) return;
        if (!isManagedReport(result) || result.export_id !== query.reportId) throw new Error("managed_report_source_invalid");
        setSelected({ source: result.source, source_ref_sha256: result.source_ref_sha256, title: result.export_id });
        setLinkedReport(result);
      }).catch((error: unknown) => { if (requests.route.isCurrent(token)) setRouteError(errorCode(error)); })
        .finally(() => { if (requests.route.isCurrent(token)) setRouteLoading(false); });
    };
    sync();
    window.addEventListener("popstate", sync); window.addEventListener(appLocationChangeEvent, sync);
    return () => { window.removeEventListener("popstate", sync); window.removeEventListener(appLocationChangeEvent, sync); lastRoute.current = null; requests.route.cancel(); };
  }, [choose, requests]);

  useEffect(() => () => { epoch.current += 1; Object.values(requests).forEach((guard) => guard.cancel()); }, [requests]);

  async function perform(operation: "create" | "download" | "delete", report?: ManagedReportDescriptor) {
    const ownerEpoch = epoch.current;
    if (selected === null) return;
    const cap = capability.key === detailKey ? capability.value : null;
    if (operation === "create" && (cap === null || !cap.html_available || cap.report_level === "unsupported")) return;
    if (report !== undefined && (reportSourceKey(report.source) !== reportSourceKey(selected.source) || report.source_ref_sha256 !== selected.source_ref_sha256)) return;
    const token = requests.action.begin();
    const current = () => epoch.current === ownerEpoch && context.current.detailKey === detailKey && requests.action.isCurrent(token);
    setAction({ key: detailKey, busy: true, error: null, completed: null });
    try {
      if (operation === "create") {
        const result = await createManagedReport(selected.source, locale, selected.source_ref_sha256);
        if (!current()) return;
        if (!isManagedReport(result) || reportSourceKey(result.source) !== reportSourceKey(selected.source) || result.source_ref_sha256 !== selected.source_ref_sha256 || result.locale !== locale) throw new Error("managed_report_source_invalid");
        setLinkedReport(result);
      } else if (operation === "download" && report !== undefined) {
        const download = await fetchManagedReportDownload(report);
        if (!current()) return;
        triggerBrowserDownload(download.blob, download.filename);
      } else if (operation === "delete" && report !== undefined) {
        const response = await deleteManagedReport(report);
        if (!current()) return;
        if (response.deleted !== true) throw new Error("managed_report_request_failed");
        setLinkedReport((previous) => previous?.export_id === report.export_id ? null : previous); setDeleteTarget(null);
      }
      if (!current()) return;
      setAction({ key: detailKey, busy: false, error: null, completed: operation === "download" ? null : operation === "create" ? "created" : "deleted" });
      if (operation !== "download") void refreshArtifacts();
    } catch (error) {
      if (current()) { setAction({ key: detailKey, busy: false, error: errorCode(error), completed: null }); if (operation === "create") void refreshCapability(); }
    }
  }

  return {
    kind, offset, selected, linkedReport, routeError, routeLoading,
    list: list.key === listKey ? list : { key: listKey, value: null, error: null, loading: true },
    capability: capability.key === detailKey ? capability : { key: detailKey, value: null, error: null, loading: selected !== null },
    artifacts: artifacts.key === detailKey ? artifacts : { key: detailKey, value: null, error: null, loading: selected !== null },
    snapshot: snapshot.key === detailKey ? snapshot : { key: detailKey, value: null, error: null, loading: false },
    action: action.key === detailKey ? action : { key: detailKey, busy: false, error: null, completed: null },
    deleteTarget: deleteTarget !== null && selected !== null && reportSourceKey(deleteTarget.source) === reportSourceKey(selected.source) && deleteTarget.source_ref_sha256 === selected.source_ref_sha256 ? deleteTarget : null,
    setDeleteTarget, refreshList, refreshCapability, refreshArtifacts, loadSnapshot,
    createReport: () => { void perform("create"); }, downloadReport: (report: ManagedReportDescriptor) => { void perform("download", report); }, deleteReport: (report: ManagedReportDescriptor) => { void perform("delete", report); },
    retryRoute: () => { lastRoute.current = null; window.dispatchEvent(new Event(appLocationChangeEvent)); },
    select: (source: ReportSourceDescriptor) => {
      if (selected === null || selected.source_ref_sha256 !== source.source_ref_sha256 || reportSourceKey(selected.source) !== reportSourceKey(source.source)) choose(source);
      lastRoute.current = JSON.stringify([null, null]);
      const url = new URL(window.location.href); url.searchParams.delete("report_id"); url.searchParams.set("source_kind", kind); pushAppLocation(`${url.pathname}${url.search}${url.hash}`);
    },
    changeKind: (value: ReportSourceKind) => { requests.list.cancel(); setKind(value); setOffset(0); const url = new URL(window.location.href); url.searchParams.set("source_kind", value); pushAppLocation(`${url.pathname}${url.search}${url.hash}`); },
    changeOffset: (value: number) => { requests.list.cancel(); setOffset(Math.max(0, value)); },
  };
}
