/**
 * 语言状态管理 Store
 * 管理 UI 语言切换，支持 zh-CN 和 en-US
 */
import { defineStore } from 'pinia'
import i18n from '@/plugins/i18n'

// 支持的 locale 类型
export type SupportedLocale = 'zh-CN' | 'en-US'

// localStorage 存储 key
const LOCALE_STORAGE_KEY = 'chatbi_locale'

// 从 localStorage 读取已保存的语言偏好
function getStoredLocale(): SupportedLocale {
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (stored === 'zh-CN' || stored === 'en-US') {
    return stored
  }
  return 'zh-CN'
}

interface LocaleState {
  locale: SupportedLocale
}

export const useLocaleStore = defineStore('locale', {
  state: (): LocaleState => ({
    // 初始化时从 localStorage 读取，默认 zh-CN
    locale: getStoredLocale(),
  }),

  getters: {
    // 当前是否为英文
    isEnglish(state): boolean {
      return state.locale === 'en-US'
    },
    // 用于按钮显示的语言标识
    localeLabel(state): string {
      return state.locale === 'en-US' ? 'EN' : '中'
    },
  },

  actions: {
    /**
     * 设置语言
     * @param locale 目标语言
     */
    setLocale(locale: SupportedLocale) {
      this.locale = locale
      localStorage.setItem(LOCALE_STORAGE_KEY, locale)
      // 同步更新 vue-i18n 的全局 locale，触发 UI 重新渲染
      i18n.global.locale.value = locale
    },

    /**
     * 在 zh-CN 和 en-US 之间切换
     */
    toggleLocale() {
      const next: SupportedLocale = this.locale === 'zh-CN' ? 'en-US' : 'zh-CN'
      this.setLocale(next)
    },
  },
})
