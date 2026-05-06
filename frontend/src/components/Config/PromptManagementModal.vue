<template>
  <el-dialog
    v-model="isVisible"
    title="Prompt 管理"
    width="80%"
    top="5vh"
    :before-close="closeModal"
    class="prompt-management-modal"
  >
    <div class="modal-content">
      <PromptManagement />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useUIStore } from '@/store/modules/ui';
import PromptManagement from './PromptManagement.vue';

const uiStore = useUIStore();

const isVisible = computed({
  get: () => uiStore.isPromptManagementModalOpen,
  set: (value) => {
    if (value) {
      uiStore.openPromptManagementModal();
    } else {
      uiStore.closePromptManagementModal();
    }
  }
});

const closeModal = () => {
  uiStore.closePromptManagementModal();
};
</script>

<style scoped>
.modal-content {
  min-height: 60vh;
  overflow-y: auto;
}
</style>