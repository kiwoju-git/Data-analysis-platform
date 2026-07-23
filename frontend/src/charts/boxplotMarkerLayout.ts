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
      Math.max(...previous.map((item) => Math.abs(item.x - marker.x))) <= 4
    ) {
      previous.push(marker);
    } else {
      groups.push([marker]);
    }
  }

  const lastXByRow = [-Infinity, -Infinity, -Infinity];
  return groups.map((group) => {
    const x = group.reduce((sum, marker) => sum + marker.x, 0) / group.length;
    let row = lastXByRow.findIndex((lastX) => x - lastX >= minimumGapPx);
    if (row < 0) {
      row = lastXByRow.indexOf(Math.min(...lastXByRow));
    }
    lastXByRow[row] = x;
    return {
      anchor: x < left + minimumGapPx / 2 ? "start" : x > right - minimumGapPx / 2 ? "end" : "middle",
      keys: group.map((marker) => marker.key),
      label: group.map((marker) => marker.label).join(" · "),
      row,
      value: group[0].value,
      x,
    };
  });
}
