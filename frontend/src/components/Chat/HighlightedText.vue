<template>
  <span v-html="highlightedContent"></span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

// Props
const props = defineProps<{
  content: string
}>()

const { locale } = useI18n()

/**
 * 将大数字格式化为简短形式：154043 → 154K，1200000 → 1.2M
 * 小于 10000 的数字保持原样（HighlightedText 内数字格式与 SmartChart 一致可后续再统一 locale）
 */
const formatNumber = (numStr: string): string => {
  const num = parseFloat(numStr.replace(/,/g, ''))
  if (isNaN(num)) return numStr
  const abs = Math.abs(num)
  const sign = num < 0 ? '-' : ''
  if (abs >= 1_000_000) {
    const val = abs / 1_000_000
    return sign + (val % 1 === 0 ? val : parseFloat(val.toFixed(1))) + 'M'
  }
  if (abs >= 10_000) {
    const val = abs / 1_000
    return sign + (val % 1 === 0 ? val : parseFloat(val.toFixed(1))) + 'K'
  }
  return numStr
}

/** 当界面为中文时，将报告中的英文段落标题替换为中文（兜底：后端已返回英文时仍能显示中文标题） */
function localizeReportHeaders(text: string, currentLocale: string): string {
  if (!currentLocale || !currentLocale.startsWith('zh')) return text
  return text
    .replace(/\*\*①\s*Executive Summary\s*\*\*/gi, '**① 执行摘要**')
    .replace(/\*\*②\s*Key Findings\s*\*\*/gi, '**② 关键发现**')
    .replace(/\*\*③\s*Data Insight\s*\*\*/gi, '**③ 数据洞察**')
    .replace(/(^|\n)\s*①\s*Executive Summary\s*($|\n)/gi, '$1① 执行摘要$2')
    .replace(/(^|\n)\s*②\s*Key Findings\s*($|\n)/gi, '$1② 关键发现$2')
    .replace(/(^|\n)\s*③\s*Data Insight\s*($|\n)/gi, '$1③ 数据洞察$2')
}

// 应用高亮规则
const highlightedContent = computed(() => {
  const loc = typeof locale === 'string' ? locale : (locale as any)?.value ?? 'zh-CN'
  let result = localizeReportHeaders(props.content, loc)

  // 1. 解析模型输出的 <num>数字</num> 标记（红色），并格式化大数字
  result = result.replace(/<num>(.*?)<\/num>/g, (_, inner) => {
    const formatted = formatNumber(inner)
    return `<strong class="highlight-number">${formatted}</strong>`
  })

  // 2. 解析模型输出的 <text>文本</text> 标记（蓝色）
  result = result.replace(/<text>(.*?)<\/text>/g, '<strong class="highlight-text">$1</strong>')

  // 3. 渲染三段式标题：**① 执行摘要** / **② 关键发现** / **③ 数据洞察**（或英文）
  result = result.replace(/\*\*([^*\n]+)\*\*/g, '<span class="section-title">$1</span>')

  // 4. 渲染 Key Findings 条目：• 开头的行
  result = result.replace(/^•\s*(.+)$/gm, '<span class="finding-item">• $1</span>')

  // 5. 兜底：若模型把纠偏说明接在句尾，强制在“说明/Note”前换行
  result = result
    .replace(/([。！？])\s*(说明：)/g, '$1\n$2')
    .replace(/([.!?])\s*(Note:)/g, '$1\n$2')

  // 6. 处理换行
  result = result.replace(/\n/g, '<br>')

  return result
})
</script>

<style scoped>
/* 数字高亮 - 红色 */
:deep(.highlight-number) {
  color: #ff4d4f;
  font-weight: 600;
}

/* 文本高亮 - 蓝色 */
:deep(.highlight-text) {
  color: #1154cc;
  font-weight: 600;
}

/* 三段式标题：① Executive Summary 等 */
:deep(.section-title) {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #1a1a1a;
  margin-top: 14px;
  margin-bottom: 4px;
  letter-spacing: 0.01em;
}

:deep(.section-title:first-child) {
  margin-top: 0;
}

/* Key Findings 条目 */
:deep(.finding-item) {
  display: block;
  padding-left: 4px;
  line-height: 1.7;
  color: #333;
}
</style>
