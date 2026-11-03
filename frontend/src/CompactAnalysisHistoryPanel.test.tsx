import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";
import type { AnalysisMethodDescriptor, DatasetVersionResponse } from "./api";
import { CompactAnalysisHistoryPanel } from "./CompactAnalysisHistoryPanel";
import { LocaleProvider } from "./i18n/LocaleProvider";
import { setCurrentLocale } from "./i18n/store";

afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("en"); });

it.each(["en", "ko"] as const)("localizes unloaded history count without fabricating a count in %s", (locale) => {
  vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
  const html = renderToStaticMarkup(<LocaleProvider><CompactAnalysisHistoryPanel
    method={{ method_id: "quality.run_chart" } as AnalysisMethodDescriptor}
    version={{ version_id: "synthetic-version" } as DatasetVersionResponse}
    isRestoring={false} refreshKey={null} onRestore={() => {}} /></LocaleProvider>);
  const label = locale === "en" ? "Not loaded" : "확인 전";
  expect(html).toContain(`class="status-pill" aria-label="${label}">${label}</span>`);
  expect(html).not.toContain("확인 전개");
});
