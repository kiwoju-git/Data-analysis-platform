import { afterEach, describe, expect, it } from "vitest";

import { getAnalysisRunErrorDetails } from "./analysisRunErrors";
import { setCurrentLocale } from "./i18n/store";

describe("attribute control chart run errors", () => {
  afterEach(() => setCurrentLocale("ko"));

  it.each([
    ["invalid_attribute_control_chart_options", "계수형 관리도 옵션 형식 오류"],
    ["attribute_control_chart_count_definition_mismatch", "계수 정의 불일치"],
    ["attribute_control_chart_count_not_finite", "유한한 계수 필요"],
    ["attribute_control_chart_denominator_not_finite", "유한한 분모 필요"],
    ["attribute_control_chart_defectives_exceed_sample_size", "불량품 수가 표본 크기 초과"],
    ["attribute_control_chart_np_varying_sample_size", "NP 표본 크기 불일치"],
    [
      "attribute_control_chart_c_constant_opportunity_required",
      "동일 검사 기회 확인 필요",
    ],
    ["attribute_control_chart_zero_variation", "관리한계 추정 불가"],
  ])("maps %s to a stable recovery message", (code, title) => {
    const details = getAnalysisRunErrorDetails(code, "ko");

    expect(details.title).toBe(title);
    expect(details.message.length).toBeGreaterThan(0);
    expect(details.action.length).toBeGreaterThan(0);
  });

  it.each([
    ["analysis_run_failed", "Analysis run failed", "분석 실행 실패"],
    ["custom_response_required", "Response variable required", "반응 변수 필요"],
    ["unknown_failure", "Analysis execution error", "분석 실행 오류"],
  ])("translates exact, pattern and fallback display fields for %s", (code, english, korean) => {
    const en = getAnalysisRunErrorDetails(code, "en");
    const ko = getAnalysisRunErrorDetails(code, "ko");
    expect(en.title).toBe(english);
    expect(ko.title).toBe(korean);
    expect(JSON.stringify(en)).not.toMatch(/[가-힣\uE000\uE001]/u);
    expect(en.message).not.toBe(ko.message);
    expect(en.action).not.toBe(ko.action);
  });

  it("uses the current locale at lookup time without modifying the source entry", () => {
    setCurrentLocale("en");
    const english = getAnalysisRunErrorDetails("analysis_run_failed");
    setCurrentLocale("ko");
    expect(getAnalysisRunErrorDetails("analysis_run_failed").title).toBe("분석 실행 실패");
    setCurrentLocale("en");
    expect(getAnalysisRunErrorDetails("analysis_run_failed")).toEqual(english);
  });

  it("matches codes literally instead of translating token-shaped input", () => {
    const fallback = getAnalysisRunErrorDetails("unknown_failure", "en");
    expect(getAnalysisRunErrorDetails("분석 실행 실패", "en")).toEqual(fallback);
    expect(getAnalysisRunErrorDetails("\uE000twoVariances.method\uE001", "en")).toEqual(fallback);
    for (const unknownCode of ["__proto__", "constructor", "toString"]) {
      expect(getAnalysisRunErrorDetails(unknownCode, "en")).toEqual(fallback);
    }
    expect(getAnalysisRunErrorDetails("custom_response_required", "en").title).toBe(
      "Response variable required",
    );
  });
});
