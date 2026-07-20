import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    // Optional convenience proxy: lets the frontend call "/api/..." during
    // dev without hardcoding http://localhost:8000 everywhere. client.ts
    // still defaults to the full backend URL via VITE_API_BASE_URL, so
    // this proxy is a fallback, not a requirement.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
