import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import * as lazyPages from "./lazyWorkspacePages";
import {
  WorkspacePageErrorBoundary,
  WorkspacePageLoadError,
  WorkspacePageLoading,
} from "./WorkspacePageBoundary";

describe("lazy workspace pages", () => {
  it("exposes accessible loading and sanitized error states", () => {
    const loadingHtml = renderToString(<WorkspacePageLoading />);
    const errorHtml = renderToString(<WorkspacePageLoadError />);

    expect(loadingHtml).toContain('role="status"');
    expect(loadingHtml).toContain('aria-label="페이지 로딩"');
    expect(errorHtml).toContain('role="alert"');
    expect(errorHtml).toContain("화면 다시 불러오기");
    expect(errorHtml).not.toContain("stack");
    expect(errorHtml).not.toContain("chunk URL");
  });

  it("replaces failed route content with the public retry state", () => {
    const boundary = new WorkspacePageErrorBoundary({
      children: createElement("span", null, "private route detail"),
      resetKey: "help",
    });
    boundary.state = WorkspacePageErrorBoundary.getDerivedStateFromError();

    const html = renderToString(boundary.render());
    expect(html).toContain("페이지를 불러오지 못했습니다.");
    expect(html).not.toContain("private route detail");
  });

  it("keeps Help and Report Center behind independent route loaders", async () => {
    const [help, reports] = await Promise.all([
      import("./HelpCenterPage"),
      import("./ReportCenterPage"),
    ]);

    expect(Object.keys(help)).toEqual(["HelpCenterPage"]);
    expect(Object.keys(reports)).toEqual(["ReportCenterPage"]);
    expect(Object.keys(lazyPages).sort()).toEqual(["HelpCenterPage", "ReportCenterPage"]);
  });
});
