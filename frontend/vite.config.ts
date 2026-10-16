import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server on :5173. In production the API URL comes from VITE_API_BASE_URL (set in Vercel).
export default defineConfig({ plugins: [react()], server: { port: 5173 }, build: { outDir: "dist", sourcemap: false } });
