import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173, // 默认端口
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // 本地开发时后端服务器地址
        changeOrigin: true,
        ws: true  // 启用WebSocket代理
      }
    }
  },
})
