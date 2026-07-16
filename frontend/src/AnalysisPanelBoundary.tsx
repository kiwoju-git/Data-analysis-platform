import { Component, Suspense, type ReactNode } from "react";

interface AnalysisPanelBoundaryProps {
  children: ReactNode;
  panelKey: string;
}

interface AnalysisPanelErrorBoundaryProps {
  children: ReactNode;
  resetKey: string;
}

interface AnalysisPanelErrorBoundaryState {
  hasError: boolean;
}

export function AnalysisPanelLoading() {
  return (
    <section
      aria-label="분석 패널 로딩"
      aria-live="polite"
      className="analysis-panel-load-state"
      role="status"
    >
      <strong>분석 화면 불러오는 중</strong>
    </section>
  );
}

export function AnalysisPanelLoadError() {
  return (
    <section aria-label="분석 패널 로드 오류" className="analysis-panel-load-state" role="alert">
      <strong>분석 화면을 불러오지 못했습니다.</strong>
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

export class AnalysisPanelErrorBoundary extends Component<
  AnalysisPanelErrorBoundaryProps,
  AnalysisPanelErrorBoundaryState
> {
  state: AnalysisPanelErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): AnalysisPanelErrorBoundaryState {
    return { hasError: true };
  }

  componentDidUpdate(previousProps: AnalysisPanelErrorBoundaryProps) {
    if (previousProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  render() {
    return this.state.hasError ? <AnalysisPanelLoadError /> : this.props.children;
  }
}

export function AnalysisPanelBoundary({ children, panelKey }: AnalysisPanelBoundaryProps) {
  return (
    <AnalysisPanelErrorBoundary resetKey={panelKey}>
      <Suspense fallback={<AnalysisPanelLoading />}>{children}</Suspense>
    </AnalysisPanelErrorBoundary>
  );
}
