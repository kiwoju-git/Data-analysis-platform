import { Component, lazy, Suspense, type ReactNode } from "react";
import { useI18n } from "./i18n/LocaleProvider";

const App = lazy(() => import("./App"));

export function ApplicationContent() {
  return <Suspense fallback={<ApplicationLoading />}><App /></Suspense>;
}

export function ApplicationLoading() {
  const { t } = useI18n();
  return (
    <main className="runtime-gate-page" data-app-startup="loading" aria-busy="true">
      <h1>Statistical Twin</h1>
      <p role="status">{t("startup.loading")}</p>
    </main>
  );
}

export function ApplicationLoadError() {
  const { t } = useI18n();
  return (
    <main className="runtime-gate-page" data-app-startup="failed">
      <section className="runtime-mismatch-panel" role="alert" aria-labelledby="startup-error-title">
        <h1 id="startup-error-title">{t("startup.failed")}</h1>
        <p>{t("startup.recovery")}</p>
        <button className="primary-button" type="button" onClick={() => window.location.reload()}>
          {t("startup.reload")}
        </button>
      </section>
    </main>
  );
}

export class ApplicationErrorBoundary extends Component<
  { children: ReactNode }, { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    return this.state.hasError ? <ApplicationLoadError /> : this.props.children;
  }
}
