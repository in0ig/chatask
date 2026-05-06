<template>
  <div class="smart-chart-container" ref="chartContainer">
    <!-- 图表推荐提示 -->
    <div class="chart-recommendation" v-if="chartRecommendation && showToolbar">
      <el-alert
        :title="`${$t('chart.recommendation')}${getChartTypeLabel(currentChartType)}`"
        type="info"
        :closable="false"
        show-icon
      >
        <template #default>
          {{ chartRecommendation }}
        </template>
      </el-alert>
    </div>

    <!-- 图表工具栏 -->
    <div class="chart-toolbar" v-if="showToolbar">
      <el-button-group>
        <el-button
          v-for="chartType in availableChartTypes"
          :key="chartType"
          :type="currentChartType === chartType ? 'primary' : 'default'"
          size="small"
          @click="changeChartType(chartType)"
        >
          {{ getChartTypeLabel(chartType) }}
        </el-button>
      </el-button-group>

      <div class="chart-actions">
        <el-dropdown @command="handleExport" v-if="exportable" trigger="click">
          <el-button link size="small">
            {{ $t('chart.toolbar.export') }} <el-icon><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="png">{{ $t('chart.export.png') }}</el-dropdown-item>
              <el-dropdown-item command="jpg">{{ $t('chart.export.jpg') }}</el-dropdown-item>
              <el-dropdown-item command="pdf">{{ $t('chart.export.pdf') }}</el-dropdown-item>
              <el-dropdown-item command="svg">{{ $t('chart.export.svg') }}</el-dropdown-item>
              <el-dropdown-item command="excel">{{ $t('chart.export.excel') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button link size="small" @click="showSaveDialog = true">
          {{ $t('chart.toolbar.saveConfig') }}
        </el-button>

        <el-button link size="small" @click="showShareDialog = true">
          {{ $t('chart.toolbar.share') }}
        </el-button>
      </div>
    </div>

    <!-- 图表容器 -->
    <div
      ref="chartElement"
      class="chart-element"
      :style="{ height: chartHeight }"
    ></div>

    <!-- 保存配置对话框 -->
    <el-dialog
      v-model="showSaveDialog"
      :title="$t('chart.saveDialog.title')"
      width="500px"
    >
      <el-form :model="saveForm" label-width="100px">
        <el-form-item :label="$t('chart.saveDialog.configName')">
          <el-input v-model="saveForm.name" :placeholder="$t('chart.saveDialog.configName')" />
        </el-form-item>
        <el-form-item :label="$t('chart.saveDialog.asTemplate')">
          <el-switch v-model="saveForm.asTemplate" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSaveConfig">{{ $t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 分享对话框 -->
    <el-dialog
      v-model="showShareDialog"
      :title="$t('chart.shareDialog.title')"
      width="600px"
    >
      <el-tabs v-model="shareTabActive">
        <el-tab-pane :label="$t('chart.shareDialog.shareLink')" name="link">
          <div class="share-content">
            <el-input
              v-model="shareLink"
              readonly
              :placeholder="$t('chart.shareDialog.shareLink')"
            >
              <template #append>
                <el-button @click="copyShareLink">{{ $t('chart.shareDialog.copy') }}</el-button>
              </template>
            </el-input>
            <div class="share-options">
              <el-form label-width="100px" size="small">
                <el-form-item :label="$t('chart.shareDialog.validity')">
                  <el-select v-model="shareOptions.expiresInDays">
                    <el-option :label="$t('chart.shareDialog.permanent')" :value="0" />
                    <el-option label="7天" :value="7" />
                    <el-option label="30天" :value="30" />
                    <el-option label="90天" :value="90" />
                  </el-select>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane :label="$t('chart.shareDialog.embedCode')" name="embed">
          <div class="share-content">
            <el-input
              v-model="embedCode"
              type="textarea"
              :rows="6"
              readonly
              :placeholder="$t('chart.shareDialog.embedCode')"
            />
            <el-button @click="copyEmbedCode" style="margin-top: 10px">
              {{ $t('chart.shareDialog.copy') }}
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="showShareDialog = false">{{ $t('common.close') }}</el-button>
        <el-button type="primary" @click="generateShare">{{ $t('chart.shareDialog.generate') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import type { ECharts, EChartsOption } from 'echarts'
import { ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { SmartChartProps, ChartType, ChartData, ExportFormat, ChartConfig } from '@/types/chart'
import { buildEChartsOption, formatPrimaryAxisValue } from '@/utils/buildEChartsOption'
import { ChartTypeSelector } from '@/utils/chartTypeSelector'
import { chartExportService } from '@/services/chartExportService'
import { chartConfigService } from '@/services/chartConfigService'
import { chartShareService } from '@/services/chartShareService'
import { chartInteractionService } from '@/services/chartInteractionService'
import { chartThemeService } from '@/services/chartThemeService'
import { chartAnimationService } from '@/services/chartAnimationService'
import { chartStreamingService } from '@/services/chartStreamingService'
import type { ContextMenuItem, DataPointSelection } from '@/services/chartInteractionService'
import type { StreamingConfig } from '@/services/chartStreamingService'

const props = withDefaults(defineProps<SmartChartProps>(), {
  type: 'auto',
  theme: 'light',
  responsive: true,
  exportable: true,
  options: () => ({})
})

// 定义事件：rendered 在图表首次渲染完成后触发
const emit = defineEmits<{
  rendered: []
}>()

// i18n（用于图表数值、轴标签等跟随语言）
const { t, locale } = useI18n()

const chartContainer = ref<HTMLElement>()
const chartElement = ref<HTMLElement>()
let chartInstance: ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const currentChartType = ref<ChartType>('bar')
const chartTypeSelector = new ChartTypeSelector()
const isLoadingChartType = ref(false)
const chartRecommendation = ref<string>('')

// 流式渲染状态
const isStreaming = ref(false)
const streamedData = ref<any[]>([])
const streamProgress = ref(0)
const chartId = `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

// 是否已完成首次渲染
let hasRendered = false

// 保存和分享相关状态
const showSaveDialog = ref(false)
const showShareDialog = ref(false)
const shareTabActive = ref('link')
const shareLink = ref('')
const embedCode = ref('')
const saveForm = ref({
  name: '',
  asTemplate: false
})
const shareOptions = ref({
  expiresInDays: 0
})

// 计算属性
const availableChartTypes = computed(() => {
  // 🔥 修复：始终返回基本的图表类型，不依赖数据分析
  // 让用户可以自由切换图表类型
  const basicTypes: ChartType[] = ['bar', 'line', 'pie', 'combo']
  
  // 如果有数据，尝试添加更多类型
  if (props.data && props.data.rows && props.data.rows.length > 0) {
    const types = chartTypeSelector.getAvailableTypes(props.data)
    // 合并基本类型和分析出的类型，去重
    const allTypes = [...new Set([...basicTypes, ...types])]
    return allTypes
  }
  
  return basicTypes
})

const chartHeight = computed(() => {
  return props.options?.height || (props.responsive ? '400px' : '300px')
})

const showToolbar = computed(() => {
  return props.options?.showToolbar !== false
})

// 监听数据变化
watch(() => props.data, async (newData, oldData) => {
  if (!newData) return

  // 检查是否需要流式渲染
  const shouldStream = chartStreamingService.shouldUseStreaming(newData.rows.length)
  
  if (shouldStream && props.options?.enableStreamingUpdate !== false) {
    // 流式渲染模式
    await renderChartStreaming(newData)
  } else {
    // 检测是否为增量更新
    const isIncremental = oldData && 
      newData.columns.length === oldData.columns.length &&
      newData.rows.length > oldData.rows.length
    
    if (isIncremental && props.options?.enableIncrementalUpdate) {
      // 增量更新模式
      await updateChartIncremental(newData, oldData)
    } else {
      // 完全更新模式
      if (props.type === 'auto') {
        await selectChartTypeWithAI(newData)
      }
      updateChart()
    }
  }
}, { deep: true })

watch(() => props.type, (newType) => {
  if (newType !== 'auto') {
    currentChartType.value = newType as ChartType
    chartRecommendation.value = ''
    updateChart()
  }
})

watch(() => props.theme, () => {
  if (chartInstance) {
    chartInstance.dispose()
    initChart()
  }
})

// 生命周期
onMounted(async () => {
  // 等待 DOM 渲染完成后再初始化，避免容器尺寸未稳定导致图表挤压
  await nextTick()
  initChart()
})

onUnmounted(() => {
  cleanup()
})

// 方法
async function initChart() {
  if (!chartElement.value) return

  // 注册自定义主题
  const themeConfig = chartThemeService.generateEChartsTheme(props.theme || 'light')
  echarts.registerTheme(props.theme || 'light', themeConfig)

  chartInstance = echarts.init(chartElement.value, props.theme)

  // 自动选择图表类型
  if (props.type === 'auto') {
    await selectChartTypeWithAI(props.data)
  } else {
    currentChartType.value = props.type as ChartType
  }

  updateChart()

  // 初始化后立即 resize，修复容器尺寸未稳定时的渲染问题
  chartInstance.resize()

  // 用 ResizeObserver 监听容器尺寸变化，确保图表始终正确填充容器
  if (chartContainer.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      chartInstance?.resize()
    })
    resizeObserver.observe(chartContainer.value)
  }

  // 集成交互服务
  if (chartInstance) {
    initInteractionFeatures(chartInstance)
  }

  // 响应式处理（window resize 兜底）
  if (props.responsive) {
    window.addEventListener('resize', handleResize)
  }
}

/**
 * 初始化交互功能
 */
function initInteractionFeatures(chart: ECharts) {
  // 启用上下文菜单
  if (props.options?.enableContextMenu) {
    const menuItems: ContextMenuItem[] = [
      {
        label: '导出为PNG',
        action: () => handleExport('png')
      },
      {
        label: '导出为Excel',
        action: () => handleExport('excel')
      },
      {
        label: '复制数据',
        action: (data: any) => {
          console.log('Copy data:', data)
          ElMessage.success('数据已复制')
        }
      }
    ]
    chartInteractionService.enableContextMenu(chart, menuItems)
  }

  // 启用数据点选择
  if (props.options?.enableDataPointSelection) {
    chartInteractionService.enableDataPointSelection(
      chart,
      (selections: DataPointSelection[]) => {
        console.log('Selected data points:', selections)
        ElMessage.info(`已选择 ${selections.length} 个数据点`)
      }
    )
  }

  // 启用钻取功能
  if (props.options?.enableDrillDown) {
    chartInteractionService.enableDrillDown(chart, {
      enabled: true,
      onDrillDown: (data: DataPointSelection) => {
        console.log('Drill down:', data)
        ElMessage.info(`钻取到: ${data.name}`)
      },
      onDrillUp: () => {
        console.log('Drill up')
        ElMessage.info('返回上一层')
      }
    })
  }

  // 启用图表联动
  if (props.options?.enableChartLinkage && props.options?.linkageGroup) {
    chartInteractionService.enableChartLinkage(chart, {
      group: props.options.linkageGroup,
      enabled: true
    })
  }
}

/**
 * 使用AI选择图表类型
 */
async function selectChartTypeWithAI(data: ChartData) {
  isLoadingChartType.value = true
  
  try {
    // 尝试使用AI选择
    const result = await chartTypeSelector.selectOptimalChartAsync(data)
    currentChartType.value = result.primary.type
    chartRecommendation.value = result.primary.reason
    
    console.log('AI Chart Selection:', {
      primary: result.primary,
      alternatives: result.alternatives,
      dataAnalysis: result.dataAnalysis
    })
  } catch (error) {
    console.warn('Failed to select chart type with AI, using fallback:', error)
    // 降级到规则引擎
    currentChartType.value = chartTypeSelector.selectOptimalChart(data)
    chartRecommendation.value = ''
  } finally {
    isLoadingChartType.value = false
  }
}

function updateChart() {
  if (!chartInstance) return

  let dataToRender = props.data
  
  // 检查是否为大数据量，需要优化
  if (chartStreamingService.isLargeDataset(props.data.rows.length)) {
    // 应用大数据量优化
    const option = generateChartOption(currentChartType.value, dataToRender)
    const optimized = chartStreamingService.optimizeForLargeDataset(
      option,
      props.data.rows.length
    )
    
    chartInstance.setOption(optimized, true)
    
    ElMessage.info({
      message: `检测到大数据量(${props.data.rows.length}条)，已启用性能优化`,
      duration: 2000
    })
    return
  }

  let option = generateChartOption(currentChartType.value, dataToRender)
  
  // 应用动画配置
  if (props.options?.animationPreset) {
    const animConfig = chartAnimationService.getAnimationConfig(props.options.animationPreset)
    option = chartAnimationService.applyAnimation(option, animConfig)
  } else if (props.options?.animationDuration || props.options?.animationEasing) {
    option = chartAnimationService.applyAnimation(option, {
      enabled: props.options?.animation !== false,
      duration: props.options?.animationDuration || 1000,
      easing: props.options?.animationEasing || 'cubicOut'
    })
  }

  chartInstance.setOption(option, true)
  
  // 首次渲染完成后触发 rendered 事件
  if (!hasRendered) {
    hasRendered = true
    // 等待 echarts 完成绘制（下一帧）
    requestAnimationFrame(() => emit('rendered'))
  }
}

/**
 * 增量更新图表数据
 */
async function updateChartIncremental(newData: ChartData, oldData: ChartData) {
  if (!chartInstance) return

  // 显示加载动画
  if (props.options?.showLoadingOnUpdate) {
    const loadingConfig = chartStreamingService.getLoadingAnimation()
    chartInstance.showLoading('default', loadingConfig)
  }

  // 计算新增的数据
  const newRows = newData.rows.slice(oldData.rows.length)
  
  // 使用增量更新服务
  const mergedRows = chartStreamingService.incrementalUpdate(
    chartId,
    newRows,
    streamedData.value.length > 0 ? streamedData.value : oldData.rows
  )
  
  streamedData.value = mergedRows

  // 构建新的数据对象
  const updatedData: ChartData = {
    ...newData,
    rows: mergedRows
  }

  // 更新图表
  const option = generateChartOption(currentChartType.value, updatedData)
  
  // 应用平滑动画
  const animatedOption = chartAnimationService.applyAnimation(option, {
    enabled: true,
    duration: 500,
    easing: 'cubicOut'
  })

  chartInstance.setOption(animatedOption, false)

  // 隐藏加载动画
  if (props.options?.showLoadingOnUpdate) {
    chartInstance.hideLoading()
  }

  ElMessage.success(`新增 ${newRows.length} 条数据`)
}

/**
 * 流式渲染图表
 */
async function renderChartStreaming(data: ChartData) {
  if (!chartInstance) return

  isStreaming.value = true
  streamProgress.value = 0
  streamedData.value = []

  // 显示加载动画
  const loadingConfig = chartStreamingService.getLoadingAnimation()
  chartInstance.showLoading('default', loadingConfig)

  try {
    // 使用流式渲染服务
    await chartStreamingService.streamData(
      chartId,
      data.rows,
      (batch, accumulatedData) => {
        // 更新进度
        const state = chartStreamingService.getState()
        streamProgress.value = state.progress
        streamedData.value = accumulatedData

        // 构建当前批次的数据对象
        const currentData: ChartData = {
          ...data,
          rows: accumulatedData
        }

        // 更新图表
        const option = generateChartOption(currentChartType.value, currentData)
        chartInstance?.setOption(option, false)
      },
      () => {
        // 完成回调
        chartInstance?.hideLoading()
        isStreaming.value = false
        streamProgress.value = 100
        ElMessage.success('数据加载完成')
      }
    )
  } catch (error) {
    console.error('Streaming render failed:', error)
    chartInstance.hideLoading()
    isStreaming.value = false
    ElMessage.error('数据加载失败')
  }
}

/**
 * 将大数字格式化为简短形式，跟随当前语言：
 * - 中文：219400 → 21.9万，1200000 → 1.2百万
 * - 英文：154043 → 154K，1200000 → 1.2M
 */
function formatChartNumber(value: number | string, currentLocale?: string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return String(value)
  const abs = Math.abs(num)
  const sign = num < 0 ? '-' : ''
  const loc = currentLocale ?? (typeof locale === 'string' ? locale : (locale as any)?.value) ?? 'zh-CN'
  const isZh = loc.startsWith('zh')
  if (abs >= 1_000_000) {
    const val = abs / 1_000_000
    const n = val % 1 === 0 ? val : parseFloat(val.toFixed(1))
    return isZh ? `${sign}${n}百万` : `${sign}${n}M`
  }
  if (abs >= 10_000 || (!isZh && abs >= 1_000)) {
    if (isZh) {
      const val = abs / 10_000
      const n = val % 1 === 0 ? val : parseFloat(val.toFixed(1))
      return `${sign}${n}万`
    }
    const val = abs / 1_000
    return sign + (val % 1 === 0 ? val : parseFloat(val.toFixed(1))) + 'K'
  }
  return String(value)
}

function generateChartOption(type: ChartType, data: ChartData): EChartsOption {
  const baseOption: EChartsOption = {
    title: {
      text: data.title || '',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      confine: true,
      backgroundColor: 'rgba(50, 50, 50, 0.9)',
      borderColor: '#333',
      borderWidth: 0,
      textStyle: {
        color: '#fff',
        fontSize: 12
      },
      padding: [8, 12],
      formatter: (params: any) => {
        if (Array.isArray(params)) {
          let result = `<div style="font-weight: bold; margin-bottom: 4px;">${params[0].axisValue}</div>`
          params.forEach((param: any) => {
            // tooltip 显示完整原始数字（领导 hover 时看到精确值）
            result += `<div style="margin: 2px 0;">
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${param.color};margin-right:5px;"></span>
              ${param.seriesName}: <span style="font-weight: bold;">${param.value}</span>
            </div>`
          })
          return result
        }
        return params.name + ': ' + params.value
      }
    },
    legend: {
      show: props.options?.showLegend !== false,
      top: 'bottom',
      type: 'scroll',
      pageButtonItemGap: 5,
      pageButtonGap: 20,
      pageIconSize: 12,
      pageTextStyle: {
        color: '#666'
      },
      selectedMode: true // 启用图例点击切换
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    // 添加工具栏
    toolbox: {
      show: props.options?.showToolbox !== false,
      feature: {
        dataZoom: {
          yAxisIndex: 'none',
          title: {
            zoom: t('chart.toolbar.zoom'),
            back: t('chart.toolbar.restore'),
          }
        },
        restore: {
          title: t('chart.toolbar.restore'),
        },
        saveAsImage: {
          title: t('chart.toolbar.saveImage'),
          pixelRatio: 2
        }
      },
      right: '20px',
      top: '10px'
    },
    // 添加数据缩放组件
    dataZoom: props.options?.enableDataZoom !== false ? [
      {
        type: 'slider',
        show: data.rows.length > 20, // 数据量大时显示
        xAxisIndex: [0],
        start: 0,
        end: 100,
        height: 20,
        bottom: '5%',
        handleSize: '80%',
        handleStyle: {
          color: '#188df0'
        },
        textStyle: {
          color: '#666'
        },
        borderColor: '#ddd'
      },
      {
        type: 'inside',
        xAxisIndex: [0],
        start: 0,
        end: 100
      }
    ] : undefined
  }

  // X 轴升序：对 FW18/FW19 等分类按数字升序排序后再渲染
  const sortedData = getSortedChartData(data)

  // 🔥 优先使用 AI 生成的 series（后端 chat_orchestrator 传入）
  // 仅当当前图表类型与 AI 推荐类型一致时使用，其他类型用 SmartChart 自己的逻辑
  const aiSeries = (sortedData as any).series as Array<{
    name: string
    type?: string
    data: Array<{ name: string; value: number } | number>
  }> | undefined
  const aiRecommendedType = (sortedData as any).aiRecommendedType as string | undefined

  if (aiSeries && aiSeries.length > 0 && type !== 'pie' && type !== 'scatter' && type !== 'heatmap' && type !== 'radar') {
    // AI series 适用于推荐类型，或 combo 类型（AI 现在支持双Y轴 combo）
    const useAISeries = !aiRecommendedType || type === aiRecommendedType || type === 'combo'
    if (useAISeries) {
      return generateChartFromAISeries(baseOption, sortedData, aiSeries, type)
    }
  }

  switch (type) {
    case 'bar':
      return generateBarChart(baseOption, sortedData)
    case 'line':
      return generateLineChart(baseOption, sortedData)
    case 'pie':
      return generatePieChart(baseOption, sortedData)
    case 'scatter':
      return generateScatterChart(baseOption, sortedData)
    case 'heatmap':
      return generateHeatmapChart(baseOption, sortedData)
    case 'radar':
      return generateRadarChart(baseOption, sortedData)
    case 'combo':
      return generateComboChart(baseOption, sortedData)
    default:
      return generateBarChart(baseOption, sortedData)
  }
}

/**
 * 使用 AI 生成的 series 直接构建图表配置
 * AI 的 series.data 格式为 [{name: 'Jan', value: 3105903}, ...]
 * 用 name 作为 X 轴标签，value 作为 Y 轴数据
 * 支持 combo 双Y轴：当 series 含 yAxisIndex 时自动启用双Y轴
 */
function generateChartFromAISeries(
  baseOption: EChartsOption,
  data: ChartData,
  aiSeries: Array<{ name: string; type?: string; yAxisIndex?: number; data: Array<{ name: string; value: number } | number> }>,
  type: ChartType
): EChartsOption {
  // 从第一个 series 的 data 提取 X 轴标签，并按 FW18/FW19 等升序排序
  const firstSeriesData = aiSeries[0]?.data ?? []
  const labels = firstSeriesData.map(d =>
    typeof d === 'object' && d !== null ? String((d as any).name) : String(d)
  )
  const sortKeys = labels.map(l => getCategorySortKey(l))
  const isSortable = sortKeys.every(k => typeof k === 'number')
  const indices = labels.map((_, i) => i)
  if (isSortable) {
    indices.sort((a, b) => (sortKeys[a] as number) - (sortKeys[b] as number))
  }
  const xAxisLabels: string[] = indices.map(i => labels[i])

  const isMultiSeries = aiSeries.length > 1

  // 🔥 检测是否需要双Y轴（combo 模式）
  const hasDualAxis = aiSeries.some(s => s.yAxisIndex === 1)

  // 如果是 combo 类型且有双Y轴标记，使用 buildEChartsOption 处理
  if ((type === 'combo' || hasDualAxis) && hasDualAxis) {
    const currentLocale = typeof locale === 'string' ? locale : (locale as any)?.value ?? 'zh-CN'
    
    // 将 AI series 转换为 buildEChartsOption 需要的格式
    const seriesConfigs = aiSeries.map((s, i) => {
      const values = indices.map(idx => {
        const d = s.data[idx]
        return typeof d === 'object' && d !== null ? (d as any).value : d
      })
      return {
        name: s.name,
        type: (s.type as 'bar' | 'line') || 'bar',
        yAxisIndex: s.yAxisIndex ?? 0,
        data: values as (number | null)[]
      }
    })

    const { yAxis, series: builtSeries } = buildEChartsOption(seriesConfigs, { locale: currentLocale })

    // 为每个 series 添加样式和数据标签
    const styledSeries = builtSeries.map((s: any, i: number) => {
      const cfg = seriesConfigs[i]
      const isPercent = cfg.yAxisIndex === 1

      if (s.type === 'line') {
        const color = LINE_COLORS[i % LINE_COLORS.length]
        return {
          ...s,
          smooth: true,
          lineStyle: { color, width: 2 },
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: { color, borderColor: '#fff', borderWidth: 2 },
          label: {
            show: true,
            position: 'top' as const,
            fontSize: 11,
            fontWeight: 'bold',
            color: '#333',
            formatter: (params: any) => {
              const v = params.value
              if (v == null || v === '') return ''
              if (isPercent && Math.abs(Number(v)) < 1000) return `${v}%`
              return formatChartNumber(v, currentLocale)
            }
          }
        }
      } else {
        const colors = SERIES_COLORS[i % SERIES_COLORS.length]
        return {
          ...s,
          label: {
            show: true,
            position: 'top' as const,
            fontSize: 11,
            fontWeight: 'bold',
            color: '#333',
            formatter: (params: any) => formatChartNumber(params.value, currentLocale)
          },
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: colors[0] },
              { offset: 0.5, color: colors[1] },
              { offset: 1, color: colors[2] }
            ])
          }
        }
      }
    })

    return {
      ...baseOption,
      legend: isMultiSeries ? { data: aiSeries.map(s => s.name), top: '5%' } : undefined,
      xAxis: {
        type: 'category',
        data: xAxisLabels,
        axisLabel: {
          rotate: xAxisLabels.length > 10 ? 45 : 0,
          interval: 0
        }
      },
      yAxis,
      series: styledSeries
    }
  }

  // 非 combo 模式：单Y轴渲染
  const series = aiSeries.map((s, i) => {
    // 提取每个 series 的数值数组，并按与 xAxisLabels 相同的顺序排列
    const values = indices.map(idx => {
      const d = s.data[idx]
      return typeof d === 'object' && d !== null ? (d as any).value : d
    })

    const seriesType = (s.type as 'bar' | 'line') || (type === 'line' ? 'line' : 'bar')

    if (seriesType === 'line') {
      const color = LINE_COLORS[i % LINE_COLORS.length]
      return {
        name: s.name,
        type: 'line' as const,
        data: values,
        smooth: true,
        lineStyle: { color, width: 2 },
        areaStyle: isMultiSeries ? undefined : {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(24, 141, 240, 0.3)' },
            { offset: 1, color: 'rgba(24, 141, 240, 0.1)' }
          ])
        },
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color, borderColor: '#fff', borderWidth: 2 }
      }
    } else {
      const colors = SERIES_COLORS[i % SERIES_COLORS.length]
      return {
        name: s.name,
        type: 'bar' as const,
        data: values,
        label: {
          show: true,
          position: 'top' as const,
          formatter: (params: any) => formatChartNumber(params.value),
          fontSize: 11,
          fontWeight: 'bold',
          color: '#333'
        },
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: colors[0] },
            { offset: 0.5, color: colors[1] },
            { offset: 1, color: colors[2] }
          ])
        }
      }
    }
  })

  return {
    ...baseOption,
    legend: isMultiSeries ? { data: aiSeries.map(s => s.name), top: '5%' } : undefined,
    xAxis: {
      type: 'category',
      data: xAxisLabels,
      boundaryGap: type !== 'line',
      axisLabel: {
        rotate: xAxisLabels.length > 10 ? 45 : 0,
        interval: 0
      }
    },
    yAxis: { type: 'value' },
    series
  }
}

// 多 series 颜色调色板
const SERIES_COLORS = [
  ['#83bff6', '#188df0', '#188df0'],
  ['#f6c23e', '#e0a800', '#e0a800'],
  ['#1cc88a', '#17a673', '#17a673'],
  ['#e74a3b', '#c0392b', '#c0392b'],
  ['#9b59b6', '#8e44ad', '#8e44ad'],
  ['#36b9cc', '#2c9faf', '#2c9faf'],
]

/**
 * 过滤出数值列的索引（跳过日期/维度列）
 * 日期/维度列特征：列名含 date/time/week/month/year/label/name/id/start/end 等，
 * 或第一行数据为非数字字符串
 */
const DIMENSION_PATTERN = /date|time|week|month|year|label|_name$|^name|^id$|_id$|start|end|fw_n|fm_n|fw_label/i

/**
 * 获取所有维度列的索引（匹配 DIMENSION_PATTERN 或值为非数字字符串的列）
 */
function getDimensionColumnIndices(data: ChartData): number[] {
  if (!data.rows || data.rows.length === 0) return [0]
  return data.columns
    .map((col, idx) => ({ col, idx }))
    .filter(({ col, idx }) => {
      if (DIMENSION_PATTERN.test(col)) return true
      const sampleVal = data.rows[0]?.[idx]
      if (typeof sampleVal === 'string' && isNaN(Number(sampleVal))) return true
      return false
    })
    .map(({ idx }) => idx)
}

/**
 * 判断第 0 列是否为维度列（X 轴）
 * 如果第 0 列是字符串或匹配 DIMENSION_PATTERN，则视为维度列
 * 否则（纯数值列）视为数值列，此时所有列都作为 series
 */
function isFirstColDimension(data: ChartData): boolean {
  if (!data.rows || data.rows.length === 0) return true
  const col0 = data.columns[0]
  if (DIMENSION_PATTERN.test(col0)) return true
  const sampleVal = data.rows[0]?.[0]
  // 如果第一行第0列是字符串（非纯数字），则是维度列
  if (typeof sampleVal === 'string' && isNaN(Number(sampleVal))) return true
  return false
}

function getNumericColumnIndices(data: ChartData): number[] {
  const dimIndices = new Set(getDimensionColumnIndices(data))
  // 如果没有任何维度列，所有列都是数值列
  if (dimIndices.size === 0) {
    return data.columns.map((_, idx) => idx)
  }
  return data.columns
    .map((col, idx) => ({ col, idx }))
    .filter(({ idx }) => !dimIndices.has(idx))
    .map(({ idx }) => idx)
}

/**
 * 从分类标签解析可排序的键（用于 X 轴升序）
 * 例如：FW18 -> 18，FW21 -> 21；纯数字字符串直接转数字
 */
function getCategorySortKey(label: string): number | string {
  const s = String(label).trim()
  const fwMatch = /^FW\s*(\d+)$/i.exec(s)
  if (fwMatch) return parseInt(fwMatch[1], 10)
  const num = parseFloat(s)
  if (!isNaN(num)) return num
  return s
}

/**
 * 当维度列为 FW18/FW19 或可解析为数字时，按升序排序 rows，保证 X 轴升序
 * 若有 AI 传入的 series，一并按相同顺序重排，避免组合图与表格数据顺序不一致
 */
function getSortedChartData(data: ChartData): ChartData {
  if (!data.rows || data.rows.length <= 1) return data
  const dimIndices = getDimensionColumnIndices(data)
  if (dimIndices.length === 0) return data
  const dimIdx = dimIndices[0]
  const keys = data.rows.map(row => getCategorySortKey(String(row[dimIdx])))
  const isSortable = keys.every(k => typeof k === 'number')
  if (!isSortable) return data
  const indices = data.rows.map((_, i) => i).sort((a, b) => (keys[a] as number) - (keys[b] as number))
  const sortedRows = indices.map(i => [...data.rows[i]])
  const out: ChartData = { ...data, rows: sortedRows }
  const aiSeries = (data as any).series as Array<{ data: (number | null)[] }> | undefined
  if (aiSeries && Array.isArray(aiSeries)) {
    (out as any).series = aiSeries.map(s => ({
      ...s,
      data: indices.map(i => s.data[i])
    }))
  }
  return out
}

/**
 * 获取 X 轴数据
 * - 有维度列时：将所有维度列的值拼接为标签（如 calendar_year+calendar_month → "2025-1"）
 * - 纯数值数据：用列名作为 X 轴（横向对比）
 */
function getXAxisData(data: ChartData): string[] {
  const dimIndices = getDimensionColumnIndices(data)
  if (dimIndices.length === 0) {
    // 纯数值数据：用列名作为 X 轴
    return getNumericColumnIndices(data).map(idx => data.columns[idx])
  }
  if (dimIndices.length === 1) {
    // 单维度列：直接用该列的值
    return data.rows.map(row => String(row[dimIndices[0]]))
  }
  // 多维度列（如 calendar_year + calendar_month）：拼接为 "2025-1", "2025-2" 等
  // 检测是否是 year+month 组合，生成更友好的月份标签
  const colNames = dimIndices.map(i => data.columns[i].toLowerCase())
  const hasYear = colNames.some(c => c.includes('year'))
  const hasMonth = colNames.some(c => c.includes('month'))
  const MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  if (hasYear && hasMonth) {
    const yearIdx = dimIndices[colNames.findIndex(c => c.includes('year'))]
    const monthIdx = dimIndices[colNames.findIndex(c => c.includes('month'))]
    return data.rows.map(row => {
      const m = Number(row[monthIdx])
      return MONTH_ABBR[m - 1] || String(m)
    })
  }
  // 其他多维度：用连字符拼接
  return data.rows.map(row => dimIndices.map(i => String(row[i])).join('-'))
}

/**
 * 获取纯数值数据的 series data（每列一个值，转置为按列取值）
 * 用于纯数值数据（无维度列）的图表渲染
 */
function getSeriesDataForAllNumeric(data: ChartData, colIndex: number): number[] {
  // 纯数值模式：每行是一条记录，但只有1行时，每列是一个数据点
  // 多行时，对同一列求和或取平均（聚合显示）
  if (data.rows.length === 1) {
    // 单行：直接取该列的值作为单个数据点
    // 但 X 轴是列名，所以 series 应该是所有列的值组成的数组
    // 这里返回所有数值列的值（每列对应 X 轴一个点）
    return getNumericColumnIndices(data).map(idx => {
      const v = data.rows[0][idx]
      return v === null || v === undefined ? 0 : Number(v)
    })
  }
  // 多行：取该列所有行的值
  return data.rows.map(row => {
    const v = row[colIndex]
    return v === null || v === undefined ? 0 : Number(v)
  })
}

function generateBarChart(baseOption: EChartsOption, data: ChartData): EChartsOption {
  // 过滤出数值列，跳过日期/维度列
  const numericIndices = getNumericColumnIndices(data)
  const hasDimension = isFirstColDimension(data)
  const isMultiSeries = numericIndices.length > 1
  const xAxisData = getXAxisData(data)

  // 纯数值模式（无维度列）：每列是一个 X 轴点，只有一条 series
  if (!hasDimension) {
    const colors = SERIES_COLORS[0]
    const seriesData = numericIndices.map(idx => {
      const v = data.rows[0]?.[idx]
      return v === null || v === undefined ? 0 : Number(v)
    })
    return {
      ...baseOption,
      xAxis: { type: 'category', data: xAxisData },
      yAxis: { type: 'value' },
      series: [{
        name: '数值',
        type: 'bar' as const,
        data: seriesData,
        label: {
          show: true, position: 'top' as const,
          formatter: (params: any) => formatChartNumber(params.value),
          fontSize: 11, fontWeight: 'bold', color: '#333'
        },
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: colors[0] },
            { offset: 0.5, color: colors[1] },
            { offset: 1, color: colors[2] }
          ])
        }
      }]
    }
  }

  const series = numericIndices.map((colIndex, i) => {
    const colors = SERIES_COLORS[i % SERIES_COLORS.length]
    return {
      name: data.columns[colIndex],
      type: 'bar' as const,
      data: data.rows.map(row => row[colIndex]),
      label: {
        show: true,
        position: 'top' as const,
        formatter: (params: any) => formatChartNumber(params.value),
        fontSize: 11,
        fontWeight: 'bold',
        color: '#333'
      },
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: colors[0] },
          { offset: 0.5, color: colors[1] },
          { offset: 1, color: colors[2] }
        ])
      },
      emphasis: {
        focus: 'series' as const,
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      },
      selectedMode: 'single' as const
    }
  })

  return {
    ...baseOption,
    // 多 series 时显示图例
    legend: isMultiSeries ? {
      data: numericIndices.map(i => data.columns[i]),
      top: '5%'
    } : undefined,
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLabel: {
        rotate: data.rows.length > 10 ? 45 : 0,
        interval: 0
      }
    },
    yAxis: {
      type: 'value'
    },
    series
  }
}

// 折线图多 series 颜色
const LINE_COLORS = ['#188df0', '#f6c23e', '#1cc88a', '#e74a3b', '#9b59b6', '#36b9cc']

function generateLineChart(baseOption: EChartsOption, data: ChartData): EChartsOption {
  // 过滤出数值列，跳过日期/维度列
  const numericIndices = getNumericColumnIndices(data)
  const hasDimension = isFirstColDimension(data)
  const isMultiSeries = numericIndices.length > 1
  const xAxisData = getXAxisData(data)

  // 纯数值模式（无维度列）：每列是一个 X 轴点，只有一条 series
  if (!hasDimension) {
    const color = LINE_COLORS[0]
    const seriesData = numericIndices.map(idx => {
      const v = data.rows[0]?.[idx]
      return v === null || v === undefined ? 0 : Number(v)
    })
    return {
      ...baseOption,
      xAxis: { type: 'category', data: xAxisData, boundaryGap: false },
      yAxis: { type: 'value' },
      series: [{
        name: '数值',
        type: 'line' as const,
        data: seriesData,
        smooth: true,
        lineStyle: { color, width: 2 },
        symbol: 'circle', symbolSize: 6,
        itemStyle: { color, borderColor: '#fff', borderWidth: 2 }
      }]
    }
  }

  const series = numericIndices.map((colIndex, i) => {
    const color = LINE_COLORS[i % LINE_COLORS.length]
    return {
      name: data.columns[colIndex],
      type: 'line' as const,
      data: data.rows.map(row => row[colIndex]),
      smooth: true,
      lineStyle: { color, width: 2 },
      // 单 series 时显示面积，多 series 时不显示（避免遮挡）
      areaStyle: isMultiSeries ? undefined : {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(24, 141, 240, 0.3)' },
          { offset: 1, color: 'rgba(24, 141, 240, 0.1)' }
        ])
      },
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color, borderColor: '#fff', borderWidth: 2 },
      emphasis: {
        focus: 'series' as const,
        itemStyle: {
          borderWidth: 3,
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }
  })

  return {
    ...baseOption,
    legend: isMultiSeries ? {
      data: numericIndices.map(i => data.columns[i]),
      top: '5%'
    } : undefined,
    xAxis: {
      type: 'category',
      data: xAxisData,
      boundaryGap: false
    },
    yAxis: { type: 'value' },
    series
  }
}

function generatePieChart(baseOption: EChartsOption, data: ChartData): EChartsOption {
  return {
    ...baseOption,
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    series: [{
      name: data.columns[0] || '数据',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        formatter: '{b}: {d}%'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold'
        },
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      },
      data: data.rows.map(row => ({
        name: row[0],
        value: row[1]
      }))
    }]
  }
}

function generateScatterChart(baseOption: EChartsOption, data: ChartData): EChartsOption {
  return {
    ...baseOption,
    xAxis: {
      type: 'value',
      name: data.columns[0] || 'X',
      nameLocation: 'middle',
      nameGap: 30
    },
    yAxis: {
      type: 'value',
      name: data.columns[1] || 'Y',
      nameLocation: 'middle',
      nameGap: 40
    },
    series: [{
      type: 'scatter',
      data: data.rows.map(row => [row[0], row[1]]),
      symbolSize: 10,
      itemStyle: {
        color: '#188df0',
        opacity: 0.7
      },
      emphasis: {
        itemStyle: {
          color: '#2378f7',
          opacity: 1,
          borderColor: '#fff',
          borderWidth: 2
        }
      }
    }]
  }
}

function generateHeatmapChart(baseOption: EChartsOption, data: ChartData): EChartsOption {
  // 简化的热力图实现
  const xAxisData = [...new Set(data.rows.map(row => row[0]))]
  const yAxisData = [...new Set(data.rows.map(row => row[1]))]
  
  return {
    ...baseOption,
    tooltip: {
      position: 'top'
    },
    grid: {
      height: '50%',
      top: '10%'
    },
    xAxis: {
      type: 'category',
      data: xAxisData,
      splitArea: {
        show: true
      }
    },
    yAxis: {
      type: 'category',
      data: yAxisData,
      splitArea: {
        show: true
      }
    },
    visualMap: {
      min: 0,
      max: Math.max(...data.rows.map(row => row[2] || 0)),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '15%'
    },
    series: [{
      type: 'heatmap',
      data: data.rows.map(row => [row[0], row[1], row[2] || 0]),
      label: {
        show: true
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }
}

function generateRadarChart(baseOption: EChartsOption, data: ChartData): EChartsOption {
  const indicators = data.columns.slice(1).map(col => ({ name: col, max: 100 }))
  
  return {
    ...baseOption,
    radar: {
      indicator: indicators
    },
    series: [{
      type: 'radar',
      data: data.rows.map(row => ({
        value: row.slice(1),
        name: row[0]
      })),
      areaStyle: {
        opacity: 0.3
      }
    }]
  }
}

/**
 * 生成 Combo Chart（双Y轴，bar + line 混合）
 * 使用 buildEChartsOption 工具函数处理双Y轴逻辑
 * Property 8: 当任意 series 含 yAxisIndex:1 时，yAxis 数组长度为 2
 * Property 9: 次轴（index 1）的 axisLabel.formatter 包含 %
 */
function generateComboChart(baseOption: EChartsOption, data: ChartData): EChartsOption {
  // 从 data 中提取 series 配置（支持外部传入的 series 含 yAxisIndex）
  // 若 data 中没有预设 series，则按列名启发式分配轴
  const rawSeries = (data as any).series as Array<{
    name: string
    type: 'bar' | 'line'
    yAxisIndex?: number
    data: (number | null)[]
  }> | undefined

  let seriesConfigs: Array<{
    name: string
    type: 'bar' | 'line'
    yAxisIndex?: number
    data: (number | null)[]
  }>

  if (rawSeries && rawSeries.length > 0) {
    seriesConfigs = rawSeries
  } else {
    // 启发式：字段名含 rate/pct/ratio/yoy/mom/growth/change → 次轴 line，其余 → 主轴 bar
    const ratePattern = /rate|pct|ratio|yoy|mom|qoq|growth/i
    // abs_ 前缀或 abs_change 类字段是绝对值，不是百分比，强制放主轴
    const absPattern = /^abs_|_abs$|abs_change/i

    // 获取所有维度列索引（支持多维度，如 calendar_year + calendar_month）
    const dimIndices = new Set(getDimensionColumnIndices(data))

    seriesConfigs = data.columns
      .map((col, i) => ({ col, i }))
      .filter(({ col, i }) => {
        // 跳过维度列
        if (dimIndices.has(i)) return false
        // 跳过第一行数据为字符串的列（说明是维度列）
        const sampleVal = data.rows[0]?.[i]
        if (typeof sampleVal === 'string' && isNaN(Number(sampleVal))) return false
        return true
      })
      .map(({ col, i }) => {
        const isAbs = absPattern.test(col)
        const isRate = !isAbs && ratePattern.test(col)
        return {
          name: col,
          type: isRate ? 'line' as const : 'bar' as const,
          yAxisIndex: isRate ? 1 : 0,
          data: data.rows.map(row => {
            const v = row[i]
            return v === null || v === undefined ? null : Number(v)
          })
        }
      })
  }

  const currentLocale = typeof locale === 'string' ? locale : (locale as any)?.value ?? 'zh-CN'
  const { yAxis, series } = buildEChartsOption(seriesConfigs, { locale: currentLocale })

  // X 轴：有维度列用维度列值（支持多维度拼接），否则用列名（横向对比）
  const xAxisData = getXAxisData(data)

  // 纯数值单行模式：每个 series 只有一个值，转为单点数据
  const isAllNumericSingleRow = getDimensionColumnIndices(data).length === 0 && data.rows.length === 1
  let finalSeries = isAllNumericSingleRow ? buildEChartsOption(seriesConfigs.map(s => ({ ...s, data: [s.data[0]] })), { locale: currentLocale }).series : series

  // 组合图：为每个 series 添加数据标签（柱状用 locale 数值，折线次轴用百分比）
  finalSeries = finalSeries.map((s: any, i: number) => {
    const cfg = seriesConfigs[i]
    const isPercent = cfg?.yAxisIndex === 1
    return {
      ...s,
      label: {
        show: true,
        position: s.type === 'bar' ? ('top' as const) : ('top' as const),
        fontSize: 11,
        fontWeight: 'bold',
        color: '#333',
        formatter: (params: any) => {
          const v = params.value
          if (v == null || v === '') return ''
          if (isPercent && Math.abs(Number(v)) < 1000) return `${v}%`
          return formatChartNumber(v, currentLocale)
        }
      }
    }
  })

  return {
    ...baseOption,
    xAxis: {
      type: 'category',
      data: xAxisData
    },
    yAxis,
    series: finalSeries
  }
}

function changeChartType(type: ChartType) {
  currentChartType.value = type
  updateChart()
}

function handleExport(format: ExportFormat) {
  if (!chartInstance) return

  try {
    if (format === 'pdf') {
      chartExportService.exportAsPDF(chartInstance, 'chart', {
        title: props.data.title
      })
    } else if (format === 'excel') {
      chartExportService.exportAsExcel(props.data, 'chart-data')
    } else {
      chartExportService.exportAsImage(chartInstance, format, 'chart')
    }
    ElMessage.success(`导出${format.toUpperCase()}成功`)
  } catch (error) {
    console.error('Export failed:', error)
    ElMessage.error('导出失败')
  }
}

function handleSaveConfig() {
  if (!saveForm.value.name) {
    ElMessage.warning('请输入配置名称')
    return
  }

  try {
    const config: ChartConfig = {
      name: saveForm.value.name,
      type: currentChartType.value,
      data: props.data,
      options: props.options || {},
      theme: props.theme || 'light'
    }

    if (saveForm.value.asTemplate) {
      const template = {
        id: `template_${Date.now()}`,
        name: saveForm.value.name,
        type: currentChartType.value,
        options: props.options || {},
        theme: props.theme || 'light'
      }
      chartConfigService.saveTemplate(template)
      ElMessage.success('模板保存成功')
    } else {
      const id = chartConfigService.saveConfig(config)
      ElMessage.success(`配置保存成功 (ID: ${id})`)
    }

    showSaveDialog.value = false
    saveForm.value.name = ''
    saveForm.value.asTemplate = false
  } catch (error) {
    console.error('Save config failed:', error)
    ElMessage.error('保存失败')
  }
}

function generateShare() {
  try {
    const config: ChartConfig = {
      name: props.data.title || '图表',
      type: currentChartType.value,
      data: props.data,
      options: props.options || {},
      theme: props.theme || 'light'
    }

    const shareConfig = chartShareService.generateShareLink(config, {
      expiresInDays: shareOptions.value.expiresInDays || undefined
    })

    shareLink.value = shareConfig.shareUrl
    embedCode.value = shareConfig.embedCode

    ElMessage.success('分享链接生成成功')
  } catch (error) {
    console.error('Generate share failed:', error)
    ElMessage.error('生成分享链接失败')
  }
}

async function copyShareLink() {
  const success = await chartShareService.copyToClipboard(shareLink.value)
  if (success) {
    ElMessage.success('分享链接已复制到剪贴板')
  } else {
    ElMessage.error('复制失败')
  }
}

async function copyEmbedCode() {
  const success = await chartShareService.copyToClipboard(embedCode.value)
  if (success) {
    ElMessage.success('嵌入代码已复制到剪贴板')
  } else {
    ElMessage.error('复制失败')
  }
}

function exportChart(format: ExportFormat) {
  handleExport(format)
}

function handleResize() {
  if (chartInstance) {
    chartInstance.resize()
  }
}

function cleanup() {
  if (props.responsive) {
    window.removeEventListener('resize', handleResize)
  }
  
  // 清理 ResizeObserver
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  
  // 清理流式渲染资源
  chartStreamingService.cleanup(chartId)
  
  // 清理交互服务
  if (chartInstance && props.options?.linkageGroup) {
    chartInteractionService.disableChartLinkage(chartInstance, props.options.linkageGroup)
  }
  chartInteractionService.cleanup()
  
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

function getChartTypeLabel(type: ChartType): string {
  const keyMap: Record<ChartType, string> = {
    bar: 'chart.types.bar',
    line: 'chart.types.line',
    pie: 'chart.types.pie',
    scatter: 'chart.types.scatter',
    heatmap: 'chart.types.heatmap',
    radar: 'chart.types.radar',
    combo: 'chart.types.combo',
  }
  return t(keyMap[type] || type)
}
</script>

<style scoped>
.smart-chart-container {
  width: 100%;
  position: relative;
  background: #fff;
  border-radius: 4px;
  padding: 16px;
}

.chart-recommendation {
  margin-bottom: 12px;
}

.chart-recommendation :deep(.el-alert) {
  padding: 8px 12px;
}

.chart-recommendation :deep(.el-alert__title) {
  font-size: 14px;
  font-weight: 500;
}

.chart-recommendation :deep(.el-alert__description) {
  font-size: 12px;
  margin-top: 4px;
  color: #606266;
}

.chart-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.chart-element {
  width: 100%;
  min-height: 300px;
}

.chart-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.share-content {
  padding: 10px 0;
}

.share-options {
  margin-top: 20px;
}
</style>
