<template>
  <div>
    <h1>Vue Test Component</h1>
    <p>This is a test to verify Vue is working correctly.</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const message = ref('Hello from Vue!')
</script>

<style scoped>
h1 {
  color: #42b983;
}
</style>