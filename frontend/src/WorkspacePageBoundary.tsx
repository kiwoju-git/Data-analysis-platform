import { Component, Suspense, type ReactNode } from "react";

interface WorkspacePageBoundaryProps {
  children: ReactNode;
  pageKey: string;
}

interface WorkspacePageErrorBoundaryProps {
  children: ReactNode;
  resetKey: string;
}

interface WorkspacePageErrorBoundaryState {
  hasError: boolean;
}

export function WorkspacePageLoading() {
  return (
    <section
      aria-label="페이지 로딩"
      aria-live="polite"
      className="analysis-panel-load-state"
      role="status"
    >
      <strong>페이지 불러오는 중</strong>
    </section>
  );
}

export function WorkspacePageLoadError() {
  return (
    <section aria-label="페이지 로드 오류" className="analysis-panel-load-state" role="alert">
      <strong>페이지를 불러오지 못했습니다.</strong>
      <button
        className="secondary-button"
        type="button"
        onClick={() => {
          if (typeof window !== "undefined") window.location.reload();
        }}
      >
        화면 다시 불러오기
      </button>
    </section>
  );
}

export class WorkspacePageErrorBoundary extends Component<
  WorkspacePageErrorBoundaryProps,
  WorkspacePageErrorBoundaryState
> {
  state: WorkspacePageErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): WorkspacePageErrorBoundaryState {
    return { hasError: true };
  }

  componentDidUpdate(previousProps: WorkspacePageErrorBoundaryProps) {
    if (previousProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  render() {
    return this.state.hasError ? <WorkspacePageLoadError /> : this.props.children;
  }
}

export function WorkspacePageBoundary({ children, pageKey }: WorkspacePageBoundaryProps) {
  return (
    <WorkspacePageErrorBoundary resetKey={pageKey}>
      <Suspense fallback={<WorkspacePageLoading />}>{children}</Suspense>
    </WorkspacePageErrorBoundary>
  );
}
