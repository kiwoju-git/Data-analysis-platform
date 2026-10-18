import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ApplicationErrorBoundary, ApplicationLoadError, ApplicationLoading } from "./ApplicationBoundary";
import { setCurrentLocale } from "./i18n/store";

describe("application startup feedback", () => {
  it("shows localized recovery without a raw exception", () => {
    for (const locale of ["en", "ko"] as const) {
      setCurrentLocale(locale);
      const html = renderToStaticMarkup(<ApplicationLoadError />);
      expect(html).toContain('role="alert"');
      expect(html).toContain('data-app-startup="failed"');
      expect(html).toContain(locale === "en" ? "Reload" : "다시 불러오기");
      expect(html).not.toContain("stack");
    }
    setCurrentLocale("en");
  });

  it("distinguishes loading from compatibility-ready", () => {
    const html = renderToStaticMarkup(<ApplicationLoading />);
    expect(html).toContain('aria-busy="true"');
    expect(html).not.toContain('data-runtime-state="compatible"');
    expect(ApplicationErrorBoundary.getDerivedStateFromError()).toEqual({ hasError: true });
    expect(renderToStaticMarkup(<ApplicationErrorBoundary><p>content</p></ApplicationErrorBoundary>))
      .toContain("content");
  });
});
