import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './'：打包後可掛在任何子路徑（例如 https://dc-tools.cc/booking/）
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { outDir: '../server/static', emptyOutDir: true },
  server: {
    proxy: {
      '/api': 'http://localhost:8100',
      '/uploads': 'http://localhost:8100',
    },
  },
})
