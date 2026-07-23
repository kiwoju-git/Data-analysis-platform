export interface BoxplotMarker {
  key: string;
  label: string;
  value: number;
  x: number;
}

export interface BoxplotMarkerLabel {
  anchor: "start" | "middle" | "end";
  keys: string[];
  label: string;
  markerX: number;
  row: number;
  value: number;
  x: number;
}

export function layoutBoxplotMarkers(
  markers: BoxplotMarker[],
  minimumGapPx: number,
  left: number,
  right: number,
): BoxplotMarkerLabel[] {
  const sorted = [...markers].sort((a, b) => a.x - b.x);
  const groups: BoxplotMarker[][] = [];
  for (const marker of sorted) {
    const previous = groups.length === 0 ? undefined : groups[groups.length - 1];
    if (
      previous !== undefined &&
      previous.every((item) => item.value === marker.value)
    ) {
      previous.push(marker);
    } else {
      groups.push([marker]);
    }
  }

  const markerXs = groups.map(
    (group) => group.reduce((sum, marker) => sum + marker.x, 0) / group.length,
  );
  const availableWidth = Math.max(0, right - left);
  const gap =
    groups.length <= 1
      ? 0
      : Math.min(minimumGapPx, availableWidth / Math.max(1, groups.length - 1));
  const labelXs = [...markerXs];
  for (let index = 1; index < labelXs.length; index += 1) {
    labelXs[index] = Math.max(labelXs[index], labelXs[index - 1] + gap);
  }
  if (labelXs.length > 0 && labelXs[labelXs.length - 1] > right) {
    labelXs[labelXs.length - 1] = right;
    for (let index = labelXs.length - 2; index >= 0; index -= 1) {
      labelXs[index] = Math.min(labelXs[index], labelXs[index + 1] - gap);
    }
  }
  if (labelXs.length > 0 && labelXs[0] < left) {
    labelXs[0] = left;
    for (let index = 1; index < labelXs.length; index += 1) {
      labelXs[index] = Math.max(labelXs[index], labelXs[index - 1] + gap);
    }
  }

  return groups.map((group, index) => {
    const x = labelXs[index];
    return {
      anchor: x < left + minimumGapPx / 2 ? "start" : x > right - minimumGapPx / 2 ? "end" : "middle",
      keys: group.map((marker) => marker.key),
      label: group.map((marker) => marker.label).join(" · "),
      markerX: markerXs[index],
      row: 0,
      value: group[0].value,
      x,
    };
  });
}
