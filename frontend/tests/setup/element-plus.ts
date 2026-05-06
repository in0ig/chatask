import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// Create a function to register Element Plus in test environment
export function registerElementPlusForTests(app: any) {
  app.use(ElementPlus)
  
  // Register all Element Plus icons
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }
}

// Export a function to get a test app with Element Plus registered
export function createTestApp() {
  const app = createApp({})
  registerElementPlusForTests(app)
  return app
}