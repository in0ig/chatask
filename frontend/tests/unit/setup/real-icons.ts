import { createApp } from 'vue'
import { 
  Document, 
  Upload, 
  Plus, 
  Setting 
} from '@element-plus/icons-vue'

// Create a mock app to register components
const app = createApp({})

// Register all Element Plus icons as global components
app.component('Document', Document)
app.component('Upload', Upload)
app.component('Plus', Plus)
app.component('Setting', Setting)

// Export the app for use in tests
export { app }