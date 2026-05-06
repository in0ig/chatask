import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  // 加载当前模式的环境变量
  const env = loadEnv(mode, process.cwd())
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8000'

  return {
    plugins: [
      vue({
        include: [/\.vue$/, /\.md$/],
        template: {
          compilerOptions: {
            // 只对真正需要的自定义元素进行标记
            isCustomElement: (tag) => [
              'search',
              'setting',
              'bell',
              'document',
              'chart-line',
              'language',
              'el-icon'
            ].includes(tag)
          }
        }
      })
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    server: {
      host: true,
      port: 5173,
      // Vite 7 仅接受 boolean | string[]；字符串 'all' 无效会被忽略，内网/随机主机名会报 Blocked request
      allowedHosts: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          ws: true // HTTP + WebSocket（/api/stream/ws）一并转发到后端
        }
      }
    },
    preview: {
      host: true,
      port: 4173,
      allowedHosts: true
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets'
    }
  }
})
