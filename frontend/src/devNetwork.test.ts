import { afterEach, describe, expect, it, vi } from "vitest";
import { devRequestAllowed, loopbackApiTarget } from "../devNetwork";
import { getApiBaseUrl } from "./api/client";

afterEach(() => vi.unstubAllEnvs());

describe("LAN development boundary", () => {
  const hosts = new Set(["localhost", "127.0.0.1", "192.168.10.4"]);
  it.each(["localhost:8600", "127.0.0.1:8600", "192.168.10.4:8600"])("accepts same-origin reads and mutations at %s", (host) => {
    expect(devRequestAllowed({ method: "GET", headers: { host } }, hosts)).toBe(true);
    expect(devRequestAllowed({ method: "POST", headers: { host, origin: `http://${host}` } }, hosts)).toBe(true);
  });
  it.each([
    { host: "attacker.example:8600" },
    { host: "192.168.10.5:8600" },
    { host: "localhost:8600", origin: "http://attacker.example" },
    { host: "localhost:8600", origin: "null" },
    { host: "localhost:8600", origin: "http://localhost:9999" },
    { host: "localhost:8600", "sec-fetch-site": "cross-site" },
    { host: "attacker@localhost:8600" },
    { host: "localhost:8600/path" },
    {},
  ])("rejects untrusted Host/Origin %j", (headers) => {
    expect(devRequestAllowed({ method: "GET", headers }, hosts)).toBe(false);
  });
  it.each(["POST", "PUT", "PATCH", "DELETE"])("requires an origin for %s", (method) => {
    expect(devRequestAllowed({ method, headers: { host: "localhost:8600" } }, hosts)).toBe(false);
  });
  it("does not become an arbitrary proxy or expose a client-side backend address", () => {
    expect(loopbackApiTarget()).toBe("http://127.0.0.1:8000");
    expect(loopbackApiTarget("http://127.0.0.1:8011")).toBe("http://127.0.0.1:8011");
    for (const value of ["http://example.com", "http://192.168.0.1", "https://127.0.0.1", "http://user@127.0.0.1", "http://127.0.0.1/path", "http://127.0.0.1?x=1"]) {
      expect(() => loopbackApiTarget(value)).toThrow();
    }
    vi.stubEnv("VITE_API_BASE_URL", "");
    expect(getApiBaseUrl()).toBe("");
    vi.stubEnv("VITE_API_BASE_URL", "/");
    expect(getApiBaseUrl()).toBe("");
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:8011/");
    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8011");
  });
});
