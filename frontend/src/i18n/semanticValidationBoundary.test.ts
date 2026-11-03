import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { assertSemanticValidationBoundary } from "../../../scripts/check_frontend_localization.mjs";
import catalog from "./catalog.generated.json";

const source = readFileSync(new URL("../capabilitySpecValidation.ts", import.meta.url), "utf8");

describe("semantic validation localization gate", () => {
  it("accepts the live complete error-code contract", () => {
    expect(() => assertSemanticValidationBoundary(source, catalog)).not.toThrow();
  });
  it("rejects registered-but-untranslated helper text", () => {
    const oldBoundary = source.replace('messageKey: "capability.validation.numeric"', 'message: "등록된 한국어 오류"');
    expect(() => assertSemanticValidationBoundary(oldBoundary, catalog)).toThrow("code/messageKey");
  });
  it("rejects an unknown semantic key and a removed error branch", () => {
    expect(() => assertSemanticValidationBoundary(source.split("capability.validation.numeric").join("capability.validation.missing"), catalog)).toThrow("unregistered");
    expect(() => assertSemanticValidationBoundary(source.replace('kind: "error", code: "invalid_number"', 'kind: "ready", code: "invalid_number"'), catalog)).toThrow("three semantic error branches");
  });
});
