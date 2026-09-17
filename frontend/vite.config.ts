import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

import localizationCatalog from "./src/i18n/catalog.generated.json";
import { createLocalizationPlugin } from "./src/i18n/vitePlugin";
import { devNetworkGuard, loopbackApiTarget } from "./devNetwork";

const i18nDirectory = decodeURIComponent(new URL("./src/i18n", import.meta.url).pathname).replace(
  /^\/([A-Za-z]:)/u,
  "$1",
);

export default defineConfig(({ mode }) => ({
  resolve: {
    alias: {
      "statistical-twin-i18n": i18nDirectory,
    },
  },
  plugins: [
    devNetworkGuard(),
    ...(mode === "test" ? [] : [createLocalizationPlugin(localizationCatalog.sourceToKey)]),
    react(),
  ],
  server: {
    host: mode === "test" ? "127.0.0.1" : "0.0.0.0",
    port: 8600,
    strictPort: true,
    cors: false,
    proxy: { "/api": { target: loopbackApiTarget(process.env.DATALAB_DEV_API_TARGET) } },
  },
  preview: {
    host: "127.0.0.1",
    port: 8600,
  },
  test: {
    environment: "node",
    globals: true,
    setupFiles: ["./src/testSetup.ts"],
  },
}));
