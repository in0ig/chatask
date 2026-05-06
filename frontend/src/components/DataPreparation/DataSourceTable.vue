<template>
  <div class="data-source-table">
    <el-table
      :data="data"
      :loading="loading"
      stripe
      border
      @sort-change="handleSortChange"
      class="source-table"
      empty-text="暂无数据源"
    >
      <!-- 数据源名称 -->
      <el-table-column
        prop="name"
        label="数据源名称"
        sortable="custom"
        min-width="180"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          <div class="name-cell">
            <el-icon class="source-icon">
              <Coin v-if="row.sourceType === 'DATABASE'" />
              <Document v-else />
            </el-icon>
            <div class="name-content">
              <div class="name-text">{{ row.name }}</div>
              <div class="description-text" v-if="row.description">
                {{ row.description }}
              </div>
            </div>
          </div>
        </template>
      </el-table-column>

      <!-- 数据源类型 -->
      <el-table-column
        prop="sourceType"
        label="类型"
        sortable="custom"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <el-tag
            :type="getTypeTagType(row.sourceType)"
            size="small"
          >
            {{ getTypeLabel(row.sourceType) }}
          </el-tag>
        </template>
      </el-table-column>

      <!-- 数据库类型（仅数据库类型显示） -->
      <el-table-column
        prop="dbType"
        label="数据库类型"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <span v-if="row.sourceType === 'DATABASE' && row.dbType">
            {{ getDbTypeLabel(row.dbType) }}
          </span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>

      <!-- 连接信息 -->
      <el-table-column
        label="连接信息"
        min-width="200"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          <div class="connection-info">
            <div v-if="row.sourceType === 'DATABASE'">
              <div v-if="row.host">
                <el-icon><Link /></el-icon>
                {{ row.host }}{{ row.port ? ':' + row.port : '' }}
              </div>
              <div v-if="row.databaseName" class="db-name">
                <el-icon><Coin /></el-icon>
                {{ row.databaseName }}
              </div>
            </div>
            <div v-else-if="row.sourceType === 'FILE'">
              <div v-if="row.filePath">
                <el-icon><Folder /></el-icon>
                {{ getFileName(row.filePath) }}
              </div>
            </div>
            <span v-else class="text-muted">-</span>
          </div>
        </template>
      </el-table-column>

      <!-- 连接状态 -->
      <el-table-column
        prop="connectionStatus"
        label="连接状态"
        sortable="custom"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <el-tag
            :type="getStatusTagType(row.connectionStatus)"
            size="small"
            :effect="row.connectionStatus === 'TESTING' ? 'plain' : 'dark'"
          >
            <el-icon v-if="row.connectionStatus === 'TESTING'" class="is-loading">
              <Loading />
            </el-icon>
            {{ getStatusLabel(row.connectionStatus) }}
          </el-tag>
        </template>
      </el-table-column>

      <!-- 创建时间 -->
      <el-table-column
        prop="createdAt"
        label="创建时间"
        sortable="custom"
        width="160"
        align="center"
      >
        <template #default="{ row }">
          {{ formatDateTime(row.createdAt) }}
        </template>
      </el-table-column>

      <!-- 更新时间 -->
      <el-table-column
        prop="updatedAt"
        label="更新时间"
        sortable="custom"
        width="160"
        align="center"
      >
        <template #default="{ row }">
          {{ formatDateTime(row.updatedAt) }}
        </template>
      </el-table-column>

      <!-- 操作列 -->
      <el-table-column
        label="操作"
        width="200"
        align="center"
        fixed="right"
      >
        <template #default="{ row }">
          <div class="action-buttons">
            <el-tooltip content="测试连接" placement="top">
              <el-button
                type="primary"
                size="small"
                :icon="Connection"
                circle
                @click="handleTestConnection(row)"
                :loading="row.connectionStatus === 'TESTING'"
              />
            </el-tooltip>
            
            <el-tooltip content="编辑" placement="top">
              <el-button
                type="warning"
                size="small"
                :icon="Edit"
                circle
                @click="handleEdit(row)"
              />
            </el-tooltip>
            
            <el-tooltip content="删除" placement="top">
              <el-button
                type="danger"
                size="small"
                :icon="Delete"
                circle
                @click="handleDelete(row)"
              />
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { 
  Coin, 
  Document, 
  Link, 
  Folder, 
  Loading,
  Connection,
  Edit,
  Delete
} from '@element-plus/icons-vue'
import type { DataSource } from '@/store/modules/dataPreparation'

// Props
interface Props {
  data: DataSource[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

// Emits
const emit = defineEmits<{
  edit: [dataSource: DataSource]
  delete: [dataSource: DataSource]
  testConnection: [dataSource: DataSource]
  sortChange: [{ prop: string; order: string }]
}>()

// 方法
const getTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'DATABASE': '数据库',
    'FILE': '文件'
  }
  return labels[type] || type
}

const getTypeTagType = (type: string): string => {
  const types: Record<string, string> = {
    'DATABASE': 'primary',
    'FILE': 'success'
  }
  return types[type] || 'info'
}

const getDbTypeLabel = (dbType: string): string => {
  const labels: Record<string, string> = {
    'MYSQL': 'MySQL',
    'SQLSERVER': 'SQL Server',
    'POSTGRESQL': 'PostgreSQL',
    'CLICKHOUSE': 'ClickHouse'
  }
  return labels[dbType] || dbType
}

const getStatusLabel = (status: string): string => {
  const labels: Record<string, string> = {
    'CONNECTED': '已连接',
    'DISCONNECTED': '未连接',
    'FAILED': '连接失败',
    'TESTING': '测试中'
  }
  return labels[status] || status
}

const getStatusTagType = (status: string): string => {
  const types: Record<string, string> = {
    'CONNECTED': 'success',
    'DISCONNECTED': 'info',
    'FAILED': 'danger',
    'TESTING': 'warning'
  }
  return types[status] || 'info'
}

const getFileName = (filePath: string): string => {
  return filePath.split('/').pop() || filePath
}

const formatDateTime = (dateTime: string): string => {
  return new Date(dateTime).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const handleEdit = (dataSource: DataSource) => {
  emit('edit', dataSource)
}

const handleDelete = (dataSource: DataSource) => {
  emit('delete', dataSource)
}

const handleTestConnection = (dataSource: DataSource) => {
  emit('testConnection', dataSource)
}

const handleSortChange = ({ prop, order }: { prop: string; order: string }) => {
  emit('sortChange', { prop, order })
}
</script>

<style scoped lang="scss">
.data-source-table {
  .source-table {
    width: 100%;

    .name-cell {
      display: flex;
      align-items: center;
      gap: 12px;

      .source-icon {
        font-size: 18px;
        color: #409eff;
        flex-shrink: 0;
      }

      .name-content {
        flex: 1;
        min-width: 0;

        .name-text {
          font-weight: 500;
          color: #303133;
          margin-bottom: 2px;
        }

        .description-text {
          font-size: 12px;
          color: #909399;
          line-height: 1.2;
        }
      }
    }

    .connection-info {
      font-size: 13px;
      color: #606266;

      > div {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-bottom: 2px;

        &:last-child {
          margin-bottom: 0;
        }

        .el-icon {
          font-size: 12px;
          color: #909399;
        }
      }

      .db-name {
        font-size: 12px;
        color: #909399;
      }
    }

    .text-muted {
      color: #c0c4cc;
    }

    .action-buttons {
      display: flex;
      gap: 8px;
      justify-content: center;

      .el-button {
        &.is-circle {
          width: 32px;
          height: 32px;
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .data-source-table {
    .source-table {
      :deep(.el-table__body-wrapper) {
        overflow-x: auto;
      }

      .action-buttons {
        flex-direction: column;
        gap: 4px;

        .el-button {
          &.is-circle {
            width: 28px;
            height: 28px;
          }
        }
      }
    }
  }
}
</style>