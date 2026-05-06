import { createI18n } from 'vue-i18n'
import zhCN from '../locales/zh-CN'
import enUS from '../locales/en-US'

// 从 localStorage 读取已保存的语言偏好，默认使用 zh-CN
const savedLocale = localStorage.getItem('chatbi_locale')
const defaultLocale = (savedLocale === 'zh-CN' || savedLocale === 'en-US') ? savedLocale : 'zh-CN'

const i18n = createI18n({
  legacy: false,          // 使用 Composition API 模式
  locale: defaultLocale,
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export default i18n
