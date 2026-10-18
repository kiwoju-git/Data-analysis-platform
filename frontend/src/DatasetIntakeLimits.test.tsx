import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { DatasetIntakeLimits, DatasetIntakeLimitsSummary } from "./DatasetIntakeLimits";
import { setCurrentLocale } from "./i18n/store";

afterEach(() => setCurrentLocale("ko"));

describe("server-provided intake limits", () => {
  it.each(["ko", "en"] as const)("shows exact server byte limits in %s", (locale) => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(<DatasetIntakeLimitsSummary limits={{
      file_bytes: 1024, paste_utf8_bytes: 2048, json_request_bytes: 16384,
      multipart_request_bytes: 4096, multipart_files: 1,
      multipart_fields: 16, multipart_field_bytes: 64,
      parsed_rows: 1000, parsed_columns: 50,
    }} />);
    expect(html).toContain("1,024");
    expect(html).toContain("2,048");
    expect(html).toContain("16,384");
    expect(html).toContain("1,000");
    expect(html).not.toContain("intake.limits");
  });

  it("does not invent a default limit before the server responds", () => {
    setCurrentLocale("en");
    const html = renderToStaticMarkup(<DatasetIntakeLimits />);
    expect(html).toContain('role="status"');
    expect(html).not.toContain("104,857,600");
  });
});
