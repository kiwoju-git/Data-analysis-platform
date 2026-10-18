import { t } from "./i18n/translate";
import type { AppLocale } from "./i18n/types";

export interface StoredGroupIdentity {
  group_index: number;
  group_label: string;
  group_value?: string;
}

export function validStoredGroupIdentities(value: unknown, requireFull: boolean): boolean {
  if (!Array.isArray(value)) return false;
  const indices = new Set<number>();
  return value.every((group: unknown) => {
    if (typeof group !== "object" || group === null) return false;
    const row = group as Record<string, unknown>;
    if (typeof row.group_index !== "number" || !Number.isInteger(row.group_index) || row.group_index < 0 || indices.has(row.group_index) || typeof row.group_label !== "string" || (requireFull && typeof row.group_value !== "string")) return false;
    indices.add(row.group_index);
    return true;
  });
}

export function fullGroupName(group: StoredGroupIdentity): string {
  return group.group_value ?? group.group_label;
}

export function groupDisplayLabel(group: StoredGroupIdentity, groups: readonly StoredGroupIdentity[], locale: AppLocale): string {
  return groups.filter((candidate) => candidate.group_label === group.group_label).length > 1
    ? `${t("group_identity.group_number", { number: group.group_index + 1 }, locale)}: ${group.group_label}`
    : group.group_label;
}

export function pairGroupLabel(index: number | undefined, label: string, groups: readonly StoredGroupIdentity[], locale: AppLocale): string {
  const group = index === undefined ? undefined : groups.find((candidate) => candidate.group_index === index);
  return group ? groupDisplayLabel(group, groups, locale) : label;
}
