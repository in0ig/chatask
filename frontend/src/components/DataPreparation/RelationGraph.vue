<template>
  <div class="relation-graph-container" ref="graphContainer">
    <svg class="relation-graph-svg" :width="width" :height="height">
      <g class="graph-content" :transform="`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`">
        <!-- 连接线 -->
        <g class="links">
          <line
            v-for="link in layoutData.links"
            :key="`${link.source}-${link.target}`"
            :x1="link.x1"
            :y1="link.y1"
            :x2="link.x2"
            :y2="link.y2"
            class="relation-link"
            :class="`link-${link.joinType?.toLowerCase()}`"
          />
          <!-- 连接线标签 -->
          <text
            v-for="link in layoutData.links"
            :key="`label-${link.source}-${link.target}`"
            :x="(link.x1 + link.x2) / 2"
            :y="(link.y1 + link.y2) / 2 - 5"
            class="link-label"
            text-anchor="middle"
          >
            {{ link.joinType }}
          </text>
        </g>
        
        <!-- 表节点 -->
        <g class="nodes">
          <g
            v-for="node in layoutData.nodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
            class="table-node"
            @mousedown="startDrag(node, $event)"
            @click="selectNode(node)"
            :class="{ selected: selectedNode?.id === node.id }"
          >
            <!-- 表背景 -->
            <rect
              :width="nodeWidth"
              :height="nodeHeight"
              class="node-background"
              rx="4"
            />
            
            <!-- 表标题 -->
            <rect
              :width="nodeWidth"
              :height="30"
              class="node-header"
              rx="4"
            />
            <text
              :x="nodeWidth / 2"
              y="20"
              class="node-title"
              text-anchor="middle"
            >
              {{ node.label }}
            </text>
            
            <!-- 字段列表 -->
            <g class="node-fields">
              <g
                v-for="(field, index) in node.fields"
                :key="field.name"
                :transform="`translate(0, ${30 + index * 20})`"
              >
                <text
                  x="10"
                  y="15"
                  class="field-name"
                >
                  {{ field.name }}
                </text>
                <text
                  :x="nodeWidth - 10"
                  y="15"
                  class="field-type"
                  text-anchor="end"
                >
                  {{ field.type }}
                </text>
              </g>
            </g>
          </g>
        </g>
      </g>
    </svg>
    
    <div class="graph-toolbar">
      <el-button :icon="ZoomIn" @click="zoomIn" circle />
      <el-button :icon="ZoomOut" @click="zoomOut" circle />
      <el-button :icon="Refresh" @click="resetView" circle />
      <el-button :icon="FullScreen" @click="fitToScreen" circle />
    </div>
    
    <!-- 节点信息面板 -->
    <div v-if="selectedNode" class="node-info-panel">
      <h4>{{ selectedNode.label }}</h4>
      <div class="field-list">
        <div v-for="field in selectedNode.fields" :key="field.name" class="field-item">
          <span class="field-name">{{ field.name }}</span>
          <span class="field-type">{{ field.type }}</span>
        </div>
      </div>
      <el-button size="small" @click="selectedNode = null">关闭</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, reactive } from 'vue';
import { ElButton } from 'element-plus';
import { ZoomIn, ZoomOut, Refresh, FullScreen } from '@element-plus/icons-vue';
import { calculateLayout } from '@/utils/graphLayout';

interface TableNode {
  id: string;
  label: string;
  x: number;
  y: number;
  fields: { name: string; type: string }[];
}

interface RelationLink {
  source: string;
  target: string;
  joinType: 'INNER' | 'LEFT' | 'RIGHT';
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface LayoutData {
  nodes: TableNode[];
  links: RelationLink[];
}

const graphContainer = ref<HTMLElement | null>(null);
const width = ref(800);
const height = ref(600);
const selectedNode = ref<TableNode | null>(null);

// 节点尺寸配置
const nodeWidth = 180;
const nodeHeight = 120;

// 变换状态
const transform = reactive({
  x: 0,
  y: 0,
  scale: 1,
});

// 拖拽状态
const dragState = reactive({
  isDragging: false,
  dragNode: null as TableNode | null,
  startX: 0,
  startY: 0,
  nodeStartX: 0,
  nodeStartY: 0,
});

// Mock 数据 - 实际应用中从 props 或 store 获取
const rawNodes = ref([
  {
    id: 'users',
    label: 'users',
    fields: [
      { name: 'id', type: 'int' },
      { name: 'name', type: 'varchar' },
      { name: 'email', type: 'varchar' },
      { name: 'created_at', type: 'datetime' },
    ],
  },
  {
    id: 'orders',
    label: 'orders',
    fields: [
      { name: 'id', type: 'int' },
      { name: 'user_id', type: 'int' },
      { name: 'product_id', type: 'int' },
      { name: 'amount', type: 'decimal' },
      { name: 'created_at', type: 'datetime' },
    ],
  },
  {
    id: 'products',
    label: 'products',
    fields: [
      { name: 'id', type: 'int' },
      { name: 'name', type: 'varchar' },
      { name: 'price', type: 'decimal' },
      { name: 'category_id', type: 'int' },
    ],
  },
]);

const rawLinks = ref([
  { source: 'users', target: 'orders', joinType: 'LEFT' as const },
  { source: 'products', target: 'orders', joinType: 'INNER' as const },
]);

// 计算布局数据
const layoutData = computed<LayoutData>(() => {
  const layout = calculateLayout(rawNodes.value, rawLinks.value, {
    width: width.value,
    height: height.value,
    nodeWidth,
    nodeHeight,
  });

  return {
    nodes: layout.nodes.map(node => ({
      ...node,
      fields: rawNodes.value.find(n => n.id === node.id)?.fields || [],
    })),
    links: layout.links.map(link => {
      const sourceNode = layout.nodes.find(n => n.id === link.source);
      const targetNode = layout.nodes.find(n => n.id === link.target);
      const rawLink = rawLinks.value.find(l => l.source === link.source && l.target === link.target);
      
      return {
        ...link,
        joinType: rawLink?.joinType || 'LEFT',
        x1: sourceNode ? sourceNode.x + nodeWidth / 2 : 0,
        y1: sourceNode ? sourceNode.y + nodeHeight / 2 : 0,
        x2: targetNode ? targetNode.x + nodeWidth / 2 : 0,
        y2: targetNode ? targetNode.y + nodeHeight / 2 : 0,
      };
    }),
  };
});

// 缩放功能
const zoomIn = () => {
  transform.scale = Math.min(transform.scale * 1.2, 3);
};

const zoomOut = () => {
  transform.scale = Math.max(transform.scale / 1.2, 0.1);
};

const resetView = () => {
  transform.x = 0;
  transform.y = 0;
  transform.scale = 1;
};

const fitToScreen = () => {
  // 计算所有节点的边界
  const nodes = layoutData.value.nodes;
  if (nodes.length === 0) return;

  const minX = Math.min(...nodes.map(n => n.x));
  const maxX = Math.max(...nodes.map(n => n.x + nodeWidth));
  const minY = Math.min(...nodes.map(n => n.y));
  const maxY = Math.max(...nodes.map(n => n.y + nodeHeight));

  const contentWidth = maxX - minX;
  const contentHeight = maxY - minY;

  // 计算缩放比例，留出边距
  const scaleX = (width.value - 100) / contentWidth;
  const scaleY = (height.value - 100) / contentHeight;
  const scale = Math.min(scaleX, scaleY, 1);

  // 计算居中偏移
  const centerX = (width.value - contentWidth * scale) / 2;
  const centerY = (height.value - contentHeight * scale) / 2;

  transform.scale = scale;
  transform.x = centerX - minX * scale;
  transform.y = centerY - minY * scale;
};

// 节点选择
const selectNode = (node: TableNode) => {
  selectedNode.value = selectedNode.value?.id === node.id ? null : node;
};

// 拖拽功能
const startDrag = (node: TableNode, event: MouseEvent) => {
  event.preventDefault();
  dragState.isDragging = true;
  dragState.dragNode = node;
  dragState.startX = event.clientX;
  dragState.startY = event.clientY;
  dragState.nodeStartX = node.x;
  dragState.nodeStartY = node.y;

  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);
};

const onMouseMove = (event: MouseEvent) => {
  if (!dragState.isDragging || !dragState.dragNode) return;

  const deltaX = (event.clientX - dragState.startX) / transform.scale;
  const deltaY = (event.clientY - dragState.startY) / transform.scale;

  dragState.dragNode.x = dragState.nodeStartX + deltaX;
  dragState.dragNode.y = dragState.nodeStartY + deltaY;
};

const onMouseUp = () => {
  dragState.isDragging = false;
  dragState.dragNode = null;
  document.removeEventListener('mousemove', onMouseMove);
  document.removeEventListener('mouseup', onMouseUp);
};

// 响应式尺寸调整
const resizeObserver = new ResizeObserver(entries => {
  for (const entry of entries) {
    width.value = entry.contentRect.width;
    height.value = entry.contentRect.height;
  }
});

onMounted(() => {
  if (graphContainer.value) {
    width.value = graphContainer.value.clientWidth;
    height.value = graphContainer.value.clientHeight;
    resizeObserver.observe(graphContainer.value);
  }
  
  // 初始化时自动适应屏幕
  setTimeout(() => {
    fitToScreen();
  }, 100);
});

onUnmounted(() => {
  if (graphContainer.value) {
    resizeObserver.unobserve(graphContainer.value);
  }
  document.removeEventListener('mousemove', onMouseMove);
  document.removeEventListener('mouseup', onMouseUp);
});
</script>

<style scoped>
.relation-graph-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 500px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.relation-graph-svg {
  display: block;
  background-color: #f9f9f9;
  cursor: grab;
}

.relation-graph-svg:active {
  cursor: grabbing;
}

.graph-toolbar {
  position: absolute;
  top: 15px;
  right: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 节点样式 */
.table-node {
  cursor: pointer;
  transition: all 0.2s ease;
}

.table-node:hover .node-background {
  stroke: #409eff;
  stroke-width: 2;
}

.table-node.selected .node-background {
  stroke: #409eff;
  stroke-width: 3;
}

.node-background {
  fill: #ffffff;
  stroke: #dcdfe6;
  stroke-width: 1;
}

.node-header {
  fill: #f5f7fa;
  stroke: #dcdfe6;
  stroke-width: 1;
}

.node-title {
  font-size: 14px;
  font-weight: bold;
  fill: #303133;
}

.field-name {
  font-size: 12px;
  fill: #606266;
}

.field-type {
  font-size: 11px;
  fill: #909399;
}

/* 连接线样式 */
.relation-link {
  stroke-width: 2;
  fill: none;
}

.link-inner {
  stroke: #67c23a;
}

.link-left {
  stroke: #409eff;
}

.link-right {
  stroke: #e6a23c;
}

.link-label {
  font-size: 11px;
  fill: #606266;
  background: rgba(255, 255, 255, 0.8);
}

/* 节点信息面板 */
.node-info-panel {
  position: absolute;
  top: 15px;
  left: 15px;
  background: #ffffff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  max-width: 250px;
  z-index: 10;
}

.node-info-panel h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #303133;
}

.field-list {
  margin-bottom: 10px;
}

.field-item {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
  font-size: 12px;
}

.field-item .field-name {
  color: #606266;
  font-weight: 500;
}

.field-item .field-type {
  color: #909399;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .graph-toolbar {
    top: 10px;
    right: 10px;
    gap: 5px;
  }
  
  .node-info-panel {
    top: 10px;
    left: 10px;
    max-width: 200px;
    padding: 10px;
  }
}
</style>
