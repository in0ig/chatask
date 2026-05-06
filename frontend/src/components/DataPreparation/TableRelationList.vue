<template>
  <div class="table-relation-list">
    <!-- Header with search and controls -->
    <div class="header">
      <h2>表关联列表</h2>
      <div class="controls">
        <div class="search-box">
          <input 
            v-model="searchTerm" 
            type="text" 
            placeholder="搜索表名..." 
            class="search-input"
          >
          <button @click="clearSearch" class="clear-btn" title="清除搜索">
            ×
          </button>
        </div>
        
        <div class="filter-group">
          <label for="relationType">关联类型:</label>
          <select 
            v-model="selectedRelationType" 
            id="relationType" 
            class="filter-select"
          >
            <option value="">全部</option>
            <option value="one_to_one">一对一</option>
            <option value="one_to_many">一对多</option>
            <option value="many_to_one">多对一</option>
            <option value="many_to_many">多对多</option>
          </select>
        </div>
        
        <button 
          @click="openAddRelationModal" 
          class="add-btn"
        >
          新增关联
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>正在加载表关联数据...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button @click="fetchRelations" class="retry-btn">重试</button>
    </div>

    <!-- Empty state -->
    <div v-else-if="filteredRelations.length === 0" class="empty-state">
      <p class="empty-message">暂无表关联数据</p>
      <button @click="openAddRelationModal" class="add-btn">新增关联</button>
    </div>

    <!-- Table with data -->
    <div v-else class="table-container">
      <div class="table-actions">
        <div class="bulk-actions">
          <input 
            type="checkbox" 
            :checked="allSelected" 
            @change="toggleAllSelection" 
            class="select-all-checkbox"
          >
          <label class="select-all-label">全选</label>
          <button 
            @click="deleteSelectedRelations" 
            :disabled="selectedRelations.length === 0"
            class="delete-selected-btn"
          >
            批量删除 ({{ selectedRelations.length }})
          </button>
        </div>
      </div>
      
      <table class="relation-table">
        <thead>
          <tr>
            <th style="width: 40px;">
              <input 
                type="checkbox" 
                :checked="allSelected" 
                @change="toggleAllSelection" 
                class="select-all-checkbox"
              >
            </th>
            <th>主表</th>
            <th>主表字段</th>
            <th>从表</th>
            <th>从表字段</th>
            <th>关联类型</th>
            <th>状态</th>
            <th>创建时间</th>
            <th style="width: 120px;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="relation in paginatedRelations" 
            :key="relation.id"
            :class="{ 'inactive-row': !relation.is_active }"
          >
            <td>
              <input 
                type="checkbox" 
                :checked="selectedRelations.includes(relation.id)" 
                @change="toggleSelection(relation.id)" 
                class="row-checkbox"
              >
            </td>
            <td>{{ relation.source_table }}</td>
            <td>{{ relation.source_column }}</td>
            <td>{{ relation.target_table }}</td>
            <td>{{ relation.target_column }}</td>
            <td>
              <span class="relation-type">
                {{ getRelationTypeLabel(relation.relation_type) }}
              </span>
            </td>
            <td>
              <span 
                :class="['status-badge', relation.is_active ? 'active' : 'inactive']"
              >
                {{ relation.is_active ? '有效' : '无效' }}
              </span>
            </td>
            <td>{{ formatDate(relation.created_at) }}</td>
            <td class="actions">
              <button 
                @click="openEditRelationModal(relation)" 
                class="action-btn edit-btn"
                title="编辑"
              >
                编辑
              </button>
              <button 
                @click="confirmDeleteRelation(relation)" 
                class="action-btn delete-btn"
                title="删除"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      
      <!-- Pagination -->
      <div class="pagination">
        <button 
          @click="prevPage" 
          :disabled="currentPage === 1"
          class="pagination-btn"
        >
          上一页
        </button>
        <span class="page-info">第 {{ currentPage }} 页，共 {{ totalPages }} 页</span>
        <button 
          @click="nextPage" 
          :disabled="currentPage === totalPages"
          class="pagination-btn"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDataPrepStore } from '@/store/modules/dataPrep'

const store = useDataPrepStore()

// State
const loading = ref(false)
const error = ref('')
const searchTerm = ref('')
const selectedRelationType = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(10)
const selectedRelations = ref([])
const isModalOpen = ref(false)
const editRelation = ref(null)

// Computed properties
const relations = computed(() => store.tableRelations || [])

const filteredRelations = computed(() => {
  return relations.value.filter(relation => {
    const matchesSearch = !searchTerm.value || 
      relation.source_table.toLowerCase().includes(searchTerm.value.toLowerCase()) ||
      relation.target_table.toLowerCase().includes(searchTerm.value.toLowerCase())
    
    const matchesType = !selectedRelationType.value || 
      relation.relation_type === selectedRelationType.value
    
    return matchesSearch && matchesType
  })
})

const totalPages = computed(() => {
  return Math.ceil(filteredRelations.value.length / itemsPerPage.value)
})

const paginatedRelations = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredRelations.value.slice(start, end)
})

const allSelected = computed({
  get() {
    return selectedRelations.value.length === filteredRelations.value.length && filteredRelations.value.length > 0
  },
  set(value) {
    if (value) {
      selectedRelations.value = filteredRelations.value.map(r => r.id)
    } else {
      selectedRelations.value = []
    }
  }
})

// Methods
const fetchRelations = async () => {
  loading.value = true
  error.value = ''
  try {
    await store.fetchTableRelations()
  } catch (err) {
    error.value = '获取表关联数据失败，请稍后重试'
    console.error('Failed to fetch table relations:', err)
  } finally {
    loading.value = false
  }
}

const clearSearch = () => {
  searchTerm.value = ''
}

const toggleSelection = (id) => {
  if (selectedRelations.value.includes(id)) {
    selectedRelations.value = selectedRelations.value.filter(item => item !== id)
  } else {
    selectedRelations.value.push(id)
  }
}

const toggleAllSelection = () => {
  if (allSelected.value) {
    selectedRelations.value = []
  } else {
    selectedRelations.value = filteredRelations.value.map(r => r.id)
  }
}

const deleteSelectedRelations = async () => {
  if (selectedRelations.value.length === 0) return
  
  if (!confirm(`确定要删除 ${selectedRelations.value.length} 个表关联吗？`)) return
  
  try {
    await store.deleteTableRelations(selectedRelations.value)
    selectedRelations.value = []
    // Reset to first page if we've deleted items from current page
    if (currentPage.value > 1 && paginatedRelations.value.length === 0) {
      currentPage.value = 1
    }
  } catch (err) {
    error.value = '删除表关联失败，请稍后重试'
    console.error('Failed to delete table relations:', err)
  }
}

const confirmDeleteRelation = (relation) => {
  if (confirm(`确定要删除表关联：${relation.source_table} -> ${relation.target_table} 吗？`)) {
    deleteRelation(relation.id)
  }
}

const deleteRelation = async (id) => {
  try {
    await store.deleteTableRelation(id)
    // Reset to first page if we've deleted items from current page
    if (currentPage.value > 1 && paginatedRelations.value.length === 0) {
      currentPage.value = 1
    }
  } catch (err) {
    error.value = '删除表关联失败，请稍后重试'
    console.error('Failed to delete table relation:', err)
  }
}

const openAddRelationModal = () => {
  editRelation.value = null
  isModalOpen.value = true
}

const openEditRelationModal = (relation) => {
  editRelation.value = {...relation}
  isModalOpen.value = true
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getRelationTypeLabel = (type) => {
  const labels = {
    one_to_one: '一对一',
    one_to_many: '一对多',
    many_to_one: '多对一',
    many_to_many: '多对多'
  }
  return labels[type] || type
}

// Initialize
fetchRelations()
</script>

<style scoped>
.table-relation-list {
  padding: 20px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.header h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
}

.controls {
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  min-width: 200px;
}

.clear-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.clear-btn:hover {
  background-color: #f0f0f0;
  color: #333;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 5px;
}

.filter-group label {
  font-size: 14px;
  color: #555;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.add-btn {
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.add-btn:hover {
  background-color: #45a049;
}

.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.loading-state .spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state .error-message {
  margin-bottom: 15px;
  color: #e74c3c;
}

.retry-btn {
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
}

.retry-btn:hover {
  background-color: #2980b9;
}

.empty-state .empty-message {
  margin-bottom: 15px;
  font-size: 16px;
}

.table-container {
  margin-top: 20px;
}

.table-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  flex-wrap: wrap;
  gap: 10px;
}

.bulk-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.select-all-checkbox {
  margin-right: 5px;
}

.select-all-label {
  font-size: 14px;
  color: #555;
}

.delete-selected-btn {
  background-color: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.delete-selected-btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.delete-selected-btn:hover:not(:disabled) {
  background-color: #c0392b;
}

.relation-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
  font-size: 14px;
}

.relation-table th,
.relation-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.relation-table th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.relation-table tr:hover {
  background-color: #f5f5f5;
}

.relation-table tbody tr.inactive-row {
  opacity: 0.7;
}

.relation-type {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.relation-type.one_to_one {
  background-color: #e3f2fd;
  color: #1976d2;
}

.relation-type.one_to_many {
  background-color: #e8f5e9;
  color: #388e3c;
}

.relation-type.many_to_one {
  background-color: #fff3e0;
  color: #e65100;
}

.relation-type.many_to_many {
  background-color: #fce4ec;
  color: #880e4f;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background-color: #e8f5e9;
  color: #388e3c;
}

.status-badge.inactive {
  background-color: #f5f5f5;
  color: #999;
}

.actions {
  display: flex;
  gap: 5px;
}

.action-btn {
  padding: 6px 10px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.action-btn.edit-btn {
  background-color: #2196f3;
  color: white;
}

.action-btn.edit-btn:hover {
  background-color: #0b7dda;
}

.action-btn.delete-btn {
  background-color: #e74c3c;
  color: white;
}

.action-btn.delete-btn:hover {
  background-color: #c0392b;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
  padding: 10px;
}

.pagination-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  color: #333;
  cursor: pointer;
  transition: background-color 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background-color: #f5f5f5;
}

.pagination-btn:disabled {
  color: #ccc;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: #666;
}

/* Responsive design */
@media (max-width: 768px) {
  .table-relation-list {
    padding: 15px;
  }
  
  .header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .controls {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  
  .search-box {
    width: 100%;
  }
  
  .search-input {
    width: 100%;
  }
  
  .filter-group {
    width: 100%;
  }
  
  .relation-table {
    font-size: 12px;
  }
  
  .relation-table th,
  .relation-table td {
    padding: 8px;
  }
  
  .actions {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .action-btn {
    width: 100%;
    text-align: center;
  }
}

@media (max-width: 480px) {
  .header h2 {
    font-size: 1.3rem;
  }
  
  .pagination {
    flex-direction: column;
    gap: 8px;
  }
  
  .pagination-btn {
    width: 100%;
    text-align: center;
  }
}
</style>