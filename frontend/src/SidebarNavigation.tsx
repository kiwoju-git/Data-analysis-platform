import { useEffect, useRef, useState, type RefObject } from "react";

import {
  createSidebarExpansionState,
  reconcileSidebarExpansionState,
} from "./sidebarExpansion";
import type {
  SidebarNavigationGroup,
  SidebarNavigationItem,
} from "./sidebarNavigationModel";

export function SidebarNavigation({
  groups,
  onNavigate,
}: {
  groups: SidebarNavigationGroup[];
  onNavigate?: () => void;
}) {
  const activeItemRef = useRef<HTMLButtonElement>(null);
  const activeGroupId = groups.find((group) => group.active)?.id ?? null;
  const activeLeafId = findActiveLeaf(groups.flatMap((group) => group.children))?.id ?? null;
  const previousActiveGroupIdRef = useRef<string | null>(activeGroupId);
  const previousActiveLeafIdRef = useRef<string | null>(activeLeafId);
  const groupIds = groups.map((group) => group.id).join("|");
  const [expandedGroups, setExpandedGroups] = useState(() => createSidebarExpansionState(groups));
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>(() =>
    expansionForItems(groups),
  );

  useEffect(() => {
    const focusedElement = document.activeElement;
    if (!(focusedElement instanceof HTMLElement) || focusedElement.closest(".sidebar-navigation") === null) return;
    activeItemRef.current?.focus();
  }, [groups]);

  useEffect(() => {
    setExpandedGroups((current) =>
      reconcileSidebarExpansionState(current, groups, previousActiveGroupIdRef.current),
    );
    previousActiveGroupIdRef.current = activeGroupId;
  }, [activeGroupId, groupIds, groups]);

  useEffect(() => {
    setExpandedItems((current) => {
      const next = { ...current };
      let changed = false;
      for (const group of groups) {
        for (const item of flattenItems(group.children)) {
          if (item.children === undefined) continue;
          if (!(item.id in next)) {
            next[item.id] = item.active;
            changed = true;
          }
        }
        if (activeLeafId !== previousActiveLeafIdRef.current) {
          for (const ancestorId of activeAncestorIds(group.children)) {
            if (next[ancestorId] !== true) {
              next[ancestorId] = true;
              changed = true;
            }
          }
        }
      }
      return changed ? next : current;
    });
    previousActiveLeafIdRef.current = activeLeafId;
  }, [activeLeafId, groups]);

  return (
    <nav className="sidebar-navigation" aria-label="주요 메뉴">
      <ul className="sidebar-groups">
        {groups.map((group) => {
          const expanded = expandedGroups[group.id] ?? true;
          const submenuId = `sidebar-submenu-${group.id}`;
          if (group.direct) {
            return (
              <li className={`sidebar-group${group.active ? " sidebar-group-active" : ""}`} key={group.id}>
                <button
                  aria-current={group.active ? "page" : undefined}
                  className="sidebar-group-control"
                  onClick={() => {
                    group.onActivate?.();
                    onNavigate?.();
                  }}
                  type="button"
                >
                  <span>{group.label}</span>
                </button>
              </li>
            );
          }
          return (
            <li className={["sidebar-group", group.active ? "sidebar-group-active" : "", expanded ? "" : "is-collapsed"].filter(Boolean).join(" ")} key={group.id}>
              <button
                aria-controls={submenuId}
                aria-expanded={expanded}
                className="sidebar-group-control"
                onClick={() => setExpandedGroups((current) => ({ ...current, [group.id]: !(current[group.id] ?? true) }))}
                type="button"
              >
                <span>{group.label}</span>
                <Chevron className="sidebar-group-chevron" />
              </button>
              <ul className="sidebar-submenu" hidden={!expanded} id={submenuId}>
                {group.children.map((item) => (
                  <NavigationItem
                    activeItemRef={activeItemRef}
                    expandedItems={expandedItems}
                    item={item}
                    key={item.id}
                    level={0}
                    onNavigate={onNavigate}
                    onToggle={(id) => setExpandedItems((current) => ({ ...current, [id]: !(current[id] ?? false) }))}
                  />
                ))}
              </ul>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function NavigationItem({
  activeItemRef,
  expandedItems,
  item,
  level,
  onNavigate,
  onToggle,
}: {
  activeItemRef: RefObject<HTMLButtonElement>;
  expandedItems: Record<string, boolean>;
  item: SidebarNavigationItem;
  level: number;
  onNavigate?: () => void;
  onToggle: (id: string) => void;
}) {
  const hasChildren = item.children !== undefined && item.children.length > 0;
  const hasActiveDescendant = item.children?.some((child) => hasActiveItem(child)) === true;
  const expanded = expandedItems[item.id] ?? false;
  const submenuId = `sidebar-tree-${safeId(item.id)}`;
  const buttonClass = level === 0 ? "sidebar-submenu-button" : "sidebar-method-button";
  return (
    <li className={hasChildren ? `sidebar-tree-item sidebar-tree-level-${level}` : undefined}>
      <button
        aria-controls={hasChildren ? submenuId : undefined}
        aria-current={item.active && !hasActiveDescendant ? "page" : undefined}
        aria-disabled={item.disabled || undefined}
        aria-expanded={hasChildren ? expanded : undefined}
        className={`${buttonClass}${item.active ? " is-active" : ""}${level > 1 ? " is-nested" : ""}`}
        disabled={item.disabled}
        onClick={() => {
          if (hasChildren) {
            if (!item.active) item.onActivate?.();
            onToggle(item.id);
          }
          else {
            item.onActivate?.();
            onNavigate?.();
          }
        }}
        ref={!hasChildren && item.active ? activeItemRef : undefined}
        type="button"
      >
        <span>{item.label}</span>
        {hasChildren ? <Chevron className="sidebar-item-chevron" /> : null}
      </button>
      {hasChildren ? (
        <ul className={level === 0 ? "sidebar-method-list" : "sidebar-family-method-list"} hidden={!expanded} id={submenuId}>
          {item.children?.map((child) => (
            <NavigationItem
              activeItemRef={activeItemRef}
              expandedItems={expandedItems}
              item={child}
              key={child.id}
              level={level + 1}
              onNavigate={onNavigate}
              onToggle={onToggle}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function hasActiveItem(item: SidebarNavigationItem): boolean {
  return item.active || item.children?.some((child) => hasActiveItem(child)) === true;
}

function Chevron({ className }: { className: string }) {
  return <svg aria-hidden="true" className={className} viewBox="0 0 16 16"><path d="M3.5 6 8 10.5 12.5 6" /></svg>;
}

function safeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}

function flattenItems(items: SidebarNavigationItem[]): SidebarNavigationItem[] {
  return items.flatMap((item) => [item, ...flattenItems(item.children ?? [])]);
}

function findActiveLeaf(items: SidebarNavigationItem[]): SidebarNavigationItem | null {
  for (const item of items) {
    const activeChild = findActiveLeaf(item.children ?? []);
    if (activeChild !== null) return activeChild;
    if (item.active && (item.children === undefined || item.children.length === 0)) return item;
  }
  return null;
}

function activeAncestorIds(items: SidebarNavigationItem[]): string[] {
  for (const item of items) {
    if (item.active && (item.children === undefined || item.children.length === 0)) return [];
    const descendantPath = activeAncestorIds(item.children ?? []);
    if (descendantPath.length > 0 || item.children?.some((child) => child.active) === true) {
      return [item.id, ...descendantPath];
    }
  }
  return [];
}

function expansionForItems(groups: SidebarNavigationGroup[]): Record<string, boolean> {
  return Object.fromEntries(
    groups.flatMap((group) =>
      flattenItems(group.children)
        .filter((item) => item.children !== undefined && item.children.length > 0)
        .map((item) => [item.id, item.active]),
    ),
  );
}
