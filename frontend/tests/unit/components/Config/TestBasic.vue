<template>
  <div>
    <p>{{ message }}</p>
    <button @click="increment">{{ count }}</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)
const message = ref('Hello World')

const increment = () => {
  count.value++
}
</script>

<style scoped>
</style>