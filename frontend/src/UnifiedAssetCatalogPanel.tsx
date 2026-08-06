import { useEffect, useMemo, useState } from "react";

import {
  deleteBayesianStudy,
  deleteDoeDesign,
  deleteStoredAnalysisRun,
  fetchAnalysisRunDeletionPreflight,
  fetchBayesianStudyDeletionPreflight,
  fetchDoeDesignDeletionPreflight,
  fetchWorkspaceAssets,
  type WorkspaceAssetCatalogResponse,
  type WorkspaceAssetCategory,
  type WorkspaceAssetDescriptor,
  type WorkspaceAssetSort,
} from "./api";
import { pushAppLocation } from "./browserNavigation";
import { formatLocalDateTime } from "./dateFormat";

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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

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
          setSelectedId((selected) =>
            response.items.some((item) => item.asset_id === selected)
              ? selected
              : (response.items[0]?.asset_id ?? null),
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
    () => catalog?.items.find((item) => item.asset_id === selectedId) ?? null,
    [catalog, selectedId],
  );

  async function deleteSelected() {
    if (selected === null || !isManagedDeletionType(selected.asset_type)) return;
    setDeleting(true);
    setError(null);
    try {
      const message = await preflightMessage(selected);
      if (message === null || !window.confirm(message)) return;
      if (selected.asset_type === "analysis_run") {
        const preflight = await fetchAnalysisRunDeletionPreflight(selected.asset_id);
        if (!preflight.deletion_ready) throw new Error(preflight.blockers.join(", "));
        await deleteStoredAnalysisRun(selected.asset_id, {
          confirmation_analysis_id: selected.asset_id,
          expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
        });
      } else if (selected.asset_type === "doe_design") {
        const preflight = await fetchDoeDesignDeletionPreflight(selected.asset_id);
        await deleteDoeDesign(selected.asset_id, preflight.deletion_manifest_sha256);
      } else if (selected.asset_type === "bayesian_study") {
        const preflight = await fetchBayesianStudyDeletionPreflight(selected.asset_id);
        if (!preflight.eligible) throw new Error(preflight.blockers.join(", "));
        await deleteBayesianStudy(selected.asset_id, {
          confirmation_study_id: selected.asset_id,
          expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
        });
      }
      setSelectedId(null);
      setRefresh((value) => value + 1);
      onMutation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "workspace_asset_delete_failed");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className="unified-asset-catalog" aria-label="저장 자산 목록">
      <div className="asset-catalog-toolbar">
        <label>
          <span>검색</span>
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.currentTarget.value)}
            placeholder="이름, 방법 또는 주요 정보"
          />
        </label>
        <label>
          <span>상태</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.currentTarget.value)}>
            <option value="">전체 상태</option>
            <option value="available">사용 가능</option>
            <option value="succeeded">완료</option>
            <option value="active">진행 중</option>
            <option value="designed">설계됨</option>
            <option value="stale">Stale</option>
            <option value="archived">보관됨</option>
          </select>
        </label>
        <label>
          <span>정렬</span>
          <select value={sort} onChange={(event) => setSort(event.currentTarget.value as WorkspaceAssetSort)}>
            <option value="updated_desc">최근 수정</option>
            <option value="created_desc">최근 생성</option>
            <option value="name_asc">이름</option>
          </select>
        </label>
        <label className="checkbox-field asset-catalog-pinned-filter">
          <input checked={pinnedOnly} type="checkbox" onChange={(event) => setPinnedOnly(event.currentTarget.checked)} />
          <span>고정만 보기</span>
        </label>
        <button className="secondary-button" onClick={() => setRefresh((value) => value + 1)} type="button">새로고침</button>
      </div>
      {loading ? <p role="status">자산 목록 확인 중</p> : null}
      {error !== null ? <div className="error-box">오류 코드: {error}</div> : null}
      <div className="table-wrap asset-catalog-table-wrap">
        <table className="result-table asset-catalog-table">
          <colgroup><col className="asset-name-column" /><col className="asset-type-column" /><col /><col className="asset-status-column" /><col className="asset-date-column" /><col className="asset-action-column" /></colgroup>
          <thead><tr><th>이름</th><th>종류</th><th>주요 정보</th><th>상태</th><th>수정</th><th>작업</th></tr></thead>
          <tbody>
            {catalog?.items.map((item) => (
              <tr className={selectedId === item.asset_id ? "asset-row-selected" : ""} key={`${item.asset_type}-${item.asset_id}`}>
                <td><strong>{item.display_name}</strong>{item.pinned ? <span className="asset-pinned-label">고정</span> : null}</td>
                <td>{assetTypeLabel(item.asset_type, item.subtype)}</td>
                <td>{item.secondary_text}</td>
                <td>{item.status}</td>
                <td>{formatLocalDateTime(item.updated_at)}</td>
                <td><button className="secondary-button compact-button" onClick={() => setSelectedId(item.asset_id)} type="button">상세</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {catalog?.items.length === 0 ? <div className="empty-state">조건에 맞는 저장 자산이 없습니다.</div> : null}
      {selected !== null ? (
        <section className="asset-catalog-detail" aria-labelledby="asset-detail-title">
          <div className="panel-heading compact-heading"><div><h3 id="asset-detail-title">{selected.display_name}</h3><p>{assetTypeLabel(selected.asset_type, selected.subtype)} · {selected.secondary_text}</p></div><span className="status-pill">{selected.status}</span></div>
          <dl className="asset-detail-grid"><div><dt>생성</dt><dd>{formatLocalDateTime(selected.created_at)}</dd></div><div><dt>종속 자산</dt><dd>{selected.dependency_count.toLocaleString()}개</dd></div><div><dt>Method</dt><dd>{selected.method_id ?? "-"}</dd></div><div><dt>메모</dt><dd>{selected.note ?? "-"}</dd></div></dl>
          <div className="button-row asset-detail-actions">
            <button className="primary-button" onClick={() => pushAppLocation(selected.open_target.path)} type="button">{selected.open_target.label}</button>
            {isManagedDeletionType(selected.asset_type) ? <button className="danger-button" disabled={deleting} onClick={() => void deleteSelected()} type="button">{deleting ? "확인 중" : "삭제 영향 확인"}</button> : null}
          </div>
          {selected.asset_type === "dataset_version" || selected.asset_type === "regression_model" ? <p className="compact-note">이름, 메모, 고정과 파일 정리 작업은 해당 자산 종류 탭의 선택 상세에서 변경합니다.</p> : null}
          <details><summary>기술 정보</summary><dl className="asset-detail-grid"><div><dt>Asset ID</dt><dd className="technical-value">{selected.asset_id}</dd></div><div><dt>Subtype</dt><dd>{selected.subtype}</dd></div></dl></details>
        </section>
      ) : null}
    </section>
  );
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

async function preflightMessage(item: WorkspaceAssetDescriptor): Promise<string | null> {
  if (item.asset_type === "analysis_run") {
    const preflight = await fetchAnalysisRunDeletionPreflight(item.asset_id);
    if (!preflight.deletion_ready) throw new Error(preflight.blockers.join(", "));
    return `분석 결과와 종속 파일 ${preflight.counts.total_file_count}개를 삭제합니다. 계속하시겠습니까?`;
  }
  if (item.asset_type === "doe_design") {
    const preflight = await fetchDoeDesignDeletionPreflight(item.asset_id);
    return `설계 ${preflight.counts.version_count}개 버전, run ${preflight.counts.run_count}개, 반응 revision ${preflight.counts.response_revision_count}개, 분석 ${preflight.counts.analysis_count}개를 함께 삭제합니다. 계속하시겠습니까?`;
  }
  if (item.asset_type === "bayesian_study") {
    const preflight = await fetchBayesianStudyDeletionPreflight(item.asset_id);
    if (!preflight.eligible) throw new Error(preflight.blockers.join(", "));
    return `Bayesian Study와 trial ${preflight.counts.trial_count}개를 삭제합니다. 계속하시겠습니까?`;
  }
  return null;
}
