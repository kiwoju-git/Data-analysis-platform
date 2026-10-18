import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DatasetRequestError } from "./DatasetRequestError";
import { datasetRequestErrorCode } from "./datasetRequestErrors";
import { getCurrentLocale, setCurrentLocale } from "./i18n/store";

describe("dataset request recovery presentation", () => {
  const initialLocale = getCurrentLocale();
  afterEach(() => setCurrentLocale(initialLocale));

  it("localizes section recovery actions without translating or rendering server prose", () => {
    const render = () => renderToStaticMarkup(<DatasetRequestError kind="profile" error="dataset_profile_failed" onRetry={vi.fn()} />);
    setCurrentLocale("en");
    const english = render();
    expect(english).toContain("Retry data quality profile");
    expect(english).toContain("The active dataset is unchanged.");
    setCurrentLocale("ko");
    expect(render()).toContain("데이터 품질 점검 다시 불러오기");
    expect(render()).toContain("dataset_profile_failed");
  });

  it("renders no error for success and exposes a disabled retry while busy", () => {
    expect(renderToStaticMarkup(<DatasetRequestError kind="preview" error={null} onRetry={vi.fn()} />)).toBe("");
    expect(renderToStaticMarkup(<DatasetRequestError kind="preview" error="rows_preview_failed" busy onRetry={vi.fn()} />)).toContain("disabled");
  });

  it("accepts a stable code but never leaks arbitrary message or user values", () => {
    const literal = "\uE000user label\uE001 private cell";
    expect(datasetRequestErrorCode({ code: "dataset_version_not_found", message: literal }, "fallback")).toBe("dataset_version_not_found");
    expect(datasetRequestErrorCode(new Error(literal), "fallback")).toBe("fallback");
    expect(datasetRequestErrorCode({ code: literal }, "fallback")).toBe("fallback");
  });
});
