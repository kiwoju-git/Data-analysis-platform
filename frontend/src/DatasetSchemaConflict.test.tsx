import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { DatasetSchemaConflict } from "./DatasetSchemaConflict";
import { setCurrentLocale } from "./i18n/store";
import type { SchemaConflictState } from "./datasetSchemaDraft";

afterEach(() => setCurrentLocale("ko"));

describe("schema conflict recovery presentation", () => {
  it.each(["ko", "en"] as const)("renders explicit actions and raw user text in %s", (locale) => {
    setCurrentLocale(locale);
    const literal = "<b>\uE000user-name\uE001";
    const conflict: SchemaConflictState = { status: "ready", baseHash: "a".repeat(64), latest: null, errorCode: null };
    const html = renderToStaticMarkup(<DatasetSchemaConflict schemaConflict={conflict} schemaComparison={[{
      columnId: "column-id", field: "display_name", base: "old", draft: literal,
      latest: "remote", localChanged: true, remoteChanged: true, conflicting: true,
    }]} />);
    expect(html).toContain('data-conflict-state="ready"');
    for (const action of ["apply", "discard", "edit"]) expect(html).toContain(`data-schema-conflict-action="${action}"`);
    expect(html).toContain("&lt;b&gt;\uE000user-name\uE001");
    expect(html).toContain(locale === "en" ? "Original base" : "최초 기준값");
    expect(html).toContain(locale === "en" ? "Save is still required" : "스키마 저장을 눌러야");
  });

  it("shows retry only after a failed read and marks staged changes as unsaved", () => {
    setCurrentLocale("en");
    const failed = renderToStaticMarkup(<DatasetSchemaConflict schemaConflict={{ status: "failed", baseHash: "a".repeat(64), latest: null, errorCode: "network_error" }} />);
    expect(failed).toContain('data-schema-conflict-action="retry"');
    expect(failed).not.toContain('data-schema-conflict-action="apply"');
    const loading = renderToStaticMarkup(<DatasetSchemaConflict schemaConflict={{ status: "loading", baseHash: "a".repeat(64), latest: null, errorCode: null }} />);
    expect(loading).not.toContain('data-schema-conflict-action="retry"');
    expect(loading).toContain("Loading the latest schema");
    expect(renderToStaticMarkup(<DatasetSchemaConflict schemaStaged />)).toContain("Save schema to commit");
  });
});
