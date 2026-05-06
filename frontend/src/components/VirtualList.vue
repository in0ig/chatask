<template>
  <div class="virtual-list" ref="container" @scroll="handleScroll" :style="containerStyle">
    <div 
      class="virtual-list-content" 
      :style="contentStyle"
    >
      <div 
        class="virtual-list-item" 
        v-for="(item, idx) in visibleItems" 
        :key="item?.id || idx" 
        :style="getItemStyle(item, idx)"
      >
        <slot name="item" :item="item" :index="idx"></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

interface VirtualListProps {
  items: any[]
  itemHeight: number
  containerHeight?: number
}

const props = withDefaults(defineProps<VirtualListProps>(), {
  containerHeight: 400
})

const container = ref<HTMLDivElement | null>(null)
const scrollTop = ref(0)

// 计算可见项的起始和结束索引
const visibleRange = computed(() => {
  const startIndex = Math.floor(scrollTop.value / props.itemHeight)
  const endIndex = Math.ceil((scrollTop.value + props.containerHeight) / props.itemHeight)
  
  return {
    start: Math.max(0, startIndex - 2), // 预加载一些项
    end: Math.min(props.items.length - 1, endIndex + 2) // 预加载一些项
  }
})

// 计算容器样式
const containerStyle = computed(() => ({
  height: `${props.containerHeight}px`,
  overflowY: 'auto',
  position: 'relative'
}))

// 计算内容样式
const contentStyle = computed(() => ({
  height: `${props.items.length * props.itemHeight}px`,
  position: 'relative'
}))

// 计算可见项 - 使用 computed 而不是 ref
const visibleItems = computed(() => {
  if (!props.items || props.items.length === 0) {
    return []
  }
  const { start, end } = visibleRange.value
  return props.items.slice(start, end + 1)
})

// 计算单个项的样式
function getItemStyle(item: any, idx: number) {
  const itemIndex = props.items.indexOf(item)
  const actualIndex = itemIndex >= 0 ? itemIndex : idx
  return {
    position: 'absolute',
    top: `${actualIndex * props.itemHeight}px`,
    left: '0',
    width: '100%',
    height: `${props.itemHeight}px`,
    transform: 'translate3d(0, 0, 0)' // 启用硬件加速
  }
}

// 处理滚动事件
function handleScroll() {
  if (!container.value) return
  scrollTop.value = container.value.scrollTop
}

onMounted(() => {
  // 组件挂载完成
})

onUnmounted(() => {
  // 清理
})
</script>

<style scoped>
.virtual-list {
  width: 100%;
}

.virtual-list-content {
  width: 100%;
}

.virtual-list-item {
  width: 100%;
  box-sizing: border-box;
}
</style>