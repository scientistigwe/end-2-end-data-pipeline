import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import tailwindcss from 'tailwindcss';
import autoprefixer from 'autoprefixer';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  css: {
    postcss: {
      plugins: [
        tailwindcss,
        autoprefixer,
      ],
    },
  },
  server: {
    port: 5173, // Changed to Vite's default port
    strictPort: false, // Will try another port if 5173 is in use
    host: true, // Expose to all network interfaces
    open: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});