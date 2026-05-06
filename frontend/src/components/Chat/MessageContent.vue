<template>
  <div class="message-content-wrapper">
    <!-- 消息操作工具栏 -->
    <div v-if="showActions" class="message-actions">
      <el-button-group size="small">
        <el-button 
          v-if="canEdit" 
          :icon="Edit" 
          @click="handleEdit"
          title="编辑消息"
        />
        <el-button 
          v-if="canResend" 
          :icon="Refresh" 
          @click="handleResend"
          title="重新发送"
        />
        <el-button 
          :icon="Download" 
          @click="handleExport"
          title="导出消息"
        />
        <el-button 
          :icon="Share" 
          @click="handleShare"
          title="分享消息"
        />
        <el-button 
          v-if="canRollback"
          :icon="Back"
          @click="handleRollback"
          title="回溯到此消息"
        />
      </el-button-group>
    </div>

    <!-- 文本消息 -->
    <div v-if="message.type === 'text' || message.type === 'thinking'" class="text-content">
      <div v-if="isEditing">
        <el-input
          v-model="editContent"
          type="textarea"
          :rows="3"
          placeholder="编辑消息内容"
        />
        <div class="edit-actions">
          <el-button size="small" @click="saveEdit">保存</el-button>
          <el-button size="small" @click="cancelEdit">取消</el-button>
        </div>
      </div>
      <div v-else v-html="formattedContent"></div>
    </div>

    <!-- SQL 消息 (带语法高亮) -->
    <div v-else-if="message.type === 'sql'" class="sql-content">
      <div class="sql-header">
        <span class="sql-label">SQL查询</span>
        <el-button 
          size="small" 
          :icon="CopyDocument" 
          @click="copySql"
          text
        >
          复制
        </el-button>
      </div>
      <pre><code class="language-sql" v-html="highlightedSql"></code></pre>
    </div>

    <!-- 表格消息 -->
    <div v-else-if="message.type === 'table'" class="table-content">
      <div class="table-header">
        <span class="table-info">共 {{ tableData.length }} 行数据</span>
        <el-button-group size="small">
          <el-button :icon="Download" @click="exportTable('csv')">导出CSV</el-button>
          <el-button :icon="Download" @click="exportTable('excel')">导出Excel</el-button>
        </el-button-group>
      </div>
      <el-table 
        :data="tableData" 
        border 
        stripe 
        max-height="400"
        style="width: 100%"
      >
        <el-table-column
          v-for="column in tableColumns"
          :key="column"
          :prop="column"
          :label="column"
          show-overflow-tooltip
        />
      </el-table>
    </div>

    <!-- 图表消息 -->
    <div v-else-if="message.type === 'chart'" class="chart-content">
      <SmartChart
        v-if="message.chartData"
        :type="message.chartData.type || 'auto'"
        :data="message.chartData.data"
        :theme="'light'"
        :responsive="true"
        :exportable="true"
      />
      <div v-else class="chart-placeholder">
        <el-icon :size="48"><TrendCharts /></el-icon>
        <p>图表数据加载中...</p>
      </div>
    </div>

    <!-- 错误消息 -->
    <div v-else-if="message.type === 'error'" class="error-content">
      <el-alert
        :title="message.content"
        type="error"
        :closable="false"
        show-icon
      >
        <template v-if="message.metadata?.details" #default>
          <div class="error-details">{{ message.metadata.details }}</div>
        </template>
      </el-alert>
    </div>

    <!-- 默认消息 -->
    <div v-else class="default-content">
      {{ message.content }}
    </div>

    <!-- 分享对话框 -->
    <el-dialog
      v-model="shareDialogVisible"
      title="分享消息"
      width="500px"
    >
      <el-form label-width="80px">
        <el-form-item label="分享链接">
          <el-input v-model="shareLink" readonly>
            <template #append>
              <el-button :icon="CopyDocument" @click="copyShareLink">复制</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="分享方式">
          <el-radio-group v-model="shareMethod">
            <el-radio label="link">链接</el-radio>
            <el-radio label="image">图片</el-radio>
            <el-radio label="markdown">Markdown</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Edit, 
  Refresh, 
  Download, 
  Share, 
  Back, 
  CopyDocument,
  TrendCharts
} from '@element-plus/icons-vue'
import type { ChatMessage } from '@/types/chat'
import SmartChart from '@/components/Chart/SmartChart.vue'

// Props
const props = defineProps<{
  message: ChatMessage
  showActions?: boolean
  canEdit?: boolean
  canResend?: boolean
  canRollback?: boolean
}>()

// Emits
const emit = defineEmits<{
  edit: [content: string]
  resend: []
  export: [format: string]
  share: [method: string, data: any]
  rollback: []
}>()

// 编辑状态
const isEditing = ref(false)
const editContent = ref('')

// 分享对话框
const shareDialogVisible = ref(false)
const shareLink = ref('')
const shareMethod = ref('link')

// 格式化文本内容（支持Markdown）
const formattedContent = computed(() => {
  if (!props.message.content) return ''
  
  // 简单的Markdown渲染（换行、加粗、代码）
  let content = props.message.content
  content = content.replace(/\n/g, '<br>')
  content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  content = content.replace(/`(.*?)`/g, '<code>$1</code>')
  
  return content
})

// SQL语法高亮
const highlightedSql = computed(() => {
  if (!props.message.content) return ''
  
  let sql = props.message.content
  
  // 简单的SQL关键字高亮
  const keywords = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
    'ON', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL',
    'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'AS',
    'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'DROP'
  ]
  
  keywords.forEach(keyword => {
    const regex = new RegExp(`\\b${keyword}\\b`, 'gi')
    sql = sql.replace(regex, `<span class="sql-keyword">${keyword}</span>`)
  })
  
  return sql
})

// 解析表格数据
const tableData = computed(() => {
  if (props.message.type !== 'table' || !props.message.metadata?.data) {
    return []
  }
  return props.message.metadata.data
})

// 解析表格列
const tableColumns = computed(() => {
  if (props.message.type !== 'table' || !props.message.metadata?.columns) {
    return []
  }
  return props.message.metadata.columns
})

// 编辑消息
const handleEdit = () => {
  editContent.value = props.message.content
  isEditing.value = true
}

const saveEdit = () => {
  emit('edit', editContent.value)
  isEditing.value = false
}

const cancelEdit = () => {
  isEditing.value = false
  editContent.value = ''
}

// 重新发送
const handleResend = () => {
  emit('resend')
}

// 导出消息
const handleExport = () => {
  const format = props.message.type === 'table' ? 'excel' : 'text'
  emit('export', format)
}

// 导出表格
const exportTable = (format: string) => {
  emit('export', format)
  ElMessage.success(`正在导出${format.toUpperCase()}格式`)
}

// 分享消息
const handleShare = () => {
  shareLink.value = `${window.location.origin}/chat/share/${props.message.id}`
  shareDialogVisible.value = true
}

// 复制分享链接
const copyShareLink = () => {
  navigator.clipboard.writeText(shareLink.value)
  ElMessage.success('分享链接已复制')
}

// 回溯到此消息
const handleRollback = () => {
  emit('rollback')
}

// 复制SQL
const copySql = () => {
  navigator.clipboard.writeText(props.message.content)
  ElMessage.success('SQL已复制到剪贴板')
}
</script>

<style scoped lang="scss">
.message-content-wrapper {
  width: 100%;
  position: relative;
}

.message-actions {
  position: absolute;
  top: -32px;
  right: 0;
  opacity: 0;
  transition: opacity 0.2s;
  
  .message-content-wrapper:hover & {
    opacity: 1;
  }
}

.text-content {
  white-space: pre-wrap;
  line-height: 1.6;
  
  :deep(code) {
    background-color: #f4f4f5;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
  }
}

.edit-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

.sql-content {
  .sql-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background-color: #f4f4f5;
    border-radius: 4px 4px 0 0;
    
    .sql-label {
      font-weight: 500;
      color: #606266;
    }
  }
  
  pre {
    margin: 0;
    padding: 12px;
    background-color: #f9f9f9;
    border-radius: 0 0 4px 4px;
    overflow-x: auto;
    
    code {
      font-family: 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.5;
      
      :deep(.sql-keyword) {
        color: #0066cc;
        font-weight: 600;
      }
    }
  }
}

.table-content {
  margin-top: 8px;
  
  .table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    
    .table-info {
      color: #909399;
      font-size: 14px;
    }
  }
}

.chart-content {
  .chart-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    background-color: #f4f4f5;
    border-radius: 4px;
    color: #909399;
    
    p {
      margin-top: 16px;
      font-size: 14px;
    }
  }
}

.error-content {
  :deep(.el-alert) {
    margin: 0;
  }
  
  .error-details {
    margin-top: 8px;
    font-size: 13px;
    color: #909399;
    white-space: pre-wrap;
  }
}

.default-content {
  white-space: pre-wrap;
}
</style>
