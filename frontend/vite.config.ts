import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // 关键配置：打包后网页全自动生成并丢到后端的 static 静态文件夹供挂载
    outDir: '../backend/static',
    emptyOutDir: true
  }
})
