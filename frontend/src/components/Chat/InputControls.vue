<template>
  <div class="input-controls">
    <!-- 第二行：大文本输入框 -->
    <el-input
      v-model="inputText"
      type="textarea"
      :placeholder="$t('chat.inputPlaceholder')"
      :rows="4"
      class="input-textarea"
      @input="handleInput"
    />

    <!-- 第三行：功能图标和按钮 -->
    <div class="action-bar">
      <!-- 附件上传按钮 -->
      <button
        type="button"
        @click="handleAttach"
        class="attachment-button"
        :aria-label="$t('common.export')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
      </button>

      <!-- 发送按钮 -->
      <button
        type="button"
        @click="handleSend"
        :disabled="!canSend"
        class="send-button"
        :aria-label="$t('chat.send')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '@/store/modules/chat'

// 使用 Pinia Store
const chatStore = useChatStore()

// 绑定 store 状态
const inputText = computed({
  get: () => chatStore.inputText,
  set: (value) => chatStore.inputText = value
})

// 发送按钮是否可点击
const canSend = computed(() => {
  return inputText.value.trim().length > 0
})

// 事件处理函数
const handleInput = () => {
  // 输入变化时自动更新 store
}

const handleSend = () => {
  if (canSend.value) {
    chatStore.sendMessage(inputText.value, chatStore.currentDataSource, chatStore.chatMode)
  }
}

const handleAttach = () => {
  // 附件上传功能
  console.log('附件上传')
}
</script>

<style scoped>
.input-controls {
  padding: 16px;
  background-color: #f5f7fa;
  border-top: 1px solid #e4e7ed;
}

.input-textarea {
  width: 100%;
  margin-bottom: 12px;
}

.action-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}

.attachment-button,
.send-button {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #1890ff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: white;
  padding: 0;
  outline: none;
}

.attachment-button svg,
.send-button svg {
  color: white;
}

.attachment-button:hover {
  background-color: #0c7bd7;
  transform: translateY(-2px);
}

.send-button:hover:not(:disabled) {
  background-color: #0c7bd7;
  transform: translateY(-2px);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>