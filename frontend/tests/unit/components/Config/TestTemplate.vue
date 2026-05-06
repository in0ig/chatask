<template>
  <div>
    <el-tree
      :data="[{id: '1', label: 'test', source: 'source'}]"
      show-checkbox
      node-key="id"
    >
      <template #default="{ node }">
        <span>{{ node.label }}</span>
        <span>({{ node.data.source }})</span>
      </template>
    </el-tree>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>