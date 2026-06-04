import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 开发服务器默认 5173 端口；预留 /api 代理到后端(FastAPI 等)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
