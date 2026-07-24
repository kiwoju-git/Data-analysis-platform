import { useEffect, useRef, useState } from "react";

import {
  createSidebarExpansionState,
  reconcileSidebarExpansionState,
} from "./sidebarExpansion";
import type { SidebarNavigationGroup } from "./sidebarNavigationModel";

export function SidebarNavigation({
  groups,
  onNavigate,
}: {
  groups: SidebarNavigationGroup[];
  onNavigate?: () => void;
}) {
  const activeItemRef = useRef<HTMLButtonElement>(null);
  const activeGroupId = groups.find((group) => group.active)?.id ?? null;
  const previousActiveGroupIdRef = useRef<string | null>(activeGroupId);
  const groupIds = groups.map((group) => group.id).join("|");
  const [expandedGroups, setExpandedGroups] = useState(() =>
    createSidebarExpansionState(groups),
  );

  useEffect(() => {
    const focusedElement = document.activeElement;
    if (
      !(focusedElement instanceof HTMLElement) ||
      focusedElement.closest(".sidebar-navigation") === null
    ) {
      return;
    }
    activeItemRef.current?.focus();
  }, [groups]);

  useEffect(() => {
    setExpandedGroups((current) =>
      reconcileSidebarExpansionState(
        current,
        groups,
        previousActiveGroupIdRef.current,
      ),
    );
    previousActiveGroupIdRef.current = activeGroupId;
  }, [activeGroupId, groupIds, groups]);

  return (
    <nav className="sidebar-navigation" aria-label="주요 메뉴">
      <ul className="sidebar-groups">
        {groups.map((group) => {
          const expanded = expandedGroups[group.id] ?? true;
          const submenuId = `sidebar-submenu-${group.id}`;
          return (
            <li
              className={[
                "sidebar-group",
                group.active ? "sidebar-group-active" : "",
                expanded ? "" : "is-collapsed",
              ]
                .filter(Boolean)
                .join(" ")}
              key={group.id}
            >
            <button
              aria-controls={submenuId}
              aria-expanded={expanded}
              className="sidebar-group-control"
              onClick={() =>
                setExpandedGroups((current) => ({
                  ...current,
                  [group.id]: !(current[group.id] ?? true),
                }))
              }
              type="button"
            >
              <span>{group.label}</span>
              <svg
                aria-hidden="true"
                className="sidebar-group-chevron"
                viewBox="0 0 16 16"
              >
                <path d="M3.5 6 8 10.5 12.5 6" />
              </svg>
            </button>
            <ul
              className="sidebar-submenu"
              hidden={!expanded}
              id={submenuId}
            >
              {group.children.map((item) => (
                <li key={item.id}>
                  <button
                    aria-current={item.active ? "page" : undefined}
                    aria-disabled={item.disabled || undefined}
                    className={
                      item.active
                        ? "sidebar-submenu-button is-active"
                        : "sidebar-submenu-button"
                    }
                    disabled={item.disabled}
                    onClick={() => {
                      item.onActivate();
                      onNavigate?.();
                    }}
                    ref={item.active ? activeItemRef : undefined}
                    type="button"
                  >
                    {item.label}
                  </button>
                </li>
              ))}
            </ul>
          </li>
          );
        })}
      </ul>
    </nav>
  );
}
