import { createApp } from 'vue'
import { 
  MockElSwitch, 
  MockElTree, 
  MockElOption, 
  MockElIcon, 
  MockElCheckbox,
  MockChartLine,
  MockDocument,
  MockSetting
} from '../../unit/mocks/ElementPlusMocks'

// Create a mock app to register components
const app = createApp({})

// Register all Element Plus mock components
app.component('ElSwitch', MockElSwitch)
app.component('ElTree', MockElTree)
app.component('ElOption', MockElOption)
app.component('ElIcon', MockElIcon)
app.component('ElCheckbox', MockElCheckbox)

// Register all icon components
app.component('ChartLine', MockChartLine)
app.component('Document', MockDocument)
app.component('Setting', MockSetting)

// Export the app for use in tests
export { app }