import type { ReactNode } from "react";

import type { DatasetVersionResponse } from "./api";
import { shortHash } from "./datasetDisplay";

export interface AppChromeProps {
  canOpenAnalysis: boolean;
  children: ReactNode;
  healthClassName: string;
  healthLabel: string;
  isAnalysisPage: boolean;
  version: DatasetVersionResponse | null;
  onOpenAnalysisPage: () => void;
  onOpenDatasetPage: () => void;
}

export function AppChrome({
  canOpenAnalysis,
  children,
  healthClassName,
  healthLabel,
  isAnalysisPage,
  version,
  onOpenAnalysisPage,
  onOpenDatasetPage,
}: AppChromeProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="주요 단계">
        <div className="brand">
          <h1 className="brand-title">DataLab Studio</h1>
          <p className="brand-subtitle">로컬 분석 작업대</p>
        </div>
        <ol className="nav-list">
          <li className="nav-item">프로젝트</li>
          <li className={isAnalysisPage ? "nav-item" : "nav-item nav-item-active"}>
            <button
              aria-current={isAnalysisPage ? undefined : "page"}
              className="nav-button"
              onClick={onOpenDatasetPage}
              type="button"
            >
              데이터셋
            </button>
          </li>
          <li className={isAnalysisPage ? "nav-item nav-item-active" : "nav-item"}>
            <button
              aria-current={isAnalysisPage ? "page" : undefined}
              className="nav-button"
              disabled={!canOpenAnalysis}
              onClick={onOpenAnalysisPage}
              type="button"
            >
              분석
            </button>
          </li>
          <li className="nav-item">리포트</li>
        </ol>
      </aside>
      <main className="main">
        <header className="topbar">
          <p className="topbar-title">Gate A 기반 구성</p>
          <span className={healthClassName} aria-live="polite">
            {healthLabel}
          </span>
        </header>
        {version !== null ? <DatasetContextBar version={version} /> : null}
        {children}
      </main>
    </div>
  );
}

function DatasetContextBar({ version }: { version: DatasetVersionResponse }) {
  return (
    <div className="context-bar" aria-label="데이터셋 컨텍스트">
      <span>Dataset v{version.version_number}</span>
      <span>{version.row_count.toLocaleString()}행</span>
      <span>{version.column_count.toLocaleString()}컬럼</span>
      <span className="hash-text">schema {shortHash(version.schema_hash)}</span>
      <span className="hash-text">source {shortHash(version.source_sha256)}</span>
    </div>
  );
}
