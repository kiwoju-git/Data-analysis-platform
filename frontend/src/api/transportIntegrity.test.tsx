import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsx } from "../i18n/jsx-runtime";
import { setCurrentLocale } from "../i18n/store";
import { apiRequestError, fetchApi } from "./client";

const userText = '한글 English "quoted" \\ path\n\uE000language.selector\uE001';

describe("API transport preserves user data", () => {
  afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("en"); });

  it.each(["en", "ko"] as const)("does not translate serialized JSON in %s", async (locale) => {
    setCurrentLocale(locale);
    const payload = { name: userText, code: userText, message: userText, warnings: [{ code: "api_connection_failed", message: userText }] };
    const body = JSON.stringify(payload);
    let received: unknown;
    const serverResponse = new Response(body, { headers: { "Content-Type": "application/json" } });
    const originalJson = Object.getOwnPropertyDescriptor(Response.prototype, "json")?.value as unknown;
    vi.stubGlobal("fetch", vi.fn((_input: unknown, init: RequestInit) => {
      expect(init.body).toBe(body);
      expect(new Headers(init.headers).get("Accept-Language")).toBe(locale);
      if (typeof init.body !== "string") throw new Error("Expected unchanged JSON string");
      received = JSON.parse(init.body);
      return Promise.resolve(serverResponse);
    }));
    const response = await fetchApi("/api/fixture", { method: "POST", body });
    expect(received).toEqual(payload);
    expect(response).toBe(serverResponse);
    expect(Object.prototype.hasOwnProperty.call(response, "json")).toBe(false);
    expect(Object.getOwnPropertyDescriptor(Response.prototype, "json")?.value).toBe(originalJson);
    expect(await response.json()).toEqual(payload);
  });

  it("preserves multipart, Blob and buffer identity without reading or rewriting them", async () => {
    const multipart = new FormData();
    multipart.append("file", new File([userText], "한글.csv", { type: "text/csv" }));
    const bodies = [multipart, new Blob([userText]), new TextEncoder().encode(userText).buffer];
    for (const body of bodies) {
      const fetch = vi.fn((_input: unknown, init: RequestInit) => {
        expect(init.body).toBe(body);
        expect(new Headers(init.headers).has("Content-Type")).toBe(false);
        return Promise.resolve(new Response("{}"));
      });
      vi.stubGlobal("fetch", fetch);
      await fetchApi("/api/fixture", { method: "POST", body });
      expect(fetch).toHaveBeenCalledTimes(1);
    }
  });

  it("keeps Request headers while adding the locale", async () => {
    const request = new Request("http://localhost/api/fixture", { headers: { "X-Fixture": "preserved" } });
    vi.stubGlobal("fetch", vi.fn((_input: unknown, init: RequestInit) => {
      expect(new Headers(init.headers).get("X-Fixture")).toBe("preserved");
      return Promise.resolve(new Response("{}"));
    }));
    await fetchApi(request);
  });

  it("keeps error code and original backend message independent of locale", async () => {
    const error = { code: "fixture_error", message: userText, correlation_id: "fixture-correlation" };
    const response = new Response(JSON.stringify({ error }), { status: 409 });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(response)));
    const parsed = await apiRequestError(await fetchApi("/api/fixture"), "fallback");
    expect(parsed).toMatchObject({ status: 409, code: error.code, message: error.code, backendMessage: userText, correlationId: error.correlation_id });
    setCurrentLocale("ko");
    expect(parsed.backendMessage).toBe(userText);
  });

  it("does not interpret private-use characters in rendered user text or input values", () => {
    const html = renderToStaticMarkup(jsx("div", {
      children: [jsx("span", { children: userText }, "label"), jsx("input", { value: userText, readOnly: true }, "value")],
    }));
    expect(html.match(/\uE000language.selector\uE001/gu)).toHaveLength(2);
    expect(html).not.toContain("Language");
  });
});
