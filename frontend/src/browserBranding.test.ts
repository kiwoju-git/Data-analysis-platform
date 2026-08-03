import { describe, expect, it } from "vitest";
import indexHtml from "../index.html?raw";
import favicon from "../public/statistical-twin-favicon-v1.svg?raw";

describe("browser branding", () => {
  it("uses a route-independent Statistical Twin title and local favicon", () => {
    expect(indexHtml).toContain("<title>Statistical Twin</title>");
    expect(indexHtml).not.toContain("<title>DataLab Studio</title>");
    expect(indexHtml).toContain(
      '<meta name="application-name" content="Statistical Twin" />',
    );
    expect(indexHtml).toContain(
      '<meta name="theme-color" content="#034da2" />',
    );
    expect(indexHtml).toMatch(
      /<link\s+rel="icon"\s+type="image\/svg\+xml"\s+href="\/statistical-twin-favicon-v1\.svg"\s*\/>/,
    );
  });

  it("keeps the favicon self-contained and limited to safe SVG elements", () => {
    expect(favicon).toMatch(/^<svg\b[^>]*viewBox="0 0 64 64"[^>]*>/);
    expect(favicon.trimEnd()).toMatch(/<\/svg>$/);

    const tags = [...favicon.matchAll(/<\/?\s*([A-Za-z][\w:-]*)\b/g)].map(
      (match) => match[1],
    );
    expect(new Set(tags)).toEqual(
      new Set(["svg", "rect", "line", "polyline", "circle"]),
    );
    expect(favicon).not.toMatch(
      /<script\b|<foreignObject\b|<image\b|<animate\b|(?:href|src)\s*=|data:|url\s*\(/i,
    );

    const stack: string[] = [];
    for (const match of favicon.matchAll(/<(\/)?([A-Za-z][\w:-]*)\b[^>]*>/g)) {
      const [tag, closing, name] = match;
      if (closing) {
        expect(stack.pop()).toBe(name);
      } else if (!tag.endsWith("/>")) {
        stack.push(name);
      }
    }
    expect(stack).toEqual([]);
  });
});
