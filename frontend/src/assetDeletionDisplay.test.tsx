import type { ComponentProps, ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AssetDeletionNotice, UnifiedAssetCatalogPanel } from "./UnifiedAssetCatalogPanel";
import { LocaleProvider } from "./i18n/LocaleProvider";
import { setCurrentLocale } from "./i18n/store";
import { t, translateSystemText } from "./i18n/translate";
import type { AppLocale } from "./i18n/types";

function markup(node: ReactNode, locale: AppLocale): string {
  vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
  return renderToStaticMarkup(<LocaleProvider>{node}</LocaleProvider>);
}

afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("en"); });

describe("asset deletion display boundary", () => {
  it("renders each stored notice with the current locale without changing its counts", () => {
    const notices: Array<ComponentProps<typeof AssetDeletionNotice>["notice"]> = [
      { kind: "factorial_analysis", predictionCount: 2, reportCount: 3 },
      { kind: "factorial_asset" },
      { kind: "analysis_run", fileCount: 7 },
      { kind: "doe_design", analysisCount: 4, predictionCount: 5, reportCount: 6, versionCount: 2, runCount: 32, revisionCount: 3 },
      { kind: "bayesian_study", trialCount: 12 },
    ];
    for (const notice of notices) {
      Object.freeze(notice);
      const snapshot = JSON.stringify(notice);
      const en = markup(<AssetDeletionNotice notice={notice} />, "en");
      const ko = markup(<AssetDeletionNotice notice={notice} />, "ko");
      expect(en).not.toMatch(/[\uAC00-\uD7A3]/u);
      expect(ko).toMatch(/[\uAC00-\uD7A3]/u);
      expect(markup(<AssetDeletionNotice notice={notice} />, "en")).toBe(en);
      expect(JSON.stringify(notice)).toBe(snapshot);
    }
  });

  it("keeps DOE dependency counts distinct and retains the zero count", () => {
    const notice = { kind: "doe_design", analysisCount: 4, predictionCount: 0, reportCount: 6, versionCount: 2, runCount: 32, revisionCount: 3 } as const;
    const html = markup(<AssetDeletionNotice notice={notice} />, "en");
    expect(html).toContain(`${t("doe.report.prediction", {}, "en")}: 0`);
    expect(html).toContain(t("assets.delete.designSummary", { versions: 2, runs: 32, revisions: 3, analyses: 4 }, "en"));
    expect(html).not.toContain(t("doe.report.confirm", {}, "en"));
  });

  it("keeps the irreversible deletion warning on analysis and study notices", () => {
    expect(markup(<AssetDeletionNotice notice={{ kind: "analysis_run", fileCount: 7 }} />, "en"))
      .toContain("7 dependent files? This action cannot be undone.");
    expect(markup(<AssetDeletionNotice notice={{ kind: "bayesian_study", trialCount: 12 }} />, "en"))
      .toContain("12 trials? This action cannot be undone.");
  });

  it("translates asset filter labels while preserving input IDs and enum values", () => {
    for (const locale of ["en", "ko", "en"] as const) {
      const html = markup(<UnifiedAssetCatalogPanel category={null} revision={0} onMutation={vi.fn()} />, locale);
      for (const label of ["검색", "상태", "정렬", "표시 옵션"]) {
        expect(html).toContain(translateSystemText(label, locale));
      }
      expect(html).toContain('id="asset-catalog-search"');
      expect(html).toContain('id="asset-catalog-status"');
      expect(html).toContain('value="updated_desc"');
      expect(html).toContain('value="available"');
    }
  });
});
