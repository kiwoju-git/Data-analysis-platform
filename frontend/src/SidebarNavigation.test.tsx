import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import {
  createSidebarExpansionState,
  reconcileSidebarExpansionState,
} from "./sidebarExpansion";
import { SidebarNavigation } from "./SidebarNavigation";
import type { SidebarNavigationGroup } from "./sidebarNavigationModel";

describe("SidebarNavigation", () => {
  it("exposes semantic hierarchy and distinguishes the active path from the leaf", () => {
    const groups = navigationGroups("analysis");
    groups[2].children = [{ id: "domain", kind: "domain", label: "Domain", active: true,
      children: [{ id: "family", kind: "family", label: "Family", active: true,
        children: [{ id: "method", kind: "method", label: "Method", active: true }] }] }];
    const html = renderToString(<SidebarNavigation groups={groups} />);
    expect(html).toContain('data-node-kind="domain" data-node-depth="0"');
    expect(html).toContain('data-node-kind="family" data-node-depth="1"');
    expect(html).toContain('data-node-kind="method" data-node-depth="2"');
    expect(html.match(/is-active-ancestor/g)).toHaveLength(2);
    expect(html.match(/aria-current="page"/g)).toHaveLength(1);
    expect(html).not.toContain('role="tree"');
  });
  it("separates workspace navigation from disclosure with accessible icons", () => {
    const groups = navigationGroups("analysis");
    groups[2].onActivate = vi.fn();
    const html = renderToString(<SidebarNavigation groups={groups} />);
    expect(html).toContain('class="sidebar-group-toggle"');
    expect(html).toContain('aria-label="분석 메뉴 접기"');
    expect(html).toMatch(/class="sidebar-group-toggle"[^>]*aria-controls="sidebar-submenu-analysis"/);
    expect(html).toContain('aria-hidden="true"');
    expect(groups[2].onActivate).not.toHaveBeenCalled();
  });
  it("expands the active group and keeps inactive submenus hidden", () => {
    const groups = navigationGroups("analysis");
    const html = renderToString(<SidebarNavigation groups={groups} />);

    expect((html.match(/aria-expanded="true"/g) ?? [])).toHaveLength(1);
    expect((html.match(/hidden=""/g) ?? [])).toHaveLength(2);
    expect(html).toContain('aria-controls="sidebar-submenu-analysis"');
    expect(html).toContain('id="sidebar-submenu-analysis"');
    expect(html).toContain('aria-current="page"');
    expect(html).not.toContain("파싱·스키마");
  });

  it("initializes only the active group as expanded", () => {
    const groups = navigationGroups("dataset");
    expect(createSidebarExpansionState(groups)).toEqual({
      home: false,
      dataset: true,
      analysis: false,
    });
  });

  it("preserves manual collapse and reopens a newly active group", () => {
    const datasetActive = navigationGroups("dataset");
    const collapsed = {
      home: true,
      dataset: false,
      analysis: false,
    };

    expect(
      reconcileSidebarExpansionState(collapsed, datasetActive, "dataset"),
    ).toBe(collapsed);

    const analysisActive = navigationGroups("analysis");
    expect(
      reconcileSidebarExpansionState(collapsed, analysisActive, "dataset"),
    ).toEqual({
      home: true,
      dataset: false,
      analysis: true,
    });
  });

  it("does not invoke navigation callbacks while rendering group controls", () => {
    const onActivate = vi.fn();
    const groups = navigationGroups("home");
    groups[0].children[0].onActivate = onActivate;

    renderToString(<SidebarNavigation groups={groups} onNavigate={vi.fn()} />);

    expect(onActivate).not.toHaveBeenCalled();
  });
});

function navigationGroups(
  activeId: "home" | "dataset" | "analysis",
): SidebarNavigationGroup[] {
  return [
    group("home", "홈", activeId),
    group("dataset", "데이터셋", activeId),
    group("analysis", "분석", activeId),
  ];
}

function group(
  id: "home" | "dataset" | "analysis",
  label: string,
  activeId: string,
): SidebarNavigationGroup {
  return {
    active: id === activeId,
    children: [
      {
        active: id === activeId,
        id: `${id}-leaf`,
        label: id === "dataset" ? "데이터 등록" : `${label} 항목`,
        onActivate: vi.fn(),
      },
    ],
    id,
    label,
  };
}
