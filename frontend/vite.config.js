import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api is proxied to Django so the browser never deals with CORS in dev.
// Port 8001 (not Django's default 8000) because 8000 is often taken by another project.
// Run the backend with: python manage.py runserver 8001
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": process.env.API_TARGET || "http://127.0.0.1:8001" } },
});
