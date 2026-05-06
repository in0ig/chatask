import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'happy-dom',
    include: ['**/PermissionSection.test.ts'],
    exclude: ['node_modules', 'dist', 'src/main.ts'],
    coverage: {
      provider: 'istanbul',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage',
    },
    globals: true,
    restoreMocks: true,
    setupFiles: ['./src/plugins/element-plus.ts'],
    // Use a minimal configuration
    server: {
      port: 5173,
      hmr: false
    }
  },
})