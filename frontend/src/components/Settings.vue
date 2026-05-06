<template>
  <div class="settings-panel">
    <h3>{{ $t('settings.title') }}</h3>
    
    <!-- 配置组1：核心配置 -->
    <div class="config-group">
      <h4>{{ $t('settings.dataSource') }}</h4>
      <div class="config-item">
        <label>{{ $t('settings.dataSource') }}</label>
        <el-button type="primary" size="small">{{ $t('common.save') }}</el-button>
      </div>
      <div class="config-item">
        <label>{{ $t('settings.aiModel') }}</label>
        <el-button type="primary" size="small">{{ $t('common.save') }}</el-button>
      </div>
      <div class="config-item">
        <label>{{ $t('settings.title') }}</label>
        <el-button type="primary" size="small">{{ $t('common.save') }}</el-button>
      </div>
      <div class="config-item">
        <label>{{ $t('common.export') }}</label>
        <el-button type="primary" size="small">{{ $t('common.save') }}</el-button>
      </div>
    </div>
    
    <!-- 配置组2：权限管理 -->
    <div class="config-group">
      <h4>{{ $t('settings.aiModel') }}</h4>
      <div class="config-item">
        <label>{{ $t('settings.aiModel') }}</label>
        <el-button type="primary" size="small">{{ $t('common.save') }}</el-button>
      </div>
      <div class="config-item">
        <label>{{ $t('settings.dataSource') }}</label>
        <el-button type="primary" size="small">{{ $t('common.save') }}</el-button>
      </div>
    </div>
    
    <!-- 配置组3：智能工具 -->
    <div class="config-group">
      <h4>{{ $t('chat.queryMode') }}</h4>
      <div class="config-item">
        <label>{{ $t('stages.result_interpretation') }}</label>
        <el-switch v-model="dataInterpretation" active-color="#1890ff" inactive-color="#ccc" />
      </div>
      <div class="config-item">
        <label>{{ $t('stages.data_analysis') }}</label>
        <el-switch v-model="fluctuationAnalysis" active-color="#1890ff" inactive-color="#ccc" />
      </div>
      <div class="config-item">
        <label>{{ $t('stages.table_selection') }}</label>
        <el-switch v-model="smartTableSelection" active-color="#1890ff" inactive-color="#ccc" />
      </div>
    </div>
    
    <!-- 配置组4：高级设置 -->
    <div class="config-group">
      <h4>{{ $t('settings.title') }}</h4>
      <div class="config-item">
        <label>{{ $t('settings.title') }}</label>
        <el-button type="primary" size="small">{{ $t('common.save') }}</el-button>
      </div>
      <div class="config-item">
        <label>{{ $t('chat.sessionHistory') }}</label>
        <el-button type="primary" size="small">{{ $t('common.save') }}</el-button>
      </div>
      <div class="config-item">
        <label>{{ $t('common.export') }}</label>
        <el-button type="primary" size="small">{{ $t('common.save') }}</el-button>
      </div>
    </div>
    
    <!-- 退出按钮 -->
    <div class="logout-section">
      <button @click="handleLogout" class="btn-secondary">{{ $t('common.close') }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// 状态
const dataInterpretation = ref(true)
const fluctuationAnalysis = ref(false)
const smartTableSelection = ref(true)

// 退出登录
const handleLogout = () => {
  console.log('用户退出登录')
}
</script>

<style scoped>
.settings-panel {
  width: 280px;
  height: 100%;
  padding: 16px;
  background-color: white;
  box-shadow: -2px 0 8px rgba(0,0,0,0.1);
  overflow-y: auto;
}

.settings-panel h3 {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.config-group {
  margin-bottom: 24px;
}

.config-group h4 {
  font-size: 14px;
  font-weight: 600;
  color: #666;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.config-item label {
  font-size: 14px;
  color: #333;
}

.btn-secondary {
  background-color: #fff;
  color: #333;
  border: 1px solid #ddd;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-secondary:hover {
  background-color: #f0f0f0;
}

.logout-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}
</style>