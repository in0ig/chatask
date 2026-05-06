/**
 * Locale Store 属性测试
 * Feature: i18n-language-switch
 * Property 1: Locale toggle is a round trip
 * Property 2: Locale persistence round trip
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import * as fc from 'fast-check'
import { useLocaleStore, type SupportedLocale } from '@/store/modules/locale'

// 支持的 locale 列表
const SUPPORTED_LOCALES: SupportedLocale[] = ['zh-CN', 'en-US']

// fast-check arbitrary：从支持的 locale 中随机选取
const localeArb = fc.constantFrom(...SUPPORTED_LOCALES)

describe('Locale Store', () => {
  beforeEach(() => {
    // 每次测试前重置 Pinia 和 localStorage
    setActivePinia(createPinia())
    localStorage.clear()
  })

  // Feature: i18n-language-switch, Property 1: Locale toggle is a round trip
  it('Property 1: toggleLocale() twice returns to original locale', () => {
    fc.assert(
      fc.property(localeArb, (initialLocale) => {
        // 重置 store 和 localStorage
        localStorage.clear()
        setActivePinia(createPinia())

        // 设置初始 locale
        const store = useLocaleStore()
        store.setLocale(initialLocale)
        const before = store.locale

        // 切换两次
        store.toggleLocale()
        store.toggleLocale()

        // 应该回到原始值
        expect(store.locale).toBe(before)
      }),
      { numRuns: 100 }
    )
  })

  // Feature: i18n-language-switch, Property 2: Locale persistence round trip
  it('Property 2: locale set via setLocale() is restored from localStorage on new store init', () => {
    fc.assert(
      fc.property(localeArb, (targetLocale) => {
        // 重置
        localStorage.clear()
        setActivePinia(createPinia())

        // 设置 locale，写入 localStorage
        const store = useLocaleStore()
        store.setLocale(targetLocale)

        // 模拟新实例：重新创建 Pinia（localStorage 仍保留）
        setActivePinia(createPinia())
        const newStore = useLocaleStore()

        // 新 store 应该从 localStorage 恢复相同的 locale
        expect(newStore.locale).toBe(targetLocale)
      }),
      { numRuns: 100 }
    )
  })

  // 单元测试：验证 toggleLocale 在两种语言间切换
  it('toggleLocale switches between zh-CN and en-US', () => {
    const store = useLocaleStore()
    store.setLocale('zh-CN')
    store.toggleLocale()
    expect(store.locale).toBe('en-US')
    store.toggleLocale()
    expect(store.locale).toBe('zh-CN')
  })

  // 单元测试：无效 localStorage 值时默认 zh-CN
  it('defaults to zh-CN when localStorage has invalid value', () => {
    localStorage.setItem('chatbi_locale', 'invalid-locale')
    setActivePinia(createPinia())
    const store = useLocaleStore()
    expect(store.locale).toBe('zh-CN')
  })

  // 单元测试：localeLabel getter
  it('localeLabel returns EN for en-US and 中 for zh-CN', () => {
    const store = useLocaleStore()
    store.setLocale('en-US')
    expect(store.localeLabel).toBe('EN')
    store.setLocale('zh-CN')
    expect(store.localeLabel).toBe('中')
  })
})
