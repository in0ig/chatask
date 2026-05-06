import { defineConfig } from 'vitest/config'
import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          // Don't treat Element Plus components as custom elements in tests
          // isCustomElement: (tag) => tag.startsWith('el-'),
          // Enable proper handling of Vue 3.4 template compilation
          bindingMetadata: {},
          whitespace: 'condense'
        }
      }
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.{test,spec}.{js,ts,jsx,tsx}'],
    exclude: ['node_modules', 'dist', 'src/main.ts'],
    coverage: {
      provider: 'istanbul',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage',
    },
    globals: true,
    restoreMocks: true,
    setupFiles: ['./tests/setup/global-mocks.ts', './tests/setup/mock-element-plus.ts'],
    // Run tests in single thread to avoid serialization issues
    singleThread: true,
  },
})