import { afterEach, describe, expect, it, vi } from "vitest";
import { elementCenterToViewport, pointerToViewport, svgPointToViewport, tooltipPosition } from "./chartCoordinates";

afterEach(() => vi.unstubAllGlobals());
describe("viewport chart coordinates", () => {
  it.each([0.5, 1, 1.5])("transforms SVG units at scale %s including translation", (scale) => {
    vi.stubGlobal("DOMPoint", class {
      constructor(public x: number, public y: number) {}
      matrixTransform(matrix: { a: number; d: number; e: number; f: number }) {
        return { x: this.x * matrix.a + matrix.e, y: this.y * matrix.d + matrix.f };
      }
    });
    const svg = { getScreenCTM: () => ({ a: scale, d: scale, e: 120, f: 45 }) } as unknown as SVGSVGElement;
    expect(svgPointToViewport(svg, 80, 60)).toEqual({ clientX: 120 + 80 * scale, clientY: 45 + 60 * scale });
  });
  it("does not substitute zero for missing or nonfinite coordinates", () => {
    expect(svgPointToViewport({ getScreenCTM: () => null } as unknown as SVGSVGElement, 1, 2)).toBeNull();
    expect(pointerToViewport({ clientX: Infinity, clientY: 2 })).toBeNull();
    expect(pointerToViewport({ clientX: 0, clientY: 0 })).toEqual({ clientX: 0, clientY: 0 });
  });
  it("uses client rect center without adding document scroll offsets", () => {
    vi.stubGlobal("scrollX", 1000);
    vi.stubGlobal("scrollY", 2000);
    const target = { getBoundingClientRect: () => ({ left: 40, top: 60, width: 10, height: 20 }) } as unknown as Element;
    expect(elementCenterToViewport(target)).toEqual({ clientX: 45, clientY: 70 });
  });
  it("flips and clamps tooltip rectangles inside viewport margins", () => {
    expect(tooltipPosition({ clientX: 380, clientY: 10 }, 200, 100, 390, 844)).toEqual({ left: 170, top: 20 });
    expect(tooltipPosition({ clientX: -20, clientY: 1000 }, 280, 100, 390, 844)).toEqual({ left: 8, top: 736 });
  });
});
