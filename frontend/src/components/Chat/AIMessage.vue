<template>
  <div class="ai-message">
    <!-- AI 头像 -->
    <div class="ai-avatar">
      <span v-if="!avatarUrl.startsWith('http')">{{ avatarUrl }}</span>
      <img v-else :src="avatarUrl" alt="AI" />
    </div>

    <!-- 消息内容 -->
    <div class="message-body">
      <!-- 思考过程（如果有） -->
      <ThinkingProcess
        v-if="thinkingSteps.length > 0"
        :steps="thinkingSteps"
        :total-time="thinkingTime"
        :auto-collapse="true"
        :collapsed="thinkingCollapsed"
      />

      <!-- 数据结果描述 -->
      <div v-if="textContent" class="result-description">
        <HighlightedText :content="textContent" />
      </div>

      <!-- 图表/表格展示：数据足够时显示，或正在生成图表时显示 loading -->
      <div v-if="hasChartableData || isGeneratingChart" class="chart-table-container">
        <!-- 视图切换工具栏：仅有足够数据时显示 -->
        <div v-if="hasChartableData" class="view-toolbar">
          <el-button-group>
            <el-button
              :type="viewMode === 'chart' ? 'primary' : 'default'"
              size="small"
              @click="viewMode = 'chart'"
            >
              {{ t('chart.chartView') }}
            </el-button>
            <el-button
              :type="viewMode === 'table' ? 'primary' : 'default'"
              size="small"
              @click="viewMode = 'table'"
            >
              {{ t('chart.tableView') }}
            </el-button>
          </el-button-group>
        </div>

        <!-- 图表视图 -->
        <div v-if="!chartData || viewMode === 'chart'" class="chart-display">
          <!-- 图表加载提示 -->
          <div v-if="isChartLoading" class="chart-loading">
            <div class="chart-loading-spinner"></div>
            <span>{{ t('chart.generatingChart') }}</span>
          </div>
          <!-- 使用 v-if 延迟挂载，确保 SmartChart 挂载时容器已可见，ECharts 能正确获取 DOM 尺寸 -->
          <SmartChart
            v-if="showChart"
            :data="chartData!"
            :type="chartType || 'auto'"
            :theme="'light'"
            :responsive="true"
            :exportable="true"
            :options="{
              showToolbar: true,
              showLegend: true,
              showToolbox: true,
              enableDataZoom: chartData!.rows.length > 20,
              height: '400px'
            }"
            @rendered="onChartRendered"
          />
        </div>

        <!-- 表格视图 -->
        <div v-else class="table-display">
          <el-table
            :data="tableData"
            stripe
            border
            style="width: 100%"
            max-height="500"
          >
            <el-table-column
              v-for="(column, index) in chartData.columns"
              :key="index"
              :prop="`col${index}`"
              :label="column"
              min-width="120"
            />
          </el-table>
        </div>
      </div>

      <!-- 时间戳 -->
      <div class="message-time">
        {{ formatTime(timestamp) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ThinkingProcess from './ThinkingProcess.vue'
import HighlightedText from './HighlightedText.vue'
import SmartChart from '@/components/Chart/SmartChart.vue'
import type { ChartData } from '@/types/chart'

const { t } = useI18n()

// 思考步骤接口
interface ThinkingStep {
  title: string
  type?: 'text' | 'sql'
  content?: string
  status: 'pending' | 'running' | 'completed' | 'error'
}

// Props
const props = defineProps<{
  // 思考过程
  thinkingSteps?: ThinkingStep[]
  thinkingTime?: string
  thinkingCollapsed?: boolean // 思考过程是否折叠
  
  // 文本内容
  textContent?: string
  
  // 图表数据
  chartData?: ChartData
  chartType?: string
  // 图表是否正在生成中（stage_chart 未完成时为 true）
  isGeneratingChart?: boolean
  
  // 其他
  timestamp?: Date | number
  avatarUrl?: string
}>()

// 默认值
const thinkingSteps = computed(() => props.thinkingSteps || [])
const thinkingTime = computed(() => props.thinkingTime || '1.4s')
const avatarUrl = computed(() => props.avatarUrl || '🤖') // 使用 emoji 作为默认头像

// 视图模式：chart（图表）或 table（表格）
const viewMode = ref<'chart' | 'table'>('chart')

// 图表加载状态：isGeneratingChart=true 时显示 loading；false 且有数据时显示图表
const isChartLoading = ref(false)
// 控制 SmartChart 是否挂载（v-if）：等 loading 结束后再挂载，确保 DOM 可见
const showChart = ref(false)

// 判断图表数据是否有意义（至少 2 行数据）
// 以下情况不展示图表，只展示文字描述：
// - 0 行：无数据
// - 1 行：单行结果（如最大值/最小值、单个聚合值），没有对比维度，图表无意义
const hasChartableData = computed(() => {
  const d = props.chartData
  if (!d) return false
  const rows = d.rows?.length ?? 0
  return rows >= 2
})

// 监听 isGeneratingChart 和 chartData 变化
watch(
  [() => props.isGeneratingChart, () => props.chartData],
  ([generating, data]) => {
    if (generating) {
      // 正在生成图表：显示 loading，隐藏图表
      isChartLoading.value = true
      showChart.value = false
    } else if (data && hasChartableData.value) {
      // 生成完成且有足够数据：短暂延迟后挂载 SmartChart（确保 DOM 可见）
      isChartLoading.value = false
      showChart.value = false
      setTimeout(() => {
        showChart.value = true
      }, 100)
    } else {
      // 无数据或数据不足（单值/空）：不显示 loading 也不显示图表
      isChartLoading.value = false
      showChart.value = false
    }
  },
  { immediate: true }
)

// 图表渲染完成回调（SmartChart 内部 ECharts 渲染完成后触发）
const onChartRendered = () => {
  // v-if 方案下无需额外操作，SmartChart 挂载时容器已可见
}

// 转换图表数据为表格数据
const tableData = computed(() => {
  if (!props.chartData) return []
  
  return props.chartData.rows.map(row => {
    const rowData: Record<string, any> = {}
    row.forEach((value, index) => {
      rowData[`col${index}`] = value
    })
    return rowData
  })
})

// 🔍 调试日志：检查 chartData
if (props.chartData) {
  console.log('📊 [AIMessage] 接收到图表数据:', {
    hasChartData: !!props.chartData,
    columns: props.chartData?.columns?.length,
    rows: props.chartData?.rows?.length,
    chartType: props.chartType,
    chartData: props.chartData
  })
} else {
  console.log('⚠️ [AIMessage] 没有图表数据')
}

// 格式化时间
const formatTime = (date?: Date | number) => {
  if (!date) return ''
  const d = typeof date === 'number' ? new Date(date) : date
  const hours = d.getHours().toString().padStart(2, '0')
  const minutes = d.getMinutes().toString().padStart(2, '0')
  return `${hours}:${minutes}`
}
</script>

<style scoped>
.ai-message {
  display: flex;
  gap: 12px;
  max-width: 100%;
  margin-bottom: 20px;
}

.ai-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  overflow: hidden;
  border: 1px solid #e0e0e0;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.ai-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.message-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-description {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 16px;
  border-top-left-radius: 4px;
  padding: 14px 16px;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.chart-table-container {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.view-toolbar {
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}

.chart-display {
  padding: 16px;
}

.chart-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 0;
  color: #6c757d;
  font-size: 14px;
}

.chart-loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e9ecef;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.table-display {
  padding: 16px;
}

.message-time {
  font-size: 11px;
  color: #999;
  padding-left: 4px;
}
</style>
