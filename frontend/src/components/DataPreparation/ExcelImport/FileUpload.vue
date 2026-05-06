<template>
  <div class="file-upload">
    <el-upload
      ref="uploadRef"
      class="upload-dragger"
      drag
      :auto-upload="false"
      :show-file-list="false"
      :accept="acceptedFormats"
      :before-upload="beforeUpload"
      :on-change="handleFileChange"
      :disabled="uploading"
    >
      <div class="upload-content">
        <el-icon class="upload-icon" :size="48">
          <UploadFilled />
        </el-icon>
        <div class="upload-text">
          <p class="primary-text">拖拽文件到此处或点击选择</p>
          <p class="secondary-text">支持 .xlsx, .xls 格式，最大 20MB</p>
        </div>
      </div>
    </el-upload>
    
    <!-- 已选择文件信息 -->
    <div v-if="selectedFile" class="file-info">
      <div class="file-details">
        <el-icon class="file-icon">
          <Document />
        </el-icon>
        <div class="file-meta">
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">({{ formatFileSize(selectedFile.size) }})</span>
        </div>
        <el-button
          type="text"
          :icon="Close"
          @click="clearFile"
          class="remove-btn"
        />
      </div>
      
      <!-- 上传进度 -->
      <div v-if="uploading" class="upload-progress">
        <el-progress
          :percentage="uploadProgress"
          :status="uploadStatus"
          :stroke-width="6"
        />
        <p class="progress-text">{{ progressText }}</p>
      </div>
    </div>
    
    <!-- 错误信息 -->
    <div v-if="errorMessage" class="error-message">
      <el-alert
        :title="errorMessage"
        type="error"
        :closable="false"
        show-icon
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document, Close } from '@element-plus/icons-vue'
import type { UploadFile, UploadRawFile } from 'element-plus'

// Props
interface Props {
  modelValue?: File | null
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  disabled: false
})

// Emits
interface Emits {
  (e: 'update:modelValue', file: File | null): void
  (e: 'file-selected', file: File): void
  (e: 'file-cleared'): void
  (e: 'upload-progress', progress: number): void
  (e: 'upload-success', result: any): void
  (e: 'upload-error', error: string): void
}

const emit = defineEmits<Emits>()

// 响应式数据
const uploadRef = ref()
const selectedFile = ref<File | null>(props.modelValue)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref<'success' | 'exception' | undefined>()
const errorMessage = ref('')

// 计算属性
const acceptedFormats = '.xlsx,.xls'
const maxFileSize = 20 * 1024 * 1024 // 20MB

const progressText = computed(() => {
  if (uploadProgress.value === 100) {
    return uploadStatus.value === 'success' ? '上传完成' : '上传失败'
  }
  return `上传中... ${uploadProgress.value}%`
})

// 文件大小格式化
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 文件上传前验证
const beforeUpload = (file: UploadRawFile): boolean => {
  clearError()
  
  // 检查文件格式
  const validFormats = ['.xlsx', '.xls']
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
  
  if (!validFormats.includes(fileExtension)) {
    setError(`不支持的文件格式: ${fileExtension}。只支持 .xlsx 和 .xls 格式`)
    return false
  }
  
  // 检查文件大小
  if (file.size > maxFileSize) {
    setError(`文件大小超过限制。最大支持 ${formatFileSize(maxFileSize)}`)
    return false
  }
  
  return true
}

// 文件选择处理
const handleFileChange = (file: UploadFile) => {
  if (file.raw && beforeUpload(file.raw)) {
    selectedFile.value = file.raw
    emit('update:modelValue', file.raw)
    emit('file-selected', file.raw)
    
    ElMessage.success(`已选择文件: ${file.name}`)
  }
}

// 清除文件
const clearFile = () => {
  selectedFile.value = null
  uploading.value = false
  uploadProgress.value = 0
  uploadStatus.value = undefined
  clearError()
  
  emit('update:modelValue', null)
  emit('file-cleared')
  
  // 清除 upload 组件的文件列表
  if (uploadRef.value && uploadRef.value.clearFiles) {
    uploadRef.value.clearFiles()
  }
}

// 设置错误信息
const setError = (message: string) => {
  errorMessage.value = message
  ElMessage.error(message)
}

// 清除错误信息
const clearError = () => {
  errorMessage.value = ''
}

// 模拟上传进度（实际项目中会通过 API 调用实现）
const simulateUpload = async (): Promise<any> => {
  return new Promise((resolve, reject) => {
    uploading.value = true
    uploadProgress.value = 0
    uploadStatus.value = undefined
    
    const interval = setInterval(() => {
      uploadProgress.value += Math.random() * 20
      emit('upload-progress', uploadProgress.value)
      
      if (uploadProgress.value >= 100) {
        clearInterval(interval)
        uploadProgress.value = 100
        
        // 模拟成功或失败
        const success = Math.random() > 0.1 // 90% 成功率
        
        setTimeout(() => {
          if (success) {
            uploadStatus.value = 'success'
            const mockResult = {
              filename: selectedFile.value?.name,
              file_path: `/uploads/${selectedFile.value?.name}`,
              sheet_names: ['Sheet1', 'Sheet2'],
              row_count: 1000,
              column_count: 8
            }
            emit('upload-success', mockResult)
            resolve(mockResult)
          } else {
            uploadStatus.value = 'exception'
            const error = '上传失败，请重试'
            setError(error)
            emit('upload-error', error)
            reject(new Error(error))
          }
          
          uploading.value = false
        }, 500)
      }
    }, 100)
  })
}

// 暴露方法给父组件
defineExpose({
  upload: simulateUpload,
  clearFile,
  selectedFile: computed(() => selectedFile.value),
  uploading: computed(() => uploading.value)
})
</script>

<style scoped>
.file-upload {
  width: 100%;
}

.upload-dragger {
  width: 100%;
}

.upload-dragger :deep(.el-upload-dragger) {
  width: 100%;
  height: 180px;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  background-color: #fafafa;
  transition: all 0.3s;
}

.upload-dragger :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background-color: #f0f9ff;
}

.upload-dragger :deep(.el-upload-dragger.is-dragover) {
  border-color: #409eff;
  background-color: #e6f7ff;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
}

.upload-icon {
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text {
  text-align: center;
}

.primary-text {
  font-size: 16px;
  color: #606266;
  margin: 0 0 8px 0;
  font-weight: 500;
}

.secondary-text {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.file-info {
  margin-top: 16px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.file-details {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  color: #409eff;
  font-size: 24px;
}

.file-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.file-size {
  font-size: 12px;
  color: #909399;
}

.remove-btn {
  color: #f56c6c;
  padding: 4px;
}

.remove-btn:hover {
  background-color: #fef0f0;
}

.upload-progress {
  margin-top: 16px;
}

.progress-text {
  margin: 8px 0 0 0;
  font-size: 12px;
  color: #909399;
  text-align: center;
}

.error-message {
  margin-top: 16px;
}

/* 禁用状态 */
.upload-dragger.is-disabled :deep(.el-upload-dragger) {
  background-color: #f5f7fa;
  border-color: #e4e7ed;
  cursor: not-allowed;
}

.upload-dragger.is-disabled .upload-icon,
.upload-dragger.is-disabled .primary-text,
.upload-dragger.is-disabled .secondary-text {
  color: #c0c4cc;
}
</style>