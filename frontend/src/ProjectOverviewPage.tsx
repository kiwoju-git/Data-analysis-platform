import type { DatasetVersionResponse } from "./api";
import { formatLocalDateTime } from "./dateFormat";
import { useProjectOverviewState } from "./useProjectOverviewState";

export interface ProjectOverviewPageProps {
  currentDatasetVersion: DatasetVersionResponse | null;
  onOpenAnalysis: () => void;
  onOpenDatasetPage: () => void;
  onOpenManage: () => void;
  onOpenReports: (analysisId?: string) => void;
}

export function ProjectOverviewPage({
  currentDatasetVersion,
  onOpenAnalysis,
  onOpenDatasetPage,
  onOpenManage,
  onOpenReports,
}: ProjectOverviewPageProps) {
  const state = useProjectOverviewState();
  const currentCatalogItem = state.recentDatasets?.versions.find(
    (item) => item.version_id === currentDatasetVersion?.version_id,
  );

  return (
    <section className="project-overview-page" aria-labelledby="project-overview-title">
      <div className="panel-heading">
        <div>
          <h2 id="project-overview-title">프로젝트</h2>
          <p>현재 DataLab Studio 설치의 단일 로컬 프로젝트와 저장 자산을 요약합니다.</p>
          <p className="field-note">
            현재 버전은 하나의 로컬 작업공간을 프로젝트로 관리합니다.
          </p>
        </div>
        <button className="secondary-button" onClick={state.onRetry} type="button">
          새로고침
        </button>
      </div>
      {state.error !== null ? (
        <div className="error-state" role="alert">
          <p>프로젝트 정보를 불러오지 못했습니다: {state.error}</p>
          <button onClick={state.onRetry} type="button">다시 시도</button>
        </div>
      ) : null}

      <section className="project-overview-band" aria-labelledby="project-current-dataset">
        <h3 id="project-current-dataset">현재 분석 데이터셋</h3>
        {currentDatasetVersion === null ? (
          <div className="empty-state">
            <p>현재 선택된 데이터셋이 없습니다.</p>
            <button className="primary-button" onClick={onOpenDatasetPage} type="button">
              새 데이터 등록
            </button>
          </div>
        ) : (
          <>
            <strong>
              {currentCatalogItem?.user_label ??
                currentCatalogItem?.original_filename ??
                `Dataset (${currentDatasetVersion.version_id.slice(0, 8)})`}
            </strong>
            {currentCatalogItem?.original_filename ? (
              <p>{currentCatalogItem.original_filename}</p>
            ) : null}
            <div className="metadata-grid">
              <span>{currentDatasetVersion.row_count.toLocaleString()}행</span>
              <span>{currentDatasetVersion.column_count.toLocaleString()}열</span>
              <span>생성 {formatLocalDateTime(currentDatasetVersion.created_at)}</span>
              <span>v{currentDatasetVersion.version_number}</span>
            </div>
            <div className="button-row">
              <button className="primary-button" onClick={onOpenAnalysis} type="button">
                분석 열기
              </button>
              <button className="secondary-button" onClick={onOpenManage} type="button">
                데이터셋 관리
              </button>
            </div>
          </>
        )}
      </section>

      <section className="project-overview-band" aria-labelledby="project-datasets">
        <div className="panel-heading compact-heading">
          <h3 id="project-datasets">데이터셋 현황</h3>
          <div className="button-row">
            <button className="secondary-button" onClick={onOpenDatasetPage} type="button">
              새 데이터 등록
            </button>
            <button className="secondary-button" onClick={onOpenManage} type="button">
              보관·삭제 관리
            </button>
          </div>
        </div>
        <div className="summary-grid">
          <span>표시 중 {state.summary?.visible_dataset_version_count ?? 0}개</span>
          <span>보관됨 {state.summary?.archived_dataset_version_count ?? 0}개</span>
        </div>
        <ul className="project-recent-list">
          {state.recentDatasets?.versions.map((item) => (
            <li key={item.version_id}>
              <strong>{item.user_label ?? item.original_filename}</strong>
              <span>{item.row_count.toLocaleString()}행 · {item.column_count}열</span>
              <span>{formatLocalDateTime(item.created_at)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="project-overview-band" aria-labelledby="project-analyses">
        <div className="panel-heading compact-heading">
          <h3 id="project-analyses">최근 분석</h3>
          <button className="secondary-button" onClick={() => onOpenReports()} type="button">
            전체 리포트
          </button>
        </div>
        <ul className="project-recent-list">
          {state.recentAnalyses?.runs.map((run) => (
            <li key={run.analysis_id}>
              <strong>{run.method_id}</strong>
              <span>{run.stale ? "stale" : "current"}</span>
              <span>{formatLocalDateTime(run.completed_at ?? run.updated_at)}</span>
              <button
                className="secondary-button"
                onClick={() => onOpenReports(run.analysis_id)}
                type="button"
              >
                리포트에서 열기
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="project-overview-band" aria-labelledby="project-assets">
        <h3 id="project-assets">모델 및 리포트</h3>
        <div className="summary-grid">
          <span>회귀모델 {state.summary?.regression_model_count ?? 0}개</span>
          <span>저장 분석 {state.summary?.stored_analysis_count ?? 0}개</span>
          <span>내보내기·리포트 {state.summary?.export_report_count ?? 0}개</span>
        </div>
        <ul className="project-recent-list">
          {state.recentModels?.models.map((model) => (
            <li key={model.model_id}>
              <strong>
                {model.user_label ??
                  model.response?.display_name ??
                  `Regression model (${model.model_id.slice(0, 8)})`}
              </strong>
              <span>{model.availability}</span>
              <span>{formatLocalDateTime(model.created_at)}</span>
            </li>
          ))}
        </ul>
        <div className="button-row">
          <button className="secondary-button" onClick={onOpenManage} type="button">
            모델 관리
          </button>
          <button className="secondary-button" onClick={() => onOpenReports()} type="button">
            리포트 관리
          </button>
        </div>
      </section>
    </section>
  );
}
