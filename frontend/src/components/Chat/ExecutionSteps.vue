<template>
  <div class="execution-steps">
    <!-- 步骤列表 -->
    <div 
      v-for="(step, index) in steps" 
      :key="index"
      class="step-card"
      :class="{ 'collapsed': step.collapsed }"
    >
      <!-- 步骤标题（可点击折叠/展开） -->
      <div class="step-header" @click="toggleStep(index)">
        <div class="step-title">
          <span class="step-icon">{{ step.icon }}</span>
          <span class="step-name">{{ step.title }}</span>
          <span v-if="step.status === 'success'" class="status-icon success">✅</span>
          <span v-else-if="step.status === 'loading'" class="status-icon loading">⏳</span>
          <span v-else-if="step.status === 'error'" class="status-icon error">❌</span>
        </div>
        <span class="collapse-icon">{{ step.collapsed ? '▶' : '▼' }}</span>
      </div>

      <!-- 步骤内容 -->
      <div v-if="!step.collapsed" class="step-content">
        <!-- 意图识别 -->
        <div v-if="step.stage === 'intent_recognition'" class="intent-content">
          <p>{{ step.content }}</p>
        </div>

        <!-- 智能选表 -->
        <div v-else-if="step.stage === 'table_selection'" class="table-content">
          <div v-if="step.tables && step.tables.length > 0">
            <p class="section-title">{{ t('execution_detail.selectedTables', { count: step.tables.length }) }}</p>
            <div v-for="(table, tIndex) in step.tables" :key="tIndex" class="table-detail">
              <div class="table-name">📊 {{ table.tableName || table }}</div>
              
              <!-- 表描述 -->
              <div v-if="table.description" class="table-description">
                {{ table.description }}
              </div>

              <!-- 字段列表 -->
              <div v-if="table.fields && table.fields.length > 0" class="fields-section">
                <p class="subsection-title">{{ t('execution_detail.fieldList', { count: table.fields.length }) }}</p>
                <div class="fields-list">
                  <div v-for="(field, fIndex) in table.fields" :key="fIndex" class="field-item">
                    <span class="field-name">{{ field.fieldName }}</span>
                    <span class="field-type">{{ field.dataType }}</span>
                    <span v-if="field.isPrimaryKey" class="field-badge primary">{{ t('execution_detail.primaryKey') }}</span>
                    <span v-if="!field.isNullable" class="field-badge required">{{ t('execution_detail.notNull') }}</span>
                    <div v-if="field.description" class="field-description">
                      {{ field.description }}
                    </div>
                    <!-- 数据字典 -->
                    <div v-if="field.dictionary" class="field-dictionary">
                      <span class="dict-label">{{ t('execution_detail.dict') }}</span>
                      <span class="dict-name">{{ field.dictionary.name }}</span>
                      <span v-if="field.dictionary.items" class="dict-items">
                        ({{ field.dictionary.items.join(', ') }})
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 表关联 -->
              <div v-if="table.relations && table.relations.length > 0" class="relations-section">
                <p class="subsection-title">{{ t('execution_detail.tableRelations', { count: table.relations.length }) }}</p>
                <div class="relations-list">
                  <div v-for="(rel, rIndex) in table.relations" :key="rIndex" class="relation-item">
                    <span class="relation-name">{{ rel.relationName || t('execution_detail.unnamed') }}</span>
                    <div class="relation-detail">
                      {{ rel.primaryTable }}.{{ rel.primaryField }} 
                      → {{ rel.foreignTable }}.{{ rel.foreignField }}
                      <span class="join-type">({{ rel.joinType || 'INNER JOIN' }})</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <p v-else>{{ step.content }}</p>
        </div>

        <!-- SQL生成 -->
        <div v-else-if="step.stage === 'sql_generation'" class="sql-content">
          <pre class="sql-code"><code>{{ step.sql || step.content }}</code></pre>
        </div>

        <!-- SQL执行 -->
        <div v-else-if="step.stage === 'sql_execution'" class="execution-content">
          <p>{{ step.content }}</p>
          <div v-if="step.executionTime" class="execution-stats">
            <span>{{ t('execution_detail.execTime', { time: step.executionTime }) }}</span>
            <span v-if="step.totalRows">{{ t('execution_detail.returnRows', { rows: step.totalRows }) }}</span>
          </div>
        </div>

        <!-- 数据分析 -->
        <div v-else-if="step.stage === 'data_analysis'" class="analysis-content">
          <p>{{ step.content }}</p>
        </div>

        <!-- 默认内容 -->
        <div v-else class="default-content">
          <p>{{ step.content }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// 定义步骤接口
interface ExecutionStep {
  title: string
  icon: string
  stage: string
  status: 'loading' | 'success' | 'error'
  content: string
  collapsed: boolean
  sql?: string
  tables?: any[]
  executionTime?: number
  totalRows?: number
}

// Props
const props = defineProps<{
  steps: ExecutionStep[]
  defaultCollapsed?: boolean
}>()

// 切换步骤折叠状态
const toggleStep = (index: number) => {
  props.steps[index].collapsed = !props.steps[index].collapsed
}

// 监听步骤变化，确保新步骤默认展开
watch(() => props.steps, (newSteps) => {
  newSteps.forEach(step => {
    if (step.collapsed === undefined) {
      step.collapsed = props.defaultCollapsed || false
    }
  })
}, { deep: true, immediate: true })
</script>

<style scoped>
.execution-steps {
  margin: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-card {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.step-card.collapsed {
  background: #ffffff;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.step-header:hover {
  background: #e9ecef;
}

.step-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  font-size: 14px;
}

.step-icon {
  font-size: 18px;
}

.status-icon {
  font-size: 16px;
  margin-left: 4px;
}

.status-icon.loading {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.collapse-icon {
  color: #6c757d;
  font-size: 12px;
  transition: transform 0.3s;
}

.step-content {
  padding: 0 16px 16px 16px;
  font-size: 13px;
  line-height: 1.6;
  color: #495057;
}

/* 意图识别样式 */
.intent-content p {
  margin: 0;
}

/* 智能选表样式 */
.table-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  font-weight: 600;
  color: #212529;
  margin: 0 0 8px 0;
}

.table-detail {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
}

.table-name {
  font-weight: 600;
  color: #0d6efd;
  margin-bottom: 8px;
  font-size: 14px;
}

.table-description {
  color: #6c757d;
  font-size: 12px;
  margin-bottom: 12px;
  font-style: italic;
}

.subsection-title {
  font-weight: 500;
  color: #495057;
  margin: 12px 0 8px 0;
  font-size: 13px;
}

.fields-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-item {
  background: #f8f9fa;
  padding: 8px 12px;
  border-radius: 4px;
  border-left: 3px solid #0d6efd;
}

.field-name {
  font-weight: 500;
  color: #212529;
  margin-right: 8px;
}

.field-type {
  color: #6c757d;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  background: #e9ecef;
  padding: 2px 6px;
  border-radius: 3px;
  margin-right: 8px;
}

.field-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  margin-right: 4px;
}

.field-badge.primary {
  background: #ffc107;
  color: #000;
}

.field-badge.required {
  background: #dc3545;
  color: white;
}

.field-description {
  color: #6c757d;
  font-size: 12px;
  margin-top: 4px;
}

.field-dictionary {
  margin-top: 4px;
  font-size: 12px;
  color: #6c757d;
}

.dict-label {
  font-weight: 500;
}

.dict-name {
  color: #0d6efd;
  margin: 0 4px;
}

.dict-items {
  color: #6c757d;
  font-style: italic;
}

.relations-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.relation-item {
  background: #fff3cd;
  padding: 8px 12px;
  border-radius: 4px;
  border-left: 3px solid #ffc107;
}

.relation-name {
  font-weight: 500;
  color: #212529;
  display: block;
  margin-bottom: 4px;
}

.relation-detail {
  font-size: 12px;
  color: #6c757d;
  font-family: 'Courier New', monospace;
}

.join-type {
  color: #0d6efd;
  margin-left: 4px;
}

/* SQL生成样式 */
.sql-content {
  background: #282c34;
  border-radius: 6px;
  overflow: hidden;
}

.sql-code {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
}

.sql-code code {
  color: #abb2bf;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 13px;
  line-height: 1.5;
}

/* SQL执行样式 */
.execution-content p {
  margin: 0 0 8px 0;
}

.execution-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #6c757d;
  background: white;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

.execution-stats span {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 数据分析样式 */
.analysis-content p {
  margin: 0;
  white-space: pre-wrap;
}

/* 默认内容样式 */
.default-content p {
  margin: 0;
  white-space: pre-wrap;
}
</style>
