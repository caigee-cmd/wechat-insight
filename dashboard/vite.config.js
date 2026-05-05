import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const isSingleFileExport = process.env.WECHAT_INSIGHT_EXPORT_SINGLE === "1";
const exportOutDir = process.env.WECHAT_INSIGHT_EXPORT_OUT_DIR;

export default defineConfig({
  base: isSingleFileExport ? "./" : "/",
  plugins: [react()],
  build: {
    ...(exportOutDir ? { outDir: exportOutDir } : {}),
    emptyOutDir: true,
    cssCodeSplit: !isSingleFileExport,
    rollupOptions: isSingleFileExport
      ? {
          output: {
            inlineDynamicImports: true,
          },
        }
      : undefined,
  },
  server: {
    host: "127.0.0.1",
    port: 4173,
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
  },
});
