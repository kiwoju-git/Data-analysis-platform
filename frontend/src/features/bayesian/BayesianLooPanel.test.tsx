import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianLooPanel } from "./BayesianLooPanel";
import { requestBoLoo } from "../../api/boLoo";

vi.mock("../../api/boLoo", () => ({ requestBoLoo: vi.fn() }));
describe("saved source conditional LOO boundary", () => {
  afterEach(() => { setCurrentLocale("ko"); vi.clearAllMocks(); });
  it.each(["en", "ko"] as const)("requires explicit calculation and states limits in %s", locale => {
    setCurrentLocale(locale);
    const model = { model_id: "model", snapshot_sha256: "a".repeat(64), config_sha256: "b".repeat(64), history_sha256: "c".repeat(64), source_history_revision_id: "history", source_is_current: false,
      objective: { responses: [{ response_id: "yield", name: "한글 <raw>", unit: null }] } };
    const before = JSON.stringify(model);
    const html = renderToStaticMarkup(<BayesianLooPanel studyId="study" model={model} contextKey="source" />);
    expect(html).toContain(locale === "en" ? "Historical saved model" : "과거 저장 모형");
    expect(html).toContain(locale === "en" ? "not refitted cross-validation" : "재적합하는 교차검증이나 독립 외부 검증이 아닙니다");
    expect(html).toContain(locale === "en" ? "does not automatically switch" : "자동 전환하지 않습니다");
    expect(html).not.toContain("<svg data-chart");
    expect(requestBoLoo).not.toHaveBeenCalled();
    expect(JSON.stringify(model)).toBe(before);
  });
});
