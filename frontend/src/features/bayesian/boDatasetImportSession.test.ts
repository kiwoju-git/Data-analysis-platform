import { describe, expect, it } from "vitest";
import { createDatasetImportSession } from "./boDatasetImportSession";
import type { DatasetImportCreateRequest } from "../../api/types/boDatasetImport";

describe("dataset import request ownership", () => {
  it("invalidates old success, error and finally on editing/source change", () => {
    const session = createDatasetImportSession();
    const first = session.begin();
    session.invalidate();
    const second = session.begin();
    expect(session.current(first)).toBe(false);
    expect(session.current(second)).toBe(true);
    session.invalidate();
    expect(session.current(second)).toBe(false);
  });
  it("retries only the exact frozen create payload and clears it on edit", () => {
    const session = createDatasetImportSession();
    const body = { request_id: "one", expected_preflight_sha256: "hash", name: "original" } as DatasetImportCreateRequest;
    session.remember(body);
    body.name = "changed";
    expect(session.retry()?.name).toBe("original");
    expect(session.retry()?.request_id).toBe("one");
    session.invalidate();
    expect(session.retry()).toBeNull();
  });
});
