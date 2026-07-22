import type { ReactNode } from "react";

import {
  ActiveDatasetVersionSelector,
  type ActiveDatasetVersionSelectorProps,
} from "./ActiveDatasetVersionSelector";
import type { AppRoute } from "./appRoute";

export interface AppChromeProps {
  canOpenAnalysis: boolean;
  children: ReactNode;
  healthClassName: string;
  healthLabel: string;
  activePage: AppRoute["page"];
  activeDatasetSelectorProps: ActiveDatasetVersionSelectorProps;
  onOpenAnalysisPage: () => void;
  onOpenDatasetPage: () => void;
  onOpenHelpPage: () => void;
  onOpenManagePage: () => void;
  onOpenReportsPage: () => void;
}

export function AppChrome({
  canOpenAnalysis,
  children,
  healthClassName,
  healthLabel,
  activePage,
  activeDatasetSelectorProps,
  onOpenAnalysisPage,
  onOpenDatasetPage,
  onOpenHelpPage,
  onOpenManagePage,
  onOpenReportsPage,
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
          <li className={activePage === "dataset" ? "nav-item nav-item-active" : "nav-item"}>
            <button
              aria-current={activePage === "dataset" ? "page" : undefined}
              className="nav-button"
              onClick={onOpenDatasetPage}
              type="button"
            >
              데이터셋
            </button>
          </li>
          <li className={activePage === "analysis" ? "nav-item nav-item-active" : "nav-item"}>
            <button
              aria-current={activePage === "analysis" ? "page" : undefined}
              className="nav-button"
              disabled={!canOpenAnalysis}
              onClick={onOpenAnalysisPage}
              type="button"
            >
              분석
            </button>
          </li>
          <li className={activePage === "reports" ? "nav-item nav-item-active" : "nav-item"}>
            <button
              aria-current={activePage === "reports" ? "page" : undefined}
              className="nav-button"
              onClick={onOpenReportsPage}
              type="button"
            >
              리포트
            </button>
          </li>
          <li className={activePage === "manage" ? "nav-item nav-item-active" : "nav-item"}>
            <button
              aria-current={activePage === "manage" ? "page" : undefined}
              className="nav-button"
              onClick={onOpenManagePage}
              type="button"
            >
              관리
            </button>
          </li>
          <li className={activePage === "help" ? "nav-item nav-item-active" : "nav-item"}>
            <button
              aria-current={activePage === "help" ? "page" : undefined}
              className="nav-button"
              onClick={onOpenHelpPage}
              type="button"
            >
              도움말
            </button>
          </li>
        </ol>
      </aside>
      <main className="main">
        <header className="topbar">
          <p className="topbar-title">Gate A 기반 구성</p>
          <span className={healthClassName} aria-live="polite">
            {healthLabel}
          </span>
        </header>
        <ActiveDatasetVersionSelector {...activeDatasetSelectorProps} />
        {children}
      </main>
    </div>
  );
}
