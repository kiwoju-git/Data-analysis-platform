import { Fragment, useEffect, useMemo, useRef, useState } from "react";

import {
  deleteBayesianStudy,
  deleteDoeDesign,
  deleteStoredAnalysisRun,
  fetchAnalysisRunDeletionPreflight,
  fetchBayesianStudyDeletionPreflight,
  fetchDoeDesignDeletionPreflight,
  fetchWorkspaceAssets,
  updateWorkspaceAssetMetadata,
  type WorkspaceAssetCatalogResponse,
  type WorkspaceAssetCategory,
  type WorkspaceAssetDescriptor,
  type WorkspaceAssetSort,
} from "./api";
import { pushAppLocation } from "./browserNavigation";
import { CompactSettingsTable } from "./components/CompactSettingsTable";
import { formatLocalDateTime } from "./dateFormat";

interface PendingAssetDeletion {
  item: WorkspaceAssetDescriptor;
  manifestSha256: string;
  message: string;
}

export function UnifiedAssetCatalogPanel({
  category,
  onMutation,
  revision,
}: {
  category: WorkspaceAssetCategory | null;
  onMutation: () => void;
  revision: number;
}) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [pinnedOnly, setPinnedOnly] = useState(false);
  const [sort, setSort] = useState<WorkspaceAssetSort>("updated_desc");
  const [catalog, setCatalog] = useState<WorkspaceAssetCatalogResponse | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [pendingDeletion, setPendingDeletion] = useState<PendingAssetDeletion | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let current = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      void fetchWorkspaceAssets({
        category,
        pinned: pinnedOnly ? true : undefined,
        search,
        sort,
        status: statusFilter || undefined,
      })
        .then((response) => {
          if (!current) return;
          setCatalog(response);
          setSelectedKey((selected) =>
            response.items.some((item) => assetKey(item) === selected) ? selected : null,
          );
        })
        .catch((caught) => {
          if (current) setError(caught instanceof Error ? caught.message : "workspace_asset_catalog_failed");
        })
        .finally(() => {
          if (current) setLoading(false);
        });
    }, 120);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [category, pinnedOnly, refresh, revision, search, sort, statusFilter]);

  const selected = useMemo(
    () => catalog?.items.find((item) => assetKey(item) === selectedKey) ?? null,
    [catalog, selectedKey],
  );

  useEffect(() => {
    if (pendingDeletion === null) return;
    const dialog = dialogRef.current;
    const focusable = dialog?.querySelectorAll<HTMLElement>(
      "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])",
    );
    focusable?.[0]?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !deleting) {
        event.preventDefault();
        closeDeletionDialog(pendingDeletion.item);
        return;
      }
      if (event.key !== "Tab" || !focusable || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [deleting, pendingDeletion]);

  function closeDeletionDialog(item: WorkspaceAssetDescriptor) {
    setPendingDeletion(null);
    window.requestAnimationFrame(() => {
      document.getElementById(detailButtonId(item))?.focus();
    });
  }

  async function requestDeleteSelected() {
    if (selected === null || !isManagedDeletionType(selected.asset_type)) return;
    setDeleting(true);
    setError(null);
    try {
      const deletion = await prepareDeletion(selected);
      setPendingDeletion(deletion);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "workspace_asset_delete_failed");
    } finally {
      setDeleting(false);
    }
  }

  async function confirmDeleteSelected() {
    if (pendingDeletion === null) return;
    const target = pendingDeletion.item;
    setDeleting(true);
    setError(null);
    try {
      if (target.asset_type === "analysis_run") {
        await deleteStoredAnalysisRun(target.asset_id, {
          confirmation_analysis_id: target.asset_id,
          expected_deletion_manifest_sha256: pendingDeletion.manifestSha256,
        });
      } else if (target.asset_type === "doe_design") {
        await deleteDoeDesign(target.asset_id, pendingDeletion.manifestSha256);
      } else if (target.asset_type === "bayesian_study") {
        await deleteBayesianStudy(target.asset_id, {
          confirmation_study_id: target.asset_id,
          expected_deletion_manifest_sha256: pendingDeletion.manifestSha256,
        });
      }
      setPendingDeletion(null);
      setSelectedKey(null);
      setRefresh((value) => value + 1);
      onMutation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "workspace_asset_delete_failed");
    } finally {
      setDeleting(false);
    }
  }

  const filterFields = [
    {
      key: "search",
      label: "검색",
      controlId: "asset-catalog-search",
      columnClassName: "asset-filter-search-column",
      control: (
        <input
          id="asset-catalog-search"
          type="search"
          value={search}
          onChange={(event) => setSearch(event.currentTarget.value)}
          placeholder="이름, 방법 또는 주요 정보"
        />
      ),
    },
    {
      key: "status",
      label: "상태",
      controlId: "asset-catalog-status",
      columnClassName: "asset-filter-status-column",
      control: (
        <select id="asset-catalog-status" value={statusFilter} onChange={(event) => setStatusFilter(event.currentTarget.value)}>
          <option value="">전체 상태</option>
          <option value="available">사용 가능</option>
          <option value="succeeded">완료</option>
          <option value="active">진행 중</option>
          <option value="designed">설계됨</option>
          <option value="stale">Stale</option>
          <option value="archived">보관됨</option>
        </select>
      ),
    },
    {
      key: "sort",
      label: "정렬",
      controlId: "asset-catalog-sort",
      columnClassName: "asset-filter-sort-column",
      control: (
        <select id="asset-catalog-sort" value={sort} onChange={(event) => setSort(event.currentTarget.value as WorkspaceAssetSort)}>
          <option value="updated_desc">최근 수정</option>
          <option value="created_desc">최근 생성</option>
          <option value="name_asc">이름</option>
        </select>
      ),
    },
    {
      key: "display",
      label: "표시 옵션",
      columnClassName: "asset-filter-option-column",
      control: (
        <label className="doe-table-toggle">
          <input checked={pinnedOnly} type="checkbox" onChange={(event) => setPinnedOnly(event.currentTarget.checked)} />
          <span>고정만 보기</span>
        </label>
      ),
    },
  ] as const;

  return (
    <section className="unified-asset-catalog" aria-label="저장 자산 목록">
      <div className="panel-heading compact-heading asset-catalog-filter-heading">
        <div><h3>자산 검색</h3><p>이름, 상태와 정렬 기준으로 로컬 자산을 찾습니다.</p></div>
        <button className="secondary-button" onClick={() => setRefresh((value) => value + 1)} type="button">새로고침</button>
      </div>
      <CompactSettingsTable ariaLabel="자산 검색 조건" className="asset-filter-table" fields={filterFields} />
      {loading ? <p role="status">자산 목록 확인 중</p> : null}
      {error !== null ? <div className="error-box">오류 코드: {error}</div> : null}
      <div className="table-wrap asset-catalog-table-wrap">
        <table className="result-table asset-catalog-table">
          <colgroup><col className="asset-name-column" /><col className="asset-type-column" /><col /><col className="asset-status-column" /><col className="asset-date-column" /><col className="asset-action-column" /></colgroup>
          <thead><tr><th>이름</th><th>종류</th><th>주요 정보</th><th>상태</th><th>수정</th><th>작업</th></tr></thead>
          <tbody>
            {catalog?.items.map((item) => {
              const key = assetKey(item);
              const isSelected = selectedKey === key;
              const detailId = detailRowId(item);
              return (
                <Fragment key={key}>
                  <tr className={isSelected ? "asset-row-selected" : ""}>
                    <td><strong>{item.display_name}</strong>{item.pinned ? <span className="asset-pinned-label">고정</span> : null}</td>
                    <td>{assetTypeLabel(item.asset_type, item.subtype)}</td>
                    <td>{item.secondary_text}</td>
                    <td>{item.status}</td>
                    <td>{formatLocalDateTime(item.updated_at)}</td>
                    <td>
                      <button
                        aria-controls={detailId}
                        aria-expanded={isSelected}
                        className="secondary-button compact-button"
                        id={detailButtonId(item)}
                        onClick={() => setSelectedKey((current) => current === key ? null : key)}
                        type="button"
                      >
                        {isSelected ? "상세 닫기" : "상세"}
                      </button>
                    </td>
                  </tr>
                  {isSelected ? (
                    <tr className="asset-inline-detail-row" id={detailId}>
                      <td colSpan={6}>
                        <section className="asset-catalog-detail" aria-labelledby={`${detailId}-title`}>
                          <div className="panel-heading compact-heading"><div><h3 id={`${detailId}-title`}>{item.display_name}</h3><p>{assetTypeLabel(item.asset_type, item.subtype)} · {item.secondary_text}</p></div><span className="status-pill">{item.status}</span></div>
                          <dl className="asset-detail-grid"><div><dt>생성</dt><dd>{formatLocalDateTime(item.created_at)}</dd></div><div><dt>종속 자산</dt><dd>{item.dependency_count.toLocaleString()}개</dd></div><div><dt>Method</dt><dd>{item.method_id ?? "-"}</dd></div><div><dt>메모</dt><dd>{item.note ?? "-"}</dd></div></dl>
                          {isGenericMetadataType(item.asset_type) ? (
                            <WorkspaceAssetMetadataEditor
                              item={item as WorkspaceAssetDescriptor & { asset_type: "analysis_run" | "doe_design" | "bayesian_study" }}
                              onSaved={() => {
                                setRefresh((value) => value + 1);
                                onMutation();
                              }}
                            />
                          ) : null}
                          <div className="button-row asset-detail-actions">
                            <button className="primary-button" onClick={() => pushAppLocation(item.open_target.path)} type="button">{item.open_target.label}</button>
                            {isManagedDeletionType(item.asset_type) ? <button className="danger-button" disabled={deleting} onClick={() => void requestDeleteSelected()} type="button">{deleting ? "확인 중" : "삭제 영향 확인"}</button> : null}
                          </div>
                          {item.asset_type === "dataset_version" || item.asset_type === "regression_model" ? <p className="compact-note">이름, 메모, 고정과 파일 정리 작업은 해당 자산 종류 탭의 선택 상세에서 변경합니다.</p> : null}
                          <details><summary>기술 정보</summary><dl className="asset-detail-grid"><div><dt>Asset ID</dt><dd className="technical-value">{item.asset_id}</dd></div><div><dt>Subtype</dt><dd>{item.subtype}</dd></div></dl></details>
                        </section>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      {catalog?.items.length === 0 ? <div className="empty-state">조건에 맞는 저장 자산이 없습니다.</div> : null}
      {pendingDeletion !== null ? (
        <div className="modal-backdrop">
          <div aria-labelledby="asset-deletion-dialog-title" aria-modal="true" className="confirmation-dialog" ref={dialogRef} role="dialog">
            <h3 id="asset-deletion-dialog-title">자산 삭제 영향 확인</h3>
            <p>{pendingDeletion.message}</p>
            <dl className="confirmation-summary"><div><dt>대상</dt><dd>{pendingDeletion.item.display_name}</dd></div><div><dt>종류</dt><dd>{assetTypeLabel(pendingDeletion.item.asset_type, pendingDeletion.item.subtype)}</dd></div></dl>
            <div className="button-row dialog-actions">
              <button className="secondary-button" disabled={deleting} onClick={() => closeDeletionDialog(pendingDeletion.item)} type="button">취소</button>
              <button className="danger-button" disabled={deleting} onClick={() => void confirmDeleteSelected()} type="button">{deleting ? "삭제 중" : "삭제"}</button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

async function prepareDeletion(item: WorkspaceAssetDescriptor): Promise<PendingAssetDeletion> {
  if (item.asset_type === "analysis_run") {
    const preflight = await fetchAnalysisRunDeletionPreflight(item.asset_id);
    if (!preflight.deletion_ready) throw new Error(preflight.blockers.join(", "));
    return { item, manifestSha256: preflight.deletion_manifest_sha256, message: `분석 결과와 종속 파일 ${preflight.counts.total_file_count}개를 삭제합니다. 이 작업은 되돌릴 수 없습니다.` };
  }
  if (item.asset_type === "doe_design") {
    const preflight = await fetchDoeDesignDeletionPreflight(item.asset_id);
    return { item, manifestSha256: preflight.deletion_manifest_sha256, message: `설계 ${preflight.counts.version_count}개 버전, run ${preflight.counts.run_count}개, 반응 revision ${preflight.counts.response_revision_count}개, 분석 ${preflight.counts.analysis_count}개를 함께 삭제합니다.` };
  }
  if (item.asset_type === "bayesian_study") {
    const preflight = await fetchBayesianStudyDeletionPreflight(item.asset_id);
    if (!preflight.eligible) throw new Error(preflight.blockers.join(", "));
    return { item, manifestSha256: preflight.deletion_manifest_sha256, message: `Bayesian Study와 trial ${preflight.counts.trial_count}개를 삭제합니다. 이 작업은 되돌릴 수 없습니다.` };
  }
  throw new Error("workspace_asset_delete_unsupported");
}

function assetKey(item: WorkspaceAssetDescriptor): string {
  return `${item.asset_type}:${item.asset_id}`;
}

function detailRowId(item: WorkspaceAssetDescriptor): string {
  return `asset-detail-${item.asset_type}-${item.asset_id}`;
}

function detailButtonId(item: WorkspaceAssetDescriptor): string {
  return `asset-detail-button-${item.asset_type}-${item.asset_id}`;
}

function assetTypeLabel(type: WorkspaceAssetDescriptor["asset_type"], subtype: string): string {
  if (type === "dataset_version") return "데이터셋";
  if (type === "analysis_run") return subtype.includes("predict") ? "예측 결과" : "분석 결과";
  if (type === "regression_model") return "회귀모델";
  if (type === "bayesian_study") return "Bayesian Study";
  if (subtype.includes("latin")) return "LHS 설계";
  if (subtype.includes("response_surface")) return "RSM 설계";
  if (subtype.includes("general")) return "일반 완전요인 설계";
  return "Factorial 설계";
}

function isManagedDeletionType(type: WorkspaceAssetDescriptor["asset_type"]): boolean {
  return type === "analysis_run" || type === "doe_design" || type === "bayesian_study";
}

function isGenericMetadataType(
  type: WorkspaceAssetDescriptor["asset_type"],
): type is "analysis_run" | "doe_design" | "bayesian_study" {
  return type === "analysis_run" || type === "doe_design" || type === "bayesian_study";
}

function WorkspaceAssetMetadataEditor({
  item,
  onSaved,
}: {
  item: WorkspaceAssetDescriptor & {
    asset_type: "analysis_run" | "doe_design" | "bayesian_study";
  };
  onSaved: () => void;
}) {
  const [userLabel, setUserLabel] = useState(item.display_name);
  const [note, setNote] = useState(item.note ?? "");
  const [pinned, setPinned] = useState(item.pinned);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  return (
    <form
      className="asset-inline-metadata-form"
      onSubmit={(event) => {
        event.preventDefault();
        setSaving(true);
        setSaveError(null);
        void updateWorkspaceAssetMetadata(item.asset_type, item.asset_id, {
          user_label: userLabel.trim() || null,
          note: note.trim() || null,
          pinned,
          expected_metadata_updated_at: item.metadata_updated_at,
        })
          .then(onSaved)
          .catch((caught) => {
            setSaveError(
              caught instanceof Error ? caught.message : "workspace_asset_metadata_update_failed",
            );
          })
          .finally(() => setSaving(false));
      }}
    >
      <div className="asset-inline-metadata-grid">
        <label>
          <span>이름</span>
          <input maxLength={120} value={userLabel} onChange={(event) => setUserLabel(event.currentTarget.value)} />
        </label>
        <label>
          <span>메모</span>
          <textarea maxLength={500} rows={2} value={note} onChange={(event) => setNote(event.currentTarget.value)} />
        </label>
        <label className="doe-table-toggle">
          <input checked={pinned} type="checkbox" onChange={(event) => setPinned(event.currentTarget.checked)} />
          <span>목록 위에 고정</span>
        </label>
      </div>
      {saveError ? <div className="error-box">오류 코드: {saveError}</div> : null}
      <button className="secondary-button" disabled={saving} type="submit">
        {saving ? "저장 중" : "저장"}
      </button>
    </form>
  );
}
