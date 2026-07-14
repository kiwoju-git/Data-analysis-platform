import { describe, expect, it } from "vitest";

import { getAnalysisRunErrorDetails } from "./analysisRunErrors";

describe("attribute control chart run errors", () => {
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
    const details = getAnalysisRunErrorDetails(code);

    expect(details.title).toBe(title);
    expect(details.message.length).toBeGreaterThan(0);
    expect(details.action.length).toBeGreaterThan(0);
  });
});
