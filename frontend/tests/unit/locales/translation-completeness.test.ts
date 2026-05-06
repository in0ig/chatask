/**
 * 翻译 key 完整性属性测试
 * Feature: i18n-language-switch
 * Property 3: Translation key completeness
 * Validates: Requirements 2.1
 *
 * For any translation key that exists in zh-CN, the same key must exist in en-US, and vice versa.
 */
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import zhCN from '@/locales/zh-CN'
import enUS from '@/locales/en-US'

/**
 * 递归提取对象中所有叶子节点的 key 路径
 * 例如 { a: { b: 'val' } } → ['a.b']
 */
function extractKeys(obj: Record<string, any>, prefix = ''): string[] {
  const keys: string[] = []
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key
    if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
      keys.push(...extractKeys(obj[key], fullKey))
    } else {
      keys.push(fullKey)
    }
  }
  return keys
}

const zhKeys = extractKeys(zhCN)
const enKeys = extractKeys(enUS)
const zhKeySet = new Set(zhKeys)
const enKeySet = new Set(enKeys)

describe('Translation key completeness - Property 3', () => {
  // Feature: i18n-language-switch, Property 3: Translation key completeness
  it('Property 3: every zh-CN key exists in en-US', () => {
    // For any key in zh-CN, it must also exist in en-US
    fc.assert(
      fc.property(fc.constantFrom(...zhKeys), (key) => {
        expect(enKeySet.has(key), `Key "${key}" exists in zh-CN but is missing from en-US`).toBe(true)
      }),
      { numRuns: Math.min(zhKeys.length, 200) }
    )
  })

  it('Property 3: every en-US key exists in zh-CN', () => {
    // For any key in en-US, it must also exist in zh-CN
    fc.assert(
      fc.property(fc.constantFrom(...enKeys), (key) => {
        expect(zhKeySet.has(key), `Key "${key}" exists in en-US but is missing from zh-CN`).toBe(true)
      }),
      { numRuns: Math.min(enKeys.length, 200) }
    )
  })

  it('Property 3: zh-CN and en-US have the same number of translation keys', () => {
    expect(zhKeys.length).toBe(enKeys.length)
  })

  it('Property 3: all zh-CN values are non-empty strings', () => {
    fc.assert(
      fc.property(fc.constantFrom(...zhKeys), (key) => {
        const parts = key.split('.')
        let val: any = zhCN
        for (const part of parts) val = val[part]
        expect(typeof val).toBe('string')
        expect((val as string).length).toBeGreaterThan(0)
      }),
      { numRuns: Math.min(zhKeys.length, 200) }
    )
  })

  it('Property 3: all en-US values are non-empty strings', () => {
    fc.assert(
      fc.property(fc.constantFrom(...enKeys), (key) => {
        const parts = key.split('.')
        let val: any = enUS
        for (const part of parts) val = val[part]
        expect(typeof val).toBe('string')
        expect((val as string).length).toBeGreaterThan(0)
      }),
      { numRuns: Math.min(enKeys.length, 200) }
    )
  })
})
