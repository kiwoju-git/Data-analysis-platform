import {
  useEffect,
  useRef,
  useState,
  type MouseEvent,
  type ReactNode,
} from "react";

import {
  ActiveDatasetVersionSelector,
  type ActiveDatasetVersionSelectorProps,
} from "./ActiveDatasetVersionSelector";
import type { AppRoute } from "./appRoute";
import samsungBioepisLogo from "./assets/brand/samsung-bioepis-logo.png";
import { SidebarNavigation } from "./SidebarNavigation";
import type {
  SidebarNavigationGroup,
  SidebarNavigationItem,
} from "./sidebarNavigationModel";
import { isPresentationProfile } from "./productProfile";

export interface AppChromeProps {
  canOpenAnalysis: boolean;
  children: ReactNode;
  healthClassName: string;
  healthLabel: string;
  activePage: AppRoute["page"];
  activeDatasetSelectorProps: ActiveDatasetVersionSelectorProps;
  navigationGroups?: SidebarNavigationGroup[];
  pageTitle?: string;
  onOpenAnalysisPage: () => void;
  onOpenDatasetPage: () => void;
  onOpenHelpPage: () => void;
  onOpenGraphsPage: () => void;
  onOpenManagePage: () => void;
  onOpenProjectPage: () => void;
  onOpenReportsPage: () => void;
}

export function AppChrome({
  canOpenAnalysis,
  children,
  healthClassName,
  healthLabel,
  activePage,
  activeDatasetSelectorProps,
  navigationGroups,
  pageTitle,
  onOpenAnalysisPage,
  onOpenDatasetPage,
  onOpenHelpPage,
  onOpenGraphsPage,
  onOpenManagePage,
  onOpenProjectPage,
  onOpenReportsPage,
}: AppChromeProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const groups =
    navigationGroups ??
    fallbackNavigationGroups({
      activePage,
      canOpenAnalysis,
      onOpenAnalysisPage,
      onOpenDatasetPage,
      onOpenHelpPage,
      onOpenGraphsPage,
      onOpenManagePage,
      onOpenProjectPage,
      onOpenReportsPage,
    });

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileMenuOpen(false);
        mobileMenuButtonRef.current?.focus();
        return;
      }
      if (event.key !== "Tab") return;
      const focusableItems = Array.from(
        sidebarRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), [href], [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      ).filter((item) => item.closest("[hidden]") === null);
      if (focusableItems.length === 0) return;
      const first = focusableItems[0];
      const last = focusableItems[focusableItems.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    window.requestAnimationFrame(() => {
      const activeItem = sidebarRef.current?.querySelector<HTMLButtonElement>(
        '[aria-current="page"]',
      );
      const activeGroupControl =
        activeItem?.closest(".sidebar-group")?.querySelector<HTMLButtonElement>(
          ".sidebar-group-control",
        ) ?? null;
      const focusTarget =
        activeItem !== undefined &&
        activeItem !== null &&
        activeItem.closest("[hidden]") === null
          ? activeItem
          : activeGroupControl ??
            sidebarRef.current?.querySelector<HTMLButtonElement>("button");
      focusTarget?.focus();
    });
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mobileMenuOpen]);

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };
  const openProjectHome = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    closeMobileMenu();
    onOpenProjectPage();
  };

  return (
    <div className="app-shell">
      <header className="mobile-shell-header">
        <a
          aria-label="Statistical Twin 홈으로 이동"
          className="mobile-brand-home-link"
          href="/home"
          lang="en"
          onClick={openProjectHome}
        >
          Statistical Twin
        </a>
        <button
          aria-controls="application-sidebar"
          aria-expanded={mobileMenuOpen}
          aria-label="주요 메뉴 열기"
          className="mobile-menu-toggle"
          onClick={() => setMobileMenuOpen((open) => !open)}
          ref={mobileMenuButtonRef}
          type="button"
        >
          <span aria-hidden="true">☰</span>
        </button>
      </header>
      {mobileMenuOpen ? (
        <button
          aria-label="주요 메뉴 닫기"
          className="sidebar-scrim"
          onClick={() => {
            closeMobileMenu();
            mobileMenuButtonRef.current?.focus();
          }}
          type="button"
        />
      ) : null}
      <aside
        className={mobileMenuOpen ? "sidebar is-open" : "sidebar"}
        id="application-sidebar"
        ref={sidebarRef}
      >
        <div className="brand">
          <a
            aria-label="Statistical Twin 홈으로 이동"
            className="brand-home-link"
            href="/home"
            onClick={openProjectHome}
          >
            <img
              alt="Samsung Bioepis"
              className="brand-logo"
              height="199"
              src={samsungBioepisLogo}
              width="499"
            />
            <h1 className="brand-product-title" lang="en">
              Statistical Twin
            </h1>
          </a>
        </div>
        <SidebarNavigation groups={groups} onNavigate={closeMobileMenu} />
      </aside>
      <main className="main">
        <header className="topbar">
          <p className="topbar-title">{pageTitle ?? pageTitleFor(activePage)}</p>
          {isPresentationProfile ? (
            <span className="presentation-profile-badge">발표용 기능 미리보기</span>
          ) : null}
          <span className={healthClassName} aria-live="polite">
            {healthLabel}
          </span>
        </header>
        <div className="active-dataset-region">
          <ActiveDatasetVersionSelector {...activeDatasetSelectorProps} />
        </div>
        {children}
      </main>
    </div>
  );
}

function pageTitleFor(page: AppRoute["page"]): string {
  const labels: Record<AppRoute["page"], string> = {
    analysis: "분석",
    dataset: "데이터셋",
    graphs: "그래프",
    help: "도움말",
    manage: "관리",
    home: "홈",
    reports: "리포트",
  };
  return labels[page];
}

function fallbackNavigationGroups({
  activePage,
  canOpenAnalysis,
  onOpenAnalysisPage,
  onOpenDatasetPage,
  onOpenHelpPage,
  onOpenGraphsPage,
  onOpenManagePage,
  onOpenProjectPage,
  onOpenReportsPage,
}: Omit<
  AppChromeProps,
  | "activeDatasetSelectorProps"
  | "children"
  | "healthClassName"
  | "healthLabel"
  | "navigationGroups"
  | "pageTitle"
>) {
  const definitions: Array<{
    id: AppRoute["page"];
    label: string;
    leaf: string;
    disabled?: boolean;
    onActivate: () => void;
  }> = [
    { id: "home", label: "홈", leaf: "홈", onActivate: onOpenProjectPage },
    { id: "dataset", label: "데이터셋", leaf: "데이터 등록", onActivate: onOpenDatasetPage },
    {
      id: "analysis",
      label: "분석",
      leaf: "탐색적 분석",
      disabled: !canOpenAnalysis,
      onActivate: onOpenAnalysisPage,
    },
    { id: "graphs", label: "그래프", leaf: "그래프 작성", onActivate: onOpenGraphsPage },
    { id: "reports", label: "리포트", leaf: "보고서", onActivate: onOpenReportsPage },
    { id: "manage", label: "관리", leaf: "자산 관리", onActivate: onOpenManagePage },
    { id: "help", label: "도움말", leaf: "질문으로 찾기", onActivate: onOpenHelpPage },
  ];
  return definitions.map(({ disabled, id, label, leaf, onActivate }) => {
    if (id === "home") {
      return {
        active: activePage === id,
        children: [],
        direct: true,
        id,
        label,
        onActivate,
      };
    }
    const item: SidebarNavigationItem = {
      active: activePage === id,
      disabled,
      id: `${id}-default`,
      label: leaf,
      onActivate,
    };
    return {
      active: activePage === id,
      children: [item],
      id,
      label,
    };
  });
}
