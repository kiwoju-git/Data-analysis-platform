export function toggleGraphVariableSelection(
  selectedIds: string[],
  columnId: string,
  maximum: number,
): string[] {
  if (selectedIds.includes(columnId)) {
    return selectedIds.filter((selectedId) => selectedId !== columnId);
  }
  if (selectedIds.length >= maximum) {
    return selectedIds;
  }
  return [...selectedIds, columnId];
}
