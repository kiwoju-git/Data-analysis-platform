import type { SidebarNavigationGroup } from "./sidebarNavigationModel";

export type SidebarExpansionState = Record<string, boolean>;

export function createSidebarExpansionState(
  groups: SidebarNavigationGroup[],
): SidebarExpansionState {
  return Object.fromEntries(groups.map((group) => [group.id, true]));
}

export function reconcileSidebarExpansionState(
  current: SidebarExpansionState,
  groups: SidebarNavigationGroup[],
  previousActiveGroupId: string | null,
): SidebarExpansionState {
  let changed = false;
  const next = { ...current };
  for (const group of groups) {
    if (!(group.id in next)) {
      next[group.id] = true;
      changed = true;
    }
  }
  const activeGroupId = groups.find((group) => group.active)?.id ?? null;
  if (
    activeGroupId !== null &&
    activeGroupId !== previousActiveGroupId &&
    next[activeGroupId] !== true
  ) {
    next[activeGroupId] = true;
    changed = true;
  }
  return changed ? next : current;
}
