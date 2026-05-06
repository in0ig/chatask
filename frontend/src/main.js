import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { registerElementPlus } from './plugins/element-plus.ts'
import i18n from './plugins/i18n.ts'
import './styles/element-plus-theme.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)
registerElementPlus(app)
app.mount('#app')
