import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  resolve: { preserveSymlinks: true },
  server: {
    port: 5173,
    fs: { strict: false },
    // Lets a single ngrok tunnel (or any host) serve the frontend AND reach
    // the backend same-origin — no CORS, no second tunnel needed for phone
    // testing. Only active when VITE_API_BASE_URL is unset/empty.
    proxy: {
      '/api': { target: 'http://localhost:8200', changeOrigin: true, ws: true },
    },
    allowedHosts: true,
  },
});
