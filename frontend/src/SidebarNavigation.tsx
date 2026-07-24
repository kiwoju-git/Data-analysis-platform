import { useEffect, useRef } from "react";

import type { SidebarNavigationGroup } from "./sidebarNavigationModel";

export function SidebarNavigation({
  groups,
  onNavigate,
}: {
  groups: SidebarNavigationGroup[];
  onNavigate?: () => void;
}) {
  const activeItemRef = useRef<HTMLButtonElement>(null);

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

  return (
    <nav className="sidebar-navigation" aria-label="주요 메뉴">
      <ul className="sidebar-groups">
        {groups.map((group) => (
          <li
            className={
              group.active
                ? "sidebar-group sidebar-group-active"
                : "sidebar-group"
            }
            key={group.id}
          >
            <button
              className="sidebar-group-control"
              disabled={group.children.every((item) => item.disabled)}
              onClick={() => {
                const target =
                  group.children.find((item) => item.active && !item.disabled) ??
                  group.children.find(
                    (item) =>
                      item.id === group.defaultChildId && !item.disabled,
                  ) ??
                  group.children.find((item) => !item.disabled);
                target?.onActivate();
                onNavigate?.();
              }}
              type="button"
            >
              {group.label}
            </button>
            <ul className="sidebar-submenu">
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
        ))}
      </ul>
    </nav>
  );
}
