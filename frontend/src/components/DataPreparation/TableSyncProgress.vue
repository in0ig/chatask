<template>
  <el-dialog
    :model-value="visible"
    title="同步表结构"
    width="600px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="sync-content">
      <div class="sync-status">
        <div class="status-header">
          <span class="status-text">{{ statusText }}</span>
        </div>
        <el-progress
          v-show="syncing || syncResult"
          :percentage="progressPercentage"
          class="sync-progress"
        />
        
        <div v-show="syncResult" class="sync-result">
          <div v-show="syncResult && syncResult.success" class="success-info">
            <el-icon class="success-icon"><Check /></el-icon>
            <span>同步成功完成</span>
          </div>
          <div v-show="syncResult && !syncResult.success" class="error-info">
            <el-icon class="error-icon"><Close /></el-icon>
            <span>同步失败: {{ syncResult?.error || '' }}</span>
          </div>
          
          <div v-show="syncResult" class="result-details">
            <p>总表数: {{ syncResult?.totalTables || 0 }}</p>
            <p>成功: {{ syncResult?.successCount || 0 }}</p>
            <p>失败: {{ syncResult?.errorCount || 0 }}</p>
            <p>耗时: {{ syncResult ? formatDuration(syncResult.duration) : '' }}</p>
          </div>
        </div>
      </div>
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button 
          v-show="!syncing && !syncResult" 
          type="primary" 
          @click="startSync"
        >
          开始同步
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElDialog, ElProgress, ElButton, ElIcon } from 'element-plus'
import { Check, Close } from '@element-plus/icons-vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'

interface Props {
  visible: boolean
  tableIds?: string[]
  tableName?: string
}

interface SyncResult {
  success: boolean
  totalTables: number
  successCount: number
  errorCount: number
  duration: number
  error?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:visible': [visible: boolean]
  'complete': [result: SyncResult]
  'cancel': []
}>()

const dataPreparationStore = useDataPreparationStore()

const syncing = ref(false)
const progressPercentage = ref(0)
const syncResult = ref<SyncResult | null>(null)

const statusText = computed(() => {
  if (syncing.value) return '正在同步表结构...'
  if (syncResult.value?.success) return '同步完成'
  if (syncResult.value && !syncResult.value.success) return '同步失败'
  return '准备同步'
})

const handleClose = () => {
  emit('update:visible', false)
  if (syncResult.value) {
    emit('complete', syncResult.value)
  }
}

const startSync = async () => {
  if (!props.tableIds || props.tableIds.length === 0) {
    return
  }

  syncing.value = true
  progressPercentage.value = 0
  syncResult.value = null

  const startTime = Date.now()
  
  try {
    if (props.tableIds.length === 1) {
      // 单表同步
      const result = await dataPreparationStore.syncTableStructure(props.tableIds[0])
      progressPercentage.value = 100
      
      syncResult.value = {
        success: result.success,
        totalTables: 1,
        successCount: result.success ? 1 : 0,
        errorCount: result.success ? 0 : 1,
        duration: Date.now() - startTime,
        error: result.message
      }
    } else {
      // 批量同步
      const result = await dataPreparationStore.batchSyncTableStructure(props.tableIds)
      progressPercentage.value = 100
      
      syncResult.value = {
        success: result.success,
        totalTables: props.tableIds.length,
        successCount: result.data?.successCount || 0,
        errorCount: result.data?.errorCount || 0,
        duration: Date.now() - startTime,
        error: result.message
      }
    }
  } catch (error: any) {
    syncResult.value = {
      success: false,
      totalTables: props.tableIds.length,
      successCount: 0,
      errorCount: props.tableIds.length,
      duration: Date.now() - startTime,
      error: error.message || '同步过程中发生错误'
    }
  } finally {
    syncing.value = false
  }
}

const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

const formatDuration = (duration: number): string => {
  const seconds = Math.floor(duration / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60

  if (minutes > 0) {
    return `${minutes}分${remainingSeconds}秒`
  }
  return `${remainingSeconds}秒`
}
</script>

<style scoped>
.sync-content {
  padding: 10px 0;
}

.sync-status {
  margin-bottom: 20px;
}

.status-header {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.status-text {
  font-size: 16px;
  font-weight: 500;
}

.sync-progress {
  margin-top: 10px;
}

.sync-result {
  margin-top: 20px;
  padding: 15px;
  border-radius: 6px;
  background-color: #f5f7fa;
}

.success-info {
  display: flex;
  align-items: center;
  color: #67c23a;
  margin-bottom: 10px;
}

.error-info {
  display: flex;
  align-items: center;
  color: #f56c6c;
  margin-bottom: 10px;
}

.success-icon,
.error-icon {
  margin-right: 8px;
}

.result-details {
  font-size: 14px;
  color: #606266;
}

.result-details p {
  margin: 5px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>