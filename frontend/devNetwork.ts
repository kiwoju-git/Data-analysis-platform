import { networkInterfaces } from "node:os";
import type { IncomingMessage } from "node:http";
import type { Plugin, ViteDevServer } from "vite";

// Numeric interface addresses only: never trust arbitrary Host/forwarded headers.
export function localDevHosts(): Set<string> {
  const hosts = new Set(["localhost", "127.0.0.1", "[::1]"]);
  for (const addresses of Object.values(networkInterfaces())) {
    for (const address of addresses ?? []) hosts.add(address.address);
  }
  return hosts;
}

export function devRequestAllowed(
  request: Pick<IncomingMessage, "headers" | "method">,
  hosts: ReadonlySet<string>,
): boolean {
  const host = request.headers.host;
  if (!host || /[\s/@\\?#]/u.test(host)) return false;
  try {
    const expected = new URL(`http://${host}`);
    if (!hosts.has(expected.hostname)) return false;
    const origin = request.headers.origin;
    if (origin !== undefined && origin !== expected.origin) return false;
    if (request.headers["sec-fetch-site"] === "cross-site") return false;
    const readOnly = ["GET", "HEAD", "OPTIONS"].includes(request.method ?? "GET");
    return readOnly || origin === expected.origin;
  } catch {
    return false;
  }
}

export function loopbackApiTarget(value = "http://127.0.0.1:8000"): string {
  const target = new URL(value);
  if (target.protocol !== "http:" || target.hostname !== "127.0.0.1" ||
      target.username || target.password || target.pathname !== "/" || target.search || target.hash) {
    throw new Error("DATALAB_DEV_API_TARGET must be an HTTP loopback origin.");
  }
  return target.origin;
}

export function devNetworkGuard(): Plugin {
  const install = (server: Pick<ViteDevServer, "middlewares">) => {
    const hosts = localDevHosts();
    server.middlewares.use((request, response, next) => {
      if (!devRequestAllowed(request, hosts)) {
        response.statusCode = 403;
        response.end("dev_origin_not_allowed");
        return;
      }
      next();
    });
  };
  return {
    name: "datalab-dev-network-guard",
    configureServer(server) {
      install(server);
      if (server.config.server.host === "0.0.0.0") {
        server.config.logger.warn("Trusted LAN dev server: shared workspace, no login/RBAC/TLS. Restrict firewall access; never publish to the Internet.");
      }
    },
    configurePreviewServer: install,
  };
}
