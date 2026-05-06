<template>
  <div class="token-usage-stats">
    <div class="el-card token-card">
      <div class="el-card__header card-header">
        <span class="title">Token 使用统计</span>
      </div>
      
      <div class="el-card__body">
        <div class="usage-details">
          <div class="usage-row">
            <span class="label">当前使用:</span>
            <span class="value">{{ formatNumber(currentUsage) }}</span>
          </div>
          <div class="usage-row">
            <span class="label">总限制:</span>
            <span class="value">{{ formatNumber(totalLimit) }}</span>
          </div>
          <div class="usage-row">
            <span class="label">剩余可用:</span>
            <span class="value">{{ formatNumber(remainingTokens) }}</span>
          </div>
          <div class="usage-row">
            <span class="label">模型类型:</span>
            <span :class="['el-tag', 'el-tag--' + modelTypeTagType, 'el-tag--small']">
              {{ modelTypeDisplayText }}
            </span>
          </div>
          <div class="usage-row">
            <span class="label">使用比例:</span>
            <span class="value percentage">{{ usagePercentage }}%</span>
          </div>
        </div>
        
        <!-- 进度条显示 -->
        <div class="progress-section">
          <div class="el-progress el-progress--line">
            <div class="el-progress-bar">
              <div class="el-progress-bar__outer" :style="{ height: '20px' }">
                <div 
                  class="el-progress-bar__inner"
                  :style="{ width: progressPercentage + '%', backgroundColor: progressColor }"
                ></div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 警告信息 -->
        <div v-if="showWarning" class="warning-text" :class="warningClass">
          {{ warningMessage }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  currentUsage?: number;
  totalLimit?: number;
  modelType?: 'local' | 'aliyun';
}

const props = withDefaults(defineProps<Props>(), {
  currentUsage: 0,
  totalLimit: 32000,
  modelType: 'local'
});

// 计算剩余Token数量
const remainingTokens = computed(() => {
  return Math.max(0, props.totalLimit - props.currentUsage);
});

// 计算使用百分比
const usagePercentage = computed(() => {
  if (props.totalLimit <= 0) return '0.00';
  const percentage = (props.currentUsage / props.totalLimit) * 100;
  return Math.min(percentage, 100).toFixed(2);
});

// 计算进度条百分比（限制在0-100之间）
const progressPercentage = computed(() => {
  if (props.totalLimit <= 0) return 0;
  return Math.min((props.currentUsage / props.totalLimit) * 100, 100);
});

// 根据使用率确定进度条颜色
const progressColor = computed(() => {
  const percentage = progressPercentage.value;
  if (percentage >= 90) return '#f56c6c'; // 红色 - 危险
  if (percentage >= 80) return '#e6a23c'; // 黄色 - 警告
  return '#67c23a'; // 绿色 - 正常
});

// 是否显示警告
const showWarning = computed(() => {
  return props.currentUsage > props.totalLimit * 0.8;
});

// 警告级别类
const warningClass = computed(() => {
  const percentage = progressPercentage.value;
  if (percentage >= 95) return 'danger';
  if (percentage >= 80) return 'warning';
  return '';
});

// 警告消息
const warningMessage = computed(() => {
  const percentage = progressPercentage.value;
  if (percentage >= 95) {
    return 'Token即将耗尽，请注意！';
  } else if (percentage >= 80) {
    return 'Token使用量较高';
  }
  return '';
});

// 模型类型标签类型
const modelTypeTagType = computed(() => {
  return props.modelType === 'local' ? 'success' : 'primary';
});

// 模型类型显示文本
const modelTypeDisplayText = computed(() => {
  return props.modelType === 'local' ? '本地模型' : '阿里云模型';
});

// 数字格式化函数
const formatNumber = (num: number): string => {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
</script>

<style scoped>
.token-usage-stats {
  width: 100%;
  margin: 10px 0;
}

.token-card {
  width: 100%;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background-color: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  padding: 12px 20px;
  border-bottom: 1px solid #ebeef5;
  box-sizing: border-box;
}

.title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.usage-details {
  padding: 20px;
}

.usage-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px dashed #dcdfe6;
}

.usage-row:last-child {
  border-bottom: none;
}

.label {
  color: #606266;
  font-weight: 500;
  flex: 1;
}

.value {
  color: #303133;
  font-weight: bold;
  text-align: right;
  min-width: 80px;
}

.percentage {
  font-size: 14px;
}

.progress-section {
  margin: 15px 20px;
}

.el-progress {
  width: 100%;
  height: 20px;
  background-color: #ebeef5;
  border-radius: 10px;
  overflow: hidden;
}

.el-progress--line {
  position: relative;
}

.el-progress-bar {
  width: 100%;
  position: relative;
}

.el-progress-bar__outer {
  width: 100%;
  height: 20px;
  background-color: #ebeef5;
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}

.el-progress-bar__inner {
  height: 100%;
  border-radius: 10px;
  text-align: right;
  transition: width 0.3s ease;
}

.warning-text {
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
  text-align: center;
  margin: 10px 20px;
}

.warning-text.warning {
  background-color: #fdf6ec;
  color: #e6a23c;
  border: 1px solid #faecd8;
}

.warning-text.danger {
  background-color: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fde2e2;
}

/* Element Plus tag styles */
.el-tag {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  height: 32px;
  padding: 0 12px;
  line-height: 30px;
  font-size: 12px;
  border: 1px solid transparent;
  border-radius: 4px;
  box-sizing: border-box;
}

.el-tag--small {
  height: 24px;
  padding: 0 8px;
  line-height: 22px;
}

.el-tag--success {
  background-color: #f0f9ff;
  border-color: #b3d8ff;
  color: #409eff;
}

.el-tag--primary {
  background-color: #ecf5ff;
  border-color: #b3d8ff;
  color: #409eff;
}
</style>