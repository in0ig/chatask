<template>
  <el-card class="dictionary-import-export">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="字典导入" name="import">
        <div class="import-section">
          <el-upload
            ref="uploadRef"
            class="dictionary-uploader"
            drag
            action="#"
            :http-request="handleHttpRequest"
            :before-upload="handleBeforeUpload"
            :on-exceed="handleExceed"
            :limit="1"
            :accept=".xlsx, .xls, .csv"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 .xlsx, .xls, .csv 格式，文件大小不超过 10MB。
              </div>
            </template>
          </el-upload>

          <div v-if="isUploading" class="import-progress">
            <el-progress
              :percentage="uploadPercentage"
              :text-inside="true"
              :stroke-width="20"
              status="success"
            >
              <span>正在导入...</span>
            </el-progress>
          </div>

          <el-result
            v-if="importResult.status !== 'pending'"
            :icon="importResult.status"
            :title="importResult.title"
            :sub-title="importResult.message"
          >
          </el-result>
        </div>
      </el-tab-pane>
      <el-tab-pane label="字典导出" name="export">
        <div class="export-section">
          <p class="export-description">选择要导出的文件格式，然后点击导出按钮。</p>
          <el-form :inline="true" label-width="100px">
            <el-form-item label="导出格式">
              <el-select v-model="exportFormat" placeholder="请选择格式">
                <el-option label="Excel (.xlsx)" value="excel"></el-option>
                <el-option label="CSV (.csv)" value="csv"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="handleExport"
                :loading="isExporting"
                :disabled="!dictionaryId"
              >
                <el-icon><Download /></el-icon>
                导出数据
              </el-button>
            </el-form-item>
          </el-form>
           <div v-if="!dictionaryId" class="export-tip">
            <el-alert
              title="请先选择一个字典以启用导出功能。"
              type="warning"
              show-icon
              :closable="false"
            />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { ElMessage, ElNotification } from 'element-plus';
import { UploadFilled, Download } from '@element-plus/icons-vue';
import type { UploadProps, UploadRequestOptions, UploadInstance } from 'element-plus';

// 假设这是您的 Pinia store
// import { useDataPreparationStore } from '../store/dataPreparation';

// --- Mock Store for demonstration ---
// 您应该替换为真实的 Pinia store
const useDataPreparationStore = () => ({
  importDictionary: async (dictionaryId: string, file: File) => {
    console.log(`正在导入文件 ${file.name} 到字典 ${dictionaryId}`);
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 2000));
    // 模拟成功或失败
    if (file.name.includes('fail')) {
       return { success: false, message: '文件内容格式不正确，请检查标题行。' };
    }
    return { success: true, message: '成功导入 150 条数据。' };
  },
  exportDictionary: async (dictionaryId: string, format: 'excel' | 'csv') => {
    console.log(`正在从字典 ${dictionaryId} 导出为 ${format} 格式`);
    // 模拟API调用和文件下载
    await new Promise(resolve => setTimeout(resolve, 1500));
    const blob = new Blob([`header1,header2\nvalue1,value2`], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `dictionary_${dictionaryId}.${format === 'excel' ? 'xlsx' : 'csv'}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }
});
// --- End of Mock Store ---


// Props
const props = defineProps({
  dictionaryId: {
    type: String,
    required: false
  }
});

const dataPreparationStore = useDataPreparationStore();
const uploadRef = ref<UploadInstance>();

const activeTab = ref('import');
const isUploading = ref(false);
const uploadPercentage = ref(0);
const isExporting = ref(false);
const exportFormat = ref<'excel' | 'csv'>('excel');

type ImportStatus = 'pending' | 'success' | 'error' | 'warning';
const importResult = reactive({
  status: 'pending' as ImportStatus,
  title: '',
  message: '',
});


const allowedFileTypes = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel', 'text/csv'];
const maxFileSize = 10 * 1024 * 1024; // 10MB

const handleBeforeUpload: UploadProps['beforeUpload'] = (rawFile) => {
  // 重置导入结果
  importResult.status = 'pending';

  if (!allowedFileTypes.includes(rawFile.type)) {
    ElMessage.error('文件格式不正确! 请上传 .xlsx, .xls, 或 .csv 文件。');
    return false;
  }
  if (rawFile.size > maxFileSize) {
    ElMessage.error(`文件大小不能超过 ${maxFileSize / 1024 / 1024}MB!`);
    return false;
  }
  if (!props.dictionaryId) {
    ElMessage.error('请先选择一个字典再进行导入操作。');
    return false;
  }
  return true;
};

const handleHttpRequest = async (options: UploadRequestOptions) => {
  if (!props.dictionaryId) return;

  isUploading.value = true;
  uploadPercentage.value = 0;

  // 模拟上传进度
  const interval = setInterval(() => {
    if (uploadPercentage.value < 90) {
      uploadPercentage.value += 10;
    }
  }, 200);

  try {
    const result = await dataPreparationStore.importDictionary(props.dictionaryId, options.file);
    uploadPercentage.value = 100;
    
    if (result.success) {
      importResult.status = 'success';
      importResult.title = '导入成功';
      importResult.message = result.message;
      ElNotification({
        title: '成功',
        message: '字典数据已成功导入。',
        type: 'success',
      });
    } else {
      importResult.status = 'error';
      importResult.title = '导入失败';
      importResult.message = result.message;
       ElNotification({
        title: '失败',
        message: `导入过程中发生错误：${result.message}`,
        type: 'error',
      });
    }
  } catch (error: any) {
    importResult.status = 'error';
    importResult.title = '导入异常';
    importResult.message = error.message || '发生未知网络错误，请稍后重试。';
    ElNotification({
      title: '异常',
      message: `导入过程中发生异常：${importResult.message}`,
      type: 'error',
    });
  } finally {
    clearInterval(interval);
    isUploading.value = false;
    uploadRef.value?.clearFiles(); // 清空已上传文件列表
  }
};

const handleExceed: UploadProps['onExceed'] = (files) => {
  uploadRef.value!.clearFiles();
  const file = files[0];
  uploadRef.value!.handleStart(file);
  uploadRef.value!.submit();
};


const handleExport = async () => {
  if (!props.dictionaryId) {
    ElMessage.warning('没有可导出的字典，请先选择一个字典。');
    return;
  }
  isExporting.value = true;
  try {
    await dataPreparationStore.exportDictionary(props.dictionaryId, exportFormat.value);
    ElNotification({
      title: '导出成功',
      message: `字典数据已开始下载为 ${exportFormat.value.toUpperCase()} 文件。`,
      type: 'success',
    });
  } catch (error: any) {
    ElNotification({
      title: '导出失败',
      message: error.message || '导出过程中发生未知错误。',
      type: 'error',
    });
  } finally {
    isExporting.value = false;
  }
};

</script>

<style scoped>
.dictionary-import-export {
  width: 100%;
  max-width: 800px;
  margin: 20px auto;
}

.import-section, .export-section {
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.dictionary-uploader {
  width: 100%;
  margin-bottom: 20px;
}

.el-upload__tip {
  text-align: center;
  margin-top: 10px;
  color: #909399;
}

.import-progress {
  width: 100%;
  margin-top: 20px;
}

.export-description {
  color: #606266;
  margin-bottom: 25px;
  text-align: center;
}

.export-section .el-form {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    gap: 20px;
}

.export-tip {
  margin-top: 20px;
  width: 100%;
}

@media (max-width: 768px) {
  .export-section .el-form {
    flex-direction: column;
    align-items: stretch;
  }

  .export-section .el-form-item {
    margin-right: 0;
    width: 100%;
  }

  .export-section .el-button {
    width: 100%;
  }
}
</style>
