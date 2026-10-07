export type ViewportAnchor = { clientX: number; clientY: number };

export function pointerToViewport(event: ViewportAnchor): ViewportAnchor | null {
  return Number.isFinite(event.clientX) && Number.isFinite(event.clientY)
    ? { clientX: event.clientX, clientY: event.clientY }
    : null;
}

export function svgPointToViewport(
  svg: SVGSVGElement,
  x: number,
  y: number,
): ViewportAnchor | null {
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  const matrix = svg.getScreenCTM();
  if (matrix === null) return null;
  const point = new DOMPoint(x, y).matrixTransform(matrix);
  return pointerToViewport({ clientX: point.x, clientY: point.y });
}

export function elementCenterToViewport(element: Element): ViewportAnchor | null {
  const rect = element.getBoundingClientRect();
  return pointerToViewport({
    clientX: rect.left + rect.width / 2,
    clientY: rect.top + rect.height / 2,
  });
}

export function tooltipPosition(
  anchor: ViewportAnchor,
  width: number,
  height: number,
  viewportWidth: number,
  viewportHeight: number,
): { left: number; top: number } {
  const right = anchor.clientX + 10;
  const above = anchor.clientY - height - 10;
  const left = right + width <= viewportWidth - 8 ? right : anchor.clientX - width - 10;
  const top = above >= 8 ? above : anchor.clientY + 10;
  return {
    left: Math.max(8, Math.min(left, viewportWidth - width - 8)),
    top: Math.max(8, Math.min(top, viewportHeight - height - 8)),
  };
}
