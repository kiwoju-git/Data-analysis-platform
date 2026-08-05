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
  const activeMethodId = groups
    .flatMap((group) => group.children)
    .flatMap((item) => item.children ?? [])
    .find((item) => item.active)?.id ?? null;
  const previousActiveGroupIdRef = useRef<string | null>(activeGroupId);
  const previousActiveMethodIdRef = useRef<string | null>(activeMethodId);
  const groupIds = groups.map((group) => group.id).join("|");
  const [expandedGroups, setExpandedGroups] = useState(() =>
    createSidebarExpansionState(groups),
  );
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(
      groups.flatMap((group) =>
        group.children
          .filter((item) => item.children !== undefined)
          .map((item) => [item.id, item.active]),
      ),
    ),
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

  useEffect(() => {
    setExpandedItems((current) => {
      const next = { ...current };
      let changed = false;
      for (const group of groups) {
        for (const item of group.children) {
          if (item.children === undefined) continue;
          if (!(item.id in next)) {
            next[item.id] = item.active;
            changed = true;
          } else if (
            activeMethodId !== previousActiveMethodIdRef.current &&
            item.children.some((child) => child.active) &&
            next[item.id] !== true
          ) {
            next[item.id] = true;
            changed = true;
          }
        }
      }
      return changed ? next : current;
    });
    previousActiveMethodIdRef.current = activeMethodId;
  }, [activeMethodId, groups]);

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
              {group.children.map((item) => {
                const hasChildren = item.children !== undefined;
                const itemExpanded = expandedItems[item.id] ?? false;
                const itemSubmenuId = `sidebar-methods-${item.id}`;
                return (
                  <li className={hasChildren ? "sidebar-module-item" : undefined} key={item.id}>
                    <button
                      aria-controls={hasChildren ? itemSubmenuId : undefined}
                      aria-current={!hasChildren && item.active ? "page" : undefined}
                      aria-disabled={item.disabled || undefined}
                      aria-expanded={hasChildren ? itemExpanded : undefined}
                      className={
                        item.active
                          ? "sidebar-submenu-button is-active"
                          : "sidebar-submenu-button"
                      }
                      disabled={item.disabled}
                      onClick={() => {
                        if (hasChildren) {
                          setExpandedItems((current) => ({ ...current, [item.id]: !itemExpanded }));
                        } else {
                          item.onActivate?.();
                          onNavigate?.();
                        }
                      }}
                      ref={!hasChildren && item.active ? activeItemRef : undefined}
                      type="button"
                    >
                      <span>{item.label}</span>
                      {hasChildren ? (
                        <svg aria-hidden="true" className="sidebar-item-chevron" viewBox="0 0 16 16"><path d="M3.5 6 8 10.5 12.5 6" /></svg>
                      ) : null}
                    </button>
                    {hasChildren ? (
                      <ul className="sidebar-method-list" hidden={!itemExpanded} id={itemSubmenuId}>
                        {item.children!.map((method) => (
                          <li key={method.id}>
                            <button
                              aria-current={method.active ? "page" : undefined}
                              className={method.active ? "sidebar-method-button is-active" : "sidebar-method-button"}
                              disabled={method.disabled}
                              onClick={() => { method.onActivate?.(); onNavigate?.(); }}
                              ref={method.active ? activeItemRef : undefined}
                              type="button"
                            >{method.label}</button>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </li>
          );
        })}
      </ul>
    </nav>
  );
}
