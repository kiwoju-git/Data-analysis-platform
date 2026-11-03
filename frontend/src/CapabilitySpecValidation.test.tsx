import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DatasetVersionResponse } from "./api";
import { CapabilityPanel } from "./CapabilityPanel";
import { LocaleProvider } from "./i18n/LocaleProvider";
import { setCurrentLocale } from "./i18n/store";
import { capabilitySpecValidation } from "./capabilitySpecValidation";

afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("en"); });

function renderError(lsl: string, usl: string, target: string, locale: "en" | "ko") {
  vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
  const onRun = vi.fn();
  const html = renderToStaticMarkup(<LocaleProvider><CapabilityPanel
    analysisResult={null} filterValidationError={null} isRunningAnalysis={false}
    lsl={lsl} usl={usl} target={target} methodId="quality.capability" result={null}
    valueColumnId="measurement" valueColumns={[]}
    version={{ version_id: "synthetic-version" } as DatasetVersionResponse}
    onLslChange={() => {}} onUslChange={() => {}} onTargetChange={() => {}}
    onValueColumnChange={() => {}} onRun={onRun}
  /></LocaleProvider>);
  expect(onRun).not.toHaveBeenCalled();
  const notice = /class="notice-box notice-warning"[^>]*>(.*?)<\/div>/su.exec(html);
  expect(notice).not.toBeNull();
  return { html, message: notice![1] };
}

describe("Capability dynamic validation display boundary", () => {
  it("returns semantic errors and preserves empty/one-sided/boundary behavior", () => {
    expect(capabilitySpecValidation("NaN", "20", "")).toEqual({ kind: "error", code: "invalid_number", messageKey: "capability.validation.numeric" });
    expect(capabilitySpecValidation("10", "Infinity", "")).toMatchObject({ kind: "error", code: "invalid_number" });
    expect(capabilitySpecValidation("10", "20", "-Infinity")).toMatchObject({ kind: "error", code: "invalid_number" });
    expect(capabilitySpecValidation("10", "10", "")).toMatchObject({ kind: "error", code: "invalid_limit_order" });
    expect(capabilitySpecValidation("10", "", "9")).toMatchObject({ kind: "error", code: "target_outside_limits" });
    expect(capabilitySpecValidation("", "20", "21")).toMatchObject({ kind: "error", code: "target_outside_limits" });
    expect(capabilitySpecValidation(" ", "", "10")).toEqual({ kind: "empty" });
    expect(capabilitySpecValidation("0", "", "0")).toEqual({ kind: "ready" });
    expect(capabilitySpecValidation("", "0", "0")).toEqual({ kind: "ready" });
    expect(capabilitySpecValidation("-1e-3", "1e-3", "0")).toEqual({ kind: "ready" });
  });
  it.each([
    ["not a number", "20", "", "Specification limits and target must be finite numbers."],
    ["20", "10", "", "LSL must be less than USL."],
    ["10", "20", "9", "Target must be within the specified limits."],
    ["10", "20", "21", "Target must be within the specified limits."],
  ])("localizes invalid specification %s/%s/%s without editing drafts", (lsl, usl, target, expected) => {
    const before = JSON.stringify({ lsl, usl, target });
    const english = renderError(lsl, usl, target, "en");
    expect(english.message).toBe(expected);
    const korean = renderError(lsl, usl, target, "ko");
    expect(korean.message).toMatch(/[\uAC00-\uD7A3]/u);
    expect(renderError(lsl, usl, target, "en").message).toBe(expected);
    expect(JSON.stringify({ lsl, usl, target })).toBe(before);
  });
});
