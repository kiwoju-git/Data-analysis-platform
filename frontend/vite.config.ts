import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 8600,
  },
  preview: {
    host: "127.0.0.1",
    port: 8600,
  },
  test: {
    environment: "node",
    globals: true,
  },
});
