<template>
  <div class="sql-builder">
    <!-- 头部工具栏 -->
    <div class="sql-builder-header">
      <div class="header-left">
        <h3 class="title">SQL 建表</h3>
        <span class="subtitle">通过 SQL 脚本创建数据表</span>
      </div>
      <div class="header-right">
        <el-button 
          type="primary" 
          :icon="Play" 
          :loading="executing"
          :disabled="!canExecute"
          @click="executeSql"
        >
          执行 SQL
        </el-button>
        <el-button 
          :icon="DocumentChecked" 
          :loading="validating"
          @click="validateSql"
        >
          验证语法
        </el-button>
        <el-button 
          :icon="Refresh" 
          @click="clearEditor"
        >
          清空
        </el-button>
      </div>
    </div>

    <!-- 配置区域 -->
    <div class="sql-builder-config">
      <el-form :model="config" label-width="100px" inline>
        <el-form-item label="数据源">
          <el-select 
            v-model="config.sourceId" 
            placeholder="选择数据源"
            style="width: 200px"
            @change="onSourceChange"
          >
            <el-option
              v-for="source in dataSources"
              :key="source.id"
              :label="source.name"
              :value="source.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="表名">
          <el-input
            v-model="config.tableName"
            placeholder="可选，从 SQL 中自动提取"
            style="width: 200px"
          />
        </el-form-item>
      </el-form>
    </div>

    <!-- SQL 编辑器 -->
    <div class="sql-builder-editor">
      <div class="editor-header">
        <span class="editor-title">SQL 脚本</span>
        <div class="editor-info">
          <span v-if="sqlStats.lines > 0" class="stats">
            {{ sqlStats.lines }} 行 | {{ sqlStats.characters }} 字符
          </span>
          <span v-if="validationResult && !validationResult.isValid" class="error-count">
            {{ validationResult.errors.length }} 个错误
          </span>
        </div>
      </div>
      <div ref="editorContainer" class="editor-container"></div>
    </div>

    <!-- 验证结果 -->
    <div v-if="validationResult && !validationResult.isValid" class="validation-errors">
      <div class="errors-header">
        <el-icon class="error-icon"><WarningFilled /></el-icon>
        <span>语法错误 ({{ validationResult.errors.length }})</span>
      </div>
      <div class="errors-list">
        <div 
          v-for="(error, index) in validationResult.errors" 
          :key="index"
          class="error-item"
          :class="{ 'error': error.severity === 'error', 'warning': error.severity === 'warning' }"
        >
          <span class="error-position">第 {{ error.line }} 行，第 {{ error.column }} 列:</span>
          <span class="error-message">{{ error.message }}</span>
        </div>
      </div>
    </div>

    <!-- 执行结果 -->
    <div v-if="executionResult" class="execution-result">
      <div class="result-header">
        <el-icon 
          :class="{ 
            'success-icon': executionResult.success, 
            'error-icon': !executionResult.success 
          }"
        >
          <SuccessFilled v-if="executionResult.success" />
          <CircleCloseFilled v-else />
        </el-icon>
        <span>执行结果</span>
        <span v-if="executionResult.executionTime" class="execution-time">
          ({{ executionResult.executionTime }}ms)
        </span>
      </div>
      
      <div class="result-content">
        <div v-if="executionResult.success" class="success-result">
          <p class="result-message">{{ executionResult.message }}</p>
          <div v-if="executionResult.rowsAffected !== undefined" class="affected-rows">
            影响行数: {{ executionResult.rowsAffected }}
          </div>
          
          <!-- 数据预览 -->
          <div v-if="executionResult.data && executionResult.data.length > 0" class="data-preview">
            <div class="preview-header">数据预览 (前 {{ Math.min(executionResult.data.length, 10) }} 行)</div>
            <el-table 
              :data="executionResult.data.slice(0, 10)" 
              size="small"
              max-height="300"
              stripe
            >
              <el-table-column
                v-for="column in executionResult.columns"
                :key="column.name"
                :prop="column.name"
                :label="column.name"
                :width="120"
                show-overflow-tooltip
              />
            </el-table>
          </div>
        </div>
        
        <div v-else class="error-result">
          <p class="result-message error">{{ executionResult.message }}</p>
        </div>
      </div>
    </div>

    <!-- SQL 模板 -->
    <div class="sql-templates">
      <div class="templates-header">
        <span>常用模板</span>
        <el-button text @click="showTemplates = !showTemplates">
          {{ showTemplates ? '收起' : '展开' }}
        </el-button>
      </div>
      <div v-show="showTemplates" class="templates-list">
        <el-button
          v-for="template in sqlTemplates"
          :key="template.name"
          size="small"
          @click="insertTemplate(template.sql)"
        >
          {{ template.name }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Play, 
  DocumentChecked, 
  Refresh, 
  WarningFilled, 
  SuccessFilled, 
  CircleCloseFilled 
} from '@element-plus/icons-vue'
import { EditorView, basicSetup } from 'codemirror'
import { EditorState } from '@codemirror/state'
import { sql } from '@codemirror/lang-sql'
import { linter, lintGutter } from '@codemirror/lint'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import { dataTableApi, type SqlExecutionResult, type SqlValidationResult } from '@/services/dataTableApi'

// Props 和 Emits
interface Props {
  visible?: boolean
}

interface Emits {
  (e: 'success', table: any): void
  (e: 'close'): void
}

const props = withDefaults(defineProps<Props>(), {
  visible: false
})

const emit = defineEmits<Emits>()

// Store
const dataPreparationStore = useDataPreparationStore()

// 响应式数据
const editorContainer = ref<HTMLElement>()
const executing = ref(false)
const validating = ref(false)
const showTemplates = ref(false)

// 配置
const config = reactive({
  sourceId: '',
  tableName: ''
})

// 编辑器实例
let editorView: EditorView | null = null

// SQL 内容
const sqlContent = ref('')

// 验证结果
const validationResult = ref<SqlValidationResult | null>(null)

// 执行结果
const executionResult = ref<SqlExecutionResult | null>(null)

// 计算属性
const dataSources = computed(() => dataPreparationStore.dataSourcesData)

const canExecute = computed(() => {
  return config.sourceId && sqlContent.value.trim().length > 0 && !executing.value
})

const sqlStats = computed(() => {
  const content = sqlContent.value
  return {
    lines: content.split('\n').length,
    characters: content.length
  }
})

// SQL 模板
const sqlTemplates = [
  {
    name: '创建表',
    sql: `CREATE TABLE example_table (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`
  },
  {
    name: '创建索引',
    sql: `CREATE INDEX idx_name ON example_table (name);`
  },
  {
    name: '插入数据',
    sql: `INSERT INTO example_table (name, email) VALUES 
('张三', 'zhangsan@example.com'),
('李四', 'lisi@example.com');`
  }
]

// SQL 语法检查器
const sqlLinter = linter(async (view) => {
  if (!config.sourceId || !sqlContent.value.trim()) {
    return []
  }

  try {
    const result = await dataTableApi.validateSql(sqlContent.value, config.sourceId)
    validationResult.value = result
    
    return result.errors.map(error => ({
      from: view.state.doc.line(error.line).from + error.column - 1,
      to: view.state.doc.line(error.line).from + error.column,
      severity: error.severity,
      message: error.message
    }))
  } catch (error) {
    console.error('SQL 验证失败:', error)
    return []
  }
})

// 初始化编辑器
const initEditor = () => {
  if (!editorContainer.value) return

  const startState = EditorState.create({
    doc: sqlContent.value,
    extensions: [
      basicSetup,
      sql(),
      lintGutter(),
      sqlLinter,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          sqlContent.value = update.state.doc.toString()
        }
      }),
      EditorView.theme({
        '&': {
          height: '300px',
          fontSize: '14px'
        },
        '.cm-content': {
          padding: '12px',
          minHeight: '300px'
        },
        '.cm-focused': {
          outline: 'none'
        },
        '.cm-editor': {
          border: '1px solid #dcdfe6',
          borderRadius: '4px'
        },
        '.cm-editor.cm-focused': {
          borderColor: '#409eff'
        }
      })
    ]
  })

  editorView = new EditorView({
    state: startState,
    parent: editorContainer.value
  })
}

// 销毁编辑器
const destroyEditor = () => {
  if (editorView) {
    editorView.destroy()
    editorView = null
  }
}

// 清空编辑器
const clearEditor = () => {
  if (editorView) {
    editorView.dispatch({
      changes: {
        from: 0,
        to: editorView.state.doc.length,
        insert: ''
      }
    })
  }
  sqlContent.value = ''
  validationResult.value = null
  executionResult.value = null
}

// 插入模板
const insertTemplate = (template: string) => {
  if (editorView) {
    const currentContent = editorView.state.doc.toString()
    const insertText = currentContent ? '\n\n' + template : template
    
    editorView.dispatch({
      changes: {
        from: editorView.state.doc.length,
        insert: insertText
      }
    })
    
    // 聚焦到编辑器
    editorView.focus()
  }
}

// 验证 SQL
const validateSql = async () => {
  if (!config.sourceId || !sqlContent.value.trim()) {
    ElMessage.warning('请选择数据源并输入 SQL 语句')
    return
  }

  validating.value = true
  try {
    const result = await dataTableApi.validateSql(sqlContent.value, config.sourceId)
    validationResult.value = result
    
    if (result.isValid) {
      ElMessage.success('SQL 语法验证通过')
    } else {
      ElMessage.error(`发现 ${result.errors.length} 个语法错误`)
    }
  } catch (error: any) {
    console.error('SQL 验证失败:', error)
    ElMessage.error('验证失败: ' + (error.message || '未知错误'))
  } finally {
    validating.value = false
  }
}

// 执行 SQL
const executeSql = async () => {
  if (!canExecute.value) {
    return
  }

  executing.value = true
  executionResult.value = null
  
  try {
    const result = await dataPreparationStore.createTableFromSQL(
      sqlContent.value,
      config.sourceId,
      config.tableName
    )
    
    if (result.success) {
      executionResult.value = {
        success: true,
        message: '表创建成功',
        rowsAffected: 1,
        executionTime: 150 // 模拟执行时间
      }
      
      ElMessage.success('SQL 执行成功，数据表已创建')
      emit('success', result.data)
    } else {
      executionResult.value = {
        success: false,
        message: result.message || 'SQL 执行失败'
      }
      
      ElMessage.error('SQL 执行失败: ' + result.message)
    }
  } catch (error: any) {
    console.error('SQL 执行失败:', error)
    executionResult.value = {
      success: false,
      message: error.message || '执行过程中发生未知错误'
    }
    ElMessage.error('SQL 执行失败: ' + (error.message || '未知错误'))
  } finally {
    executing.value = false
  }
}

// 数据源变化处理
const onSourceChange = () => {
  // 清除之前的验证结果
  validationResult.value = null
  executionResult.value = null
}

// 生命周期
onMounted(() => {
  // 加载数据源
  dataPreparationStore.fetchDataSources()
  
  // 初始化编辑器
  setTimeout(() => {
    initEditor()
  }, 100)
})

onUnmounted(() => {
  destroyEditor()
})

// 监听可见性变化
watch(() => props.visible, (visible) => {
  if (visible && !editorView) {
    setTimeout(() => {
      initEditor()
    }, 100)
  }
})
</script>

<style scoped lang="scss">
.sql-builder {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;

  .sql-builder-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid #e4e7ed;
    background: #fafafa;

    .header-left {
      .title {
        margin: 0 0 4px 0;
        font-size: 16px;
        font-weight: 600;
        color: #303133;
      }

      .subtitle {
        font-size: 12px;
        color: #909399;
      }
    }

    .header-right {
      display: flex;
      gap: 8px;
    }
  }

  .sql-builder-config {
    padding: 16px 20px;
    border-bottom: 1px solid #e4e7ed;
    background: #fff;
  }

  .sql-builder-editor {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;

    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 20px;
      border-bottom: 1px solid #e4e7ed;
      background: #fafafa;

      .editor-title {
        font-weight: 500;
        color: #303133;
      }

      .editor-info {
        display: flex;
        gap: 16px;
        font-size: 12px;

        .stats {
          color: #909399;
        }

        .error-count {
          color: #f56c6c;
        }
      }
    }

    .editor-container {
      flex: 1;
      padding: 20px;
      min-height: 300px;
    }
  }

  .validation-errors {
    border-top: 1px solid #e4e7ed;
    background: #fef0f0;

    .errors-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 20px;
      font-weight: 500;
      color: #f56c6c;
      border-bottom: 1px solid #fbc4c4;

      .error-icon {
        font-size: 16px;
      }
    }

    .errors-list {
      max-height: 200px;
      overflow-y: auto;

      .error-item {
        padding: 8px 20px;
        border-bottom: 1px solid #fbc4c4;
        font-size: 12px;

        &:last-child {
          border-bottom: none;
        }

        &.error {
          color: #f56c6c;
        }

        &.warning {
          color: #e6a23c;
        }

        .error-position {
          font-weight: 500;
          margin-right: 8px;
        }

        .error-message {
          color: #606266;
        }
      }
    }
  }

  .execution-result {
    border-top: 1px solid #e4e7ed;

    .result-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 20px;
      font-weight: 500;
      border-bottom: 1px solid #e4e7ed;

      .success-icon {
        color: #67c23a;
        font-size: 16px;
      }

      .error-icon {
        color: #f56c6c;
        font-size: 16px;
      }

      .execution-time {
        font-size: 12px;
        color: #909399;
        font-weight: normal;
      }
    }

    .result-content {
      padding: 16px 20px;

      .success-result {
        .result-message {
          margin: 0 0 12px 0;
          color: #67c23a;
          font-weight: 500;
        }

        .affected-rows {
          margin-bottom: 16px;
          font-size: 14px;
          color: #606266;
        }

        .data-preview {
          .preview-header {
            margin-bottom: 12px;
            font-weight: 500;
            color: #303133;
          }
        }
      }

      .error-result {
        .result-message.error {
          margin: 0;
          color: #f56c6c;
          font-weight: 500;
        }
      }
    }
  }

  .sql-templates {
    border-top: 1px solid #e4e7ed;
    background: #fafafa;

    .templates-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 20px;
      font-weight: 500;
      color: #303133;
    }

    .templates-list {
      padding: 0 20px 16px 20px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
  }
}
</style>