import type { ReactNode } from "react";

import type {
  AnalysisMethodListResponse,
  DatasetVersionCatalogItem,
  DatasetVersionResponse,
} from "./api";
import {
  summarizeDatasetColumnComposition,
  type DatasetColumnCompositionItem,
} from "./datasetColumnComposition";
import { analysisMethodDisplayLabel } from "./analysisNavigation";
import { formatLocalDateTime } from "./dateFormat";
import {
  useProjectOverviewState,
  type ProjectResourceState,
} from "./useProjectOverviewState";
import { isPresentationProfile } from "./productProfile";

export interface ProjectOverviewPageProps {
  activeDatasetCatalogItem?: DatasetVersionCatalogItem | null;
  analysisCatalog?: AnalysisMethodListResponse | null;
  currentDatasetVersion: DatasetVersionResponse | null;
  onOpenAnalysis: () => void;
  onOpenDatasetPage: () => void;
  onOpenGraphs: () => void;
  onOpenHelp: () => void;
  onOpenManage: () => void;
  onOpenReports: (analysisId?: string) => void;
  workspaceAssetRevision?: number;
}

export function ProjectOverviewPage({
  activeDatasetCatalogItem = null,
  analysisCatalog = null,
  currentDatasetVersion,
  onOpenAnalysis,
  onOpenDatasetPage,
  onOpenGraphs,
  onOpenHelp,
  onOpenManage,
  onOpenReports,
  workspaceAssetRevision = 0,
}: ProjectOverviewPageProps) {
  const state = useProjectOverviewState(workspaceAssetRevision);
  const composition =
    currentDatasetVersion === null
      ? []
      : summarizeDatasetColumnComposition(currentDatasetVersion.columns);

  return (
    <section className="project-overview-page" aria-labelledby="project-overview-title">
      <div className="panel-heading project-overview-heading">
        <div>
          <h2 id="project-overview-title">Statistical Twin 대시보드</h2>
          <p>로컬 작업공간의 최근 자산을 확인하고 다음 작업을 시작합니다.</p>
        </div>
        <button className="secondary-button" onClick={state.onRetry} type="button">
          새로고침
        </button>
      </div>

      {isPresentationProfile ? (
        <p className="presentation-profile-scope">
          공개 시연 범위: 홈 · 데이터셋 · 탐색적 분석 · 가설 검정
        </p>
      ) : null}

      <div className="home-quick-grid" aria-label="빠른 실행">
        <HomeQuickCard
          accent="dataset"
          action={currentDatasetVersion === null ? "데이터 등록" : "데이터 보기"}
          detail={currentDatasetVersion === null ? "분석을 시작하려면 데이터를 등록하세요." : `${currentDatasetVersion.row_count.toLocaleString()}행 · ${currentDatasetVersion.column_count.toLocaleString()}열`}
          title="데이터셋"
          onActivate={onOpenDatasetPage}
        />
        <HomeQuickCard
          accent="analysis"
          action="분석 시작"
          detail={state.summary.data === null ? "통계 method 선택" : `저장 분석 ${state.summary.data.stored_analysis_count.toLocaleString()}건`}
          title="분석"
          onActivate={onOpenAnalysis}
        />
        {!isPresentationProfile ? (
          <>
            <HomeQuickCard accent="graphs" action="그래프 작성" detail="변수 선택형 그래프" title="그래프" onActivate={onOpenGraphs} />
            <HomeQuickCard
              accent="reports"
              action="리포트 열기"
              detail={state.summary.data === null ? "결과 보기와 내보내기" : `리포트·내보내기 ${state.summary.data.export_report_count.toLocaleString()}건`}
              title="리포트"
              onActivate={() => onOpenReports()}
            />
            <HomeQuickCard
              accent="manage"
              action="자산 관리"
              detail={state.summary.data === null ? "저장 자산 검색과 관리" : `데이터 ${state.summary.data.visible_dataset_version_count + state.summary.data.archived_dataset_version_count} · 모델 ${state.summary.data.regression_model_count}`}
              title="관리"
              onActivate={onOpenManage}
            />
            <HomeQuickCard accent="help" action="도움말 열기" detail="Method 찾기와 튜토리얼" title="도움말" onActivate={onOpenHelp} />
          </>
        ) : null}
      </div>

      {!isPresentationProfile ? (
      <div className="project-dashboard-grid">
        <article
          className="project-dashboard-card"
          aria-labelledby="project-current-dataset"
        >
          <div className="project-dashboard-card-header">
            <h3 id="project-current-dataset">현재 분석 데이터셋</h3>
          </div>
          {currentDatasetVersion === null ? (
            <div className="empty-state">
              <p>현재 선택된 데이터셋이 없습니다.</p>
              <button className="primary-button" onClick={onOpenDatasetPage} type="button">
                새 데이터 등록
              </button>
            </div>
          ) : (
            <>
              <div className="project-dashboard-primary">
                <strong>
                  {activeDatasetCatalogItem?.user_label ??
                    activeDatasetCatalogItem?.original_filename ??
                    `데이터셋 v${currentDatasetVersion.version_number}`}
                </strong>
                {activeDatasetCatalogItem?.user_label !== null &&
                activeDatasetCatalogItem?.user_label !== undefined &&
                activeDatasetCatalogItem.original_filename !==
                  activeDatasetCatalogItem.user_label ? (
                  <span>{activeDatasetCatalogItem.original_filename}</span>
                ) : null}
              </div>
              <dl className="project-dashboard-metadata">
                <div>
                  <dt>버전</dt>
                  <dd>v{currentDatasetVersion.version_number}</dd>
                </div>
                <div>
                  <dt>행</dt>
                  <dd>{currentDatasetVersion.row_count.toLocaleString()}</dd>
                </div>
                <div>
                  <dt>열</dt>
                  <dd>{currentDatasetVersion.column_count.toLocaleString()}</dd>
                </div>
                <div>
                  <dt>생성</dt>
                  <dd>{formatLocalDateTime(currentDatasetVersion.created_at)}</dd>
                </div>
              </dl>
              {currentDatasetVersion.parent_version_id ? (
                <p className="project-lineage-note">
                  v{Math.max(1, currentDatasetVersion.version_number - 1)}에서 셀{" "}
                  {currentDatasetVersion.lineage_affected_cell_count ?? 1}건을 수정해
                  생성됨
                </p>
              ) : null}
              <DatasetColumnComposition
                items={composition}
                total={currentDatasetVersion.column_count}
              />
              <div className="button-row project-dashboard-actions">
                <button className="primary-button" onClick={onOpenAnalysis} type="button">
                  분석 열기
                </button>
                <button className="secondary-button" onClick={onOpenManage} type="button">
                  데이터셋 관리
                </button>
              </div>
            </>
          )}
        </article>

        <article className="project-dashboard-card" aria-labelledby="project-datasets">
          <div className="project-dashboard-card-header">
            <h3 id="project-datasets">데이터셋 현황</h3>
          </div>
          <ProjectResource
            resource={state.summary}
            retry={state.onRetry}
            loadingLabel="데이터셋 현황을 불러오는 중"
          >
            {(summary) => (
              <div className="project-dashboard-kpis">
                <div>
                  <span>표시 중</span>
                  <strong>{summary.visible_dataset_version_count.toLocaleString()}</strong>
                </div>
                <div>
                  <span>보관됨</span>
                  <strong>{summary.archived_dataset_version_count.toLocaleString()}</strong>
                </div>
              </div>
            )}
          </ProjectResource>
          <ProjectResource
            resource={state.recentDatasets}
            retry={state.onRetry}
            loadingLabel="최근 데이터셋을 불러오는 중"
          >
            {(catalog) =>
              catalog.versions.length === 0 ? (
                <p className="project-dashboard-empty">등록된 데이터셋이 없습니다.</p>
              ) : (
                <ul className="project-recent-list">
                  {catalog.versions.slice(0, 3).map((item) => (
                    <li key={item.version_id}>
                      <strong>{item.user_label ?? item.original_filename}</strong>
                      <span>
                        {item.row_count.toLocaleString()}행 ·{" "}
                        {item.column_count.toLocaleString()}열
                      </span>
                      <span>{formatLocalDateTime(item.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )
            }
          </ProjectResource>
          <div className="button-row project-dashboard-actions">
            <button className="secondary-button" onClick={onOpenDatasetPage} type="button">
              새 데이터 등록
            </button>
            <button className="secondary-button" onClick={onOpenManage} type="button">
              보관·삭제 관리
            </button>
          </div>
        </article>

        <article className="project-dashboard-card" aria-labelledby="project-analyses">
          <div className="project-dashboard-card-header">
            <h3 id="project-analyses">최근 분석</h3>
            <ProjectResource
              resource={state.summary}
              retry={state.onRetry}
              loadingLabel="저장 분석 수를 불러오는 중"
              compact
            >
              {(summary) => (
                <span className="project-dashboard-count">
                  저장 {summary.stored_analysis_count.toLocaleString()}
                </span>
              )}
            </ProjectResource>
          </div>
          <ProjectResource
            resource={state.recentAnalyses}
            retry={state.onRetry}
            loadingLabel="최근 분석을 불러오는 중"
          >
            {(catalog) =>
              catalog.runs.length === 0 ? (
                <p className="project-dashboard-empty">저장된 분석 결과가 없습니다.</p>
              ) : (
                <ul className="project-recent-list project-analysis-list">
                  {catalog.runs.slice(0, 3).map((run) => (
                    <li key={run.analysis_id}>
                      <div>
                        <strong>
                          {analysisMethodDisplayLabel(
                            run.method_id,
                            analysisCatalog,
                            "저장 분석",
                          )}
                        </strong>
                        <span title={run.method_id}>
                          {run.stale ? "이전 스키마 기준" : "현재 데이터 기준"}
                        </span>
                      </div>
                      <span>{formatLocalDateTime(run.completed_at ?? run.updated_at)}</span>
                      <button
                        className="secondary-button compact-button"
                        onClick={() => onOpenReports(run.analysis_id)}
                        type="button"
                      >
                        리포트 열기
                      </button>
                    </li>
                  ))}
                </ul>
              )
            }
          </ProjectResource>
          <div className="button-row project-dashboard-actions">
            <button className="secondary-button" onClick={() => onOpenReports()} type="button">
              전체 리포트
            </button>
          </div>
        </article>

        <article className="project-dashboard-card" aria-labelledby="project-assets">
          <div className="project-dashboard-card-header">
            <h3 id="project-assets">모델 및 리포트</h3>
          </div>
          <ProjectResource
            resource={state.summary}
            retry={state.onRetry}
            loadingLabel="모델과 리포트 수를 불러오는 중"
          >
            {(summary) => (
              <div className="project-dashboard-kpis">
                <div>
                  <span>회귀모델</span>
                  <strong>{summary.regression_model_count.toLocaleString()}</strong>
                </div>
                <div>
                  <span>리포트·내보내기</span>
                  <strong>{summary.export_report_count.toLocaleString()}</strong>
                </div>
              </div>
            )}
          </ProjectResource>
          <ProjectResource
            resource={state.recentModels}
            retry={state.onRetry}
            loadingLabel="최근 모델을 불러오는 중"
          >
            {(catalog) =>
              catalog.models.length === 0 ? (
                <p className="project-dashboard-empty">저장된 회귀모델이 없습니다.</p>
              ) : (
                <ul className="project-recent-list">
                  {catalog.models.slice(0, 3).map((model) => (
                    <li key={model.model_id}>
                      <strong>
                        {model.user_label ??
                          model.response?.display_name ??
                          "회귀모델"}
                      </strong>
                      <span>{modelAvailabilityLabel(model.availability)}</span>
                      <span>{formatLocalDateTime(model.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )
            }
          </ProjectResource>
          <div className="button-row project-dashboard-actions">
            <button className="secondary-button" onClick={onOpenManage} type="button">
              모델 관리
            </button>
            <button className="secondary-button" onClick={() => onOpenReports()} type="button">
              리포트 관리
            </button>
          </div>
        </article>
      </div>
      ) : null}
    </section>
  );
}

function HomeQuickCard({
  accent,
  action,
  detail,
  onActivate,
  title,
}: {
  accent: "dataset" | "analysis" | "graphs" | "reports" | "manage" | "help";
  action: string;
  detail: string;
  onActivate: () => void;
  title: string;
}) {
  return (
    <button
      aria-label={`${title}: ${action}`}
      className={`home-quick-card is-${accent}`}
      onClick={onActivate}
      type="button"
    >
      <strong>{title}</strong>
      <span>{detail}</span>
      <small>{action}</small>
    </button>
  );
}

function ProjectResource<T>({
  children,
  compact = false,
  loadingLabel,
  resource,
  retry,
}: {
  children: (data: T) => ReactNode;
  compact?: boolean;
  loadingLabel: string;
  resource: ProjectResourceState<T>;
  retry: () => void;
}) {
  if (resource.isLoading) {
    return (
      <span className={compact ? "project-card-status is-compact" : "project-card-status"} role="status">
        {loadingLabel}
      </span>
    );
  }
  if (resource.error !== null) {
    return (
      <div className={compact ? "project-card-error is-compact" : "project-card-error"} role="alert">
        <span>정보를 불러오지 못했습니다.</span>
        <button className="secondary-button compact-button" onClick={retry} type="button">
          다시 시도
        </button>
      </div>
    );
  }
  return resource.data === null ? null : children(resource.data);
}

function DatasetColumnComposition({
  items,
  total,
}: {
  items: DatasetColumnCompositionItem[];
  total: number;
}) {
  const visibleItems = items.filter((item) => item.count > 0);
  const description =
    visibleItems.length === 0
      ? "변수 구성 정보 없음"
      : visibleItems.map((item) => `${item.label} ${item.count}개`).join(", ");
  return (
    <section className="dataset-column-composition" aria-labelledby="dataset-composition-title">
      <h4 id="dataset-composition-title">변수 구성</h4>
      <div
        className="dataset-column-composition-bar"
        role="img"
        aria-label={description}
      >
        {visibleItems.map((item) => (
          <span
            className={`dataset-column-composition-segment is-${item.kind}`}
            key={item.kind}
            style={{ width: total > 0 ? `${(item.count / total) * 100}%` : "0%" }}
          />
        ))}
      </div>
      <ul className="dataset-column-composition-legend">
        {visibleItems.map((item) => (
          <li key={item.kind}>
            <span
              className={`dataset-column-composition-key is-${item.kind}`}
              aria-hidden="true"
            />
            {item.label} <strong>{item.count}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}

function modelAvailabilityLabel(
  availability: "available" | "source_stale" | "integrity_error",
): string {
  const labels = {
    available: "사용 가능",
    source_stale: "원본 변경",
    integrity_error: "무결성 확인 필요",
  } as const;
  return labels[availability];
}
