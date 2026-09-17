import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API base is read from src/api.js (defaults to http://localhost:8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
