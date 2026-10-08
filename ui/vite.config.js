import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Relative, so the build works at /results/ on any host, including a sub-path one.
  base: "./",
  plugins: [react()],
  build: {
    sourcemap: false,
  },
});
