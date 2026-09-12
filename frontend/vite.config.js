import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward /health and all /api/* requests to the FastAPI backend.
      // The browser sends requests to Vite (same origin) → Vite proxies to backend.
      // This avoids all CORS issues regardless of which port Vite starts on.
      '/health': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})
