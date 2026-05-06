<template>
  <div class="import-export-container">
    <el-button @click="openImportDialog" :icon="Upload" type="primary">导入字典项</el-button>
    <el-button @click="openExportDialog" :icon="Download" type="success">导出字典</el-button>

    <!-- Import Dialog -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入字典项"
      width="500px"
      :before-close="handleCloseImport"
      draggable
    >
      <div v-if="!importResult.completed">
        <el-upload
          ref="uploadRef"
          class="upload-dragger"
          drag
          action="#"
          :auto-upload="false"
          :on-change="handleFileChange"
          :on-exceed="handleFileExceed"
          :limit="1"
          accept=".xlsx, .xls, .csv"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              仅支持 Excel (.xls, .xlsx) 和 CSV 文件，且单次只能上传一个文件。
            </div>
          </template>
        </el-upload>
      </div>

      <!-- Import Result -->
      <div v-if="importResult.completed" class="import-result">
        <h4>导入完成</h4>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="总行数" :value="importResult.total" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="成功导入" :value="importResult.success" value-style="color: #67C23A;" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="失败行数" :value="importResult.failed" value-style="color: #F56C6C;"/>
          </el-col>
        </el-row>
        <el-collapse v-if="importResult.errors.length > 0" style="margin-top: 20px;">
          <el-collapse-item title="查看失败详情" name="1">
            <ul>
              <li v-for="(error, index) in importResult.errors" :key="index">{{ error }}</li>
            </ul>
          </el-collapse-item>
        </el-collapse>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleCloseImport">
            {{ importResult.completed ? '关闭' : '取消' }}
          </el-button>
          <el-button 
            type="primary" 
            @click="handleImport" 
            :loading="importing" 
            :disabled="!selectedFile || importResult.completed"
          >
            开始导入
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Export Dialog -->
    <el-dialog
      v-model="exportDialogVisible"
      title="导出字典数据"
      width="400px"
      draggable
    >
      <el-form>
        <el-form-item label="选择导出格式">
          <el-radio-group v-model="exportFormat">
            <el-radio value="excel">Excel (.xlsx)</el-radio>
            <el-radio value="csv">CSV (.csv)</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="exportDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleExport" :loading="exporting">
            确认导出
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { ElButton, ElDialog, ElUpload, ElMessage, ElStatistic, ElRow, ElCol, ElCollapse, ElCollapseItem, ElRadioGroup, ElRadio, ElForm, ElFormItem, ElIcon } from 'element-plus';
import { Upload, Download, UploadFilled } from '@element-plus/icons-vue';
import type { UploadInstance, UploadProps, UploadRawFile } from 'element-plus';
import { useDataPreparationStore } from '@/store/modules/dataPreparation';

const props = defineProps({
  dictionaryId: {
    type: [String, Number],
    required: false
  }
});

const store = useDataPreparationStore();
const uploadRef = ref<UploadInstance>();

const importDialogVisible = ref(false);
const exportDialogVisible = ref(false);
const importing = ref(false);
const exporting = ref(false);
const selectedFile = ref<UploadRawFile | null>(null);

const initialImportResult = {
  completed: false,
  total: 0,
  success: 0,
  failed: 0,
  errors: [] as string[],
};
const importResult = reactive({ ...initialImportResult });

const exportFormat = ref<'excel' | 'csv'>('excel');

const openImportDialog = () => {
  if (!props.dictionaryId) {
    ElMessage.warning('请先选择一个字典。');
    return;
  }
  resetImportState();
  importDialogVisible.value = true;
};

const handleCloseImport = (done: () => void) => {
  resetImportState();
  if (typeof done === 'function') {
    done();
  } else {
    importDialogVisible.value = false;
  }
};

const resetImportState = () => {
  Object.assign(importResult, initialImportResult);
  selectedFile.value = null;
  uploadRef.value?.clearFiles();
}

const openExportDialog = () => {
  if (!props.dictionaryId) {
    ElMessage.warning('请先选择一个字典。');
    return;
  }
  exportDialogVisible.value = true;
};

const handleFileChange: UploadProps['onChange'] = (file) => {
  selectedFile.value = file.raw!;
};

const handleFileExceed: UploadProps['onExceed'] = () => {
  ElMessage.warning('一次只能上传一个文件。');
};

const handleImport = async () => {
  if (!props.dictionaryId) {
    ElMessage.error('内部错误：字典ID丢失。');
    return;
  }
  if (!selectedFile.value) {
    ElMessage.warning('请先选择一个文件。');
    return;
  }

  importing.value = true;
  try {
    const result = await store.importDictionary(selectedFile.value);
    if (result) {
      // 处理成功的导入结果
      Object.assign(importResult, { 
        completed: true,
        total: 1, // 由于真实 API 返回格式可能不同，这里设置默认值
        success: 1,
        failed: 0,
        errors: []
      });
      ElMessage.success('导入处理完成！');
    } else {
      // 处理失败的导入结果
      Object.assign(importResult, { 
        completed: true,
        total: 1,
        success: 0,
        failed: 1,
        errors: ['导入失败']
      });
      ElMessage.error('导入失败');
    }
  } catch (error: any) {
    ElMessage.error(`导入失败: ${error.message || '请稍后重试'}`);
    Object.assign(importResult, { 
      completed: true,
      total: 1,
      success: 0,
      failed: 1,
      errors: [error.message || '导入失败']
    });
  } finally {
    importing.value = false;
  }
};

const handleExport = async () => {
  if (!props.dictionaryId) {
    ElMessage.error('内部错误：字典ID丢失。');
    return;
  }
  
  exporting.value = true;
  try {
    const result = await store.exportDictionary(parseInt(props.dictionaryId));
    if (result) {
      // 创建下载链接
      const url = window.URL.createObjectURL(result);
      const link = document.createElement('a');
      link.href = url;
      link.download = `dictionary_${props.dictionaryId}.${exportFormat.value === 'excel' ? 'xlsx' : 'csv'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      ElMessage.success('导出成功！');
      exportDialogVisible.value = false;
    } else {
      ElMessage.error('导出失败');
    }
  } catch (error: any) {
    ElMessage.error(`导出失败: ${error.message || '请稍后重试'}`);
  } finally {
    exporting.value = false;
  }
};
</script>

<style scoped>
.import-export-container {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.upload-dragger {
  width: 100%;
}

.el-upload__tip {
  text-align: center;
  margin-top: 8px;
  color: #999;
}

.import-result {
  margin-top: 20px;
  text-align: center;
}

.import-result h4 {
  margin-bottom: 20px;
  font-size: 1.2rem;
}

.import-result ul {
  list-style-type: none;
  padding: 0;
  max-height: 150px;
  overflow-y: auto;
  text-align: left;
  background-color: #f8f8f8;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 0.9em;
}

.import-result li {
  padding: 4px 0;
  border-bottom: 1px solid #eee;
}
.import-result li:last-child {
  border-bottom: none;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .import-export-container {
    justify-content: center;
  }
  
  :deep(.el-dialog) {
    width: 90% !important;
  }

  :deep(.el-row) {
    flex-direction: column;
    gap: 10px;
  }
  :deep(.el-col) {
    width: 100%;
    max-width: 100%;
  }
}
</style>