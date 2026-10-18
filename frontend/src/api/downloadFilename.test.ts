import { describe, expect, it } from "vitest";
import { filenameFromContentDisposition } from "./client";

describe("download filename boundary", () => {
  it("prefers RFC5987 UTF-8 over the ASCII fallback", () => {
    expect(filenameFromContentDisposition("attachment; filename=report.html; filename*=UTF-8''%ED%95%9C%EA%B8%80%20report.html"))
      .toBe("한글 report.html");
  });
  it("falls back safely from malformed or unsupported extended names", () => {
    for (const extended of ["UTF-8''%ZZ", "UTF-8''%FF", "ISO-8859-1''%E9"]) {
      expect(filenameFromContentDisposition(`attachment; filename="safe report.html"; filename*=${extended}`)).toBe("safe report.html");
    }
    expect(filenameFromContentDisposition("attachment; filename*=UTF-8''%ZZ")).toBeNull();
  });
  it("removes paths, controls, bidi controls and invalid filesystem characters", () => {
    expect(filenameFromContentDisposition('attachment; filename="../../private/report.html"')).toBe("report.html");
    expect(filenameFromContentDisposition("attachment; filename*=UTF-8''C%3A%5Ctemp%5Creport%00%0A%3F.html")).toBe("report_.html");
    expect(filenameFromContentDisposition("attachment; filename*=UTF-8''%E2%80%AEreport.html")).toBe("report.html");
    expect(filenameFromContentDisposition('attachment; filename=".."')).toBeNull();
  });
  it("keeps valid Unicode, spaces and quoted semicolons without token translation", () => {
    expect(filenameFromContentDisposition('attachment; filename="saved; report \ue000.html"')).toBe("saved; report \ue000.html");
    expect(filenameFromContentDisposition(null)).toBeNull();
  });
});
