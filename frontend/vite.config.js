import path from "path";
import { fileURLToPath } from "url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Dev server pinned to 5173 to match the backend's CORS_ALLOWED_ORIGINS
// default (http://localhost:5173, http://127.0.0.1:5173 -- see
// backend/.env.example and app/core/config.py).
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
  },
});
