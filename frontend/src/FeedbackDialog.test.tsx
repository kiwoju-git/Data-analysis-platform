import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FeedbackDialog } from "./FeedbackDialog";
import { setCurrentLocale } from "./i18n/store";
import { RuntimeCompatibilityGate } from "./RuntimeMismatchPage";
import { buildSupportDiagnostics, copyFeedbackText, serializeFeedback } from "./supportDiagnostics";

afterEach(() => setCurrentLocale("ko"));

describe("local feedback", () => {
  it.each([
    ["ko", "문제 신고 / 의견 보내기", "전체 내용 미리보기", "자동 전송하지 않습니다."],
    ["en", "Report a Problem / Send Feedback", "Full content preview", "Nothing is sent automatically."],
  ] as const)("renders %s with a labelled modal and fully visible readonly preview", (locale, title, preview, privacy) => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(<FeedbackDialog onClose={() => undefined} />);
    expect(html).toContain("<dialog");
    expect(html).toContain('aria-modal="true"');
    expect(html).toContain("aria-labelledby=");
    expect(html).toContain(title);
    expect(html).toContain(preview);
    expect(html).toContain(privacy);
    expect(html).toContain("readonly");
    expect(html).toContain("feedback_schema_version");
    expect(html).toContain("diagnostics");
    expect(html).not.toContain("<form");
    expect(html).not.toContain("mailto:");
    expect(html).not.toContain("github.com");
  });

  it("preserves explicitly authored text separately from automatic diagnostics", () => {
    const text = '<script>PRIVATE</script> & "한글" \uE000user-owned\uE001';
    const diagnostics = buildSupportDiagnostics({}, { locale: "ko" });
    const serialized = serializeFeedback({ problemType: "suggestion", reproduction: text, expected: text, actual: text, repeatability: "once" }, diagnostics);
    const document = JSON.parse(serialized) as { user_feedback: { reproduction: string; expected: string; actual: string }; diagnostics: unknown };
    expect(document.user_feedback.reproduction).toBe(text);
    expect(document.user_feedback.expected).toBe(text);
    expect(document.user_feedback.actual).toBe(text);
    expect(JSON.stringify(document.diagnostics)).not.toContain("PRIVATE");
  });

  it("keeps local feedback available before a successful runtime handshake", () => {
    setCurrentLocale("en");
    for (const state of [
      { kind: "checking", runtime: null, result: null, error: null },
      { kind: "blocked", runtime: null, result: null, error: "api_unreachable" },
    ] as const) {
      const html = renderToStaticMarkup(<RuntimeCompatibilityGate state={state} onRetry={() => undefined} />);
      expect(html).toContain("Report a Problem / Send Feedback");
      expect(html).toContain('class="secondary-button feedback-entry"');
      expect(html).not.toContain('class="app-shell"');
    }
  });

  it("uses clipboard only when requested and returns a selectable-text fallback", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    expect(await copyFeedbackText("reviewed only", { writeText })).toBe("copied");
    expect(writeText).toHaveBeenCalledExactlyOnceWith("reviewed only");
    expect(await copyFeedbackText("private", undefined)).toBe("manual");
    expect(await copyFeedbackText("private", { writeText: vi.fn().mockRejectedValue(new Error("secret raw exception")) })).toBe("manual");
  });
});
