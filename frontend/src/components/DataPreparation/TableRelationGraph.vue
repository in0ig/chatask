<template>
  <div class="table-relation-graph-container">
    <!-- 工具栏 -->
    <div class="toolbar">
      <button @click="setLayout('force')" :class="{ active: layout === 'force' }">力导向布局</button>
      <button @click="setLayout('hierarchical')" :class="{ active: layout === 'hierarchical' }">层次布局</button>
      <button @click="resetView">重置视图</button>
      <button @click="exportImage">导出图片</button>
    </div>
    
    <!-- 图形容器 -->
    <div class="graph-container" ref="graphContainer">
      <svg ref="svg" :width="containerWidth" :height="containerHeight" @wheel="handleWheel" @mousedown="handleMouseDown" @mousemove="handleMouseMove" @mouseup="handleMouseUp">
        <!-- 边 -->
        <g class="edges">
          <path 
            v-for="(edge, index) in edges" 
            :key="index"
            :d="edge.path"
            :class="['edge', edge.type, { highlight: edge.highlight }]"
            :stroke-width="edge.highlight ? 3 : 1"
            @mouseenter="highlightEdge(edge)"
            @mouseleave="clearHighlight()"
          />
        </g>
        
        <!-- 节点 -->
        <g class="nodes">
          <g 
            v-for="(node, index) in nodes" 
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
            @mousedown="startDrag(node)"
            @mouseenter="highlightNode(node)"
            @mouseleave="clearHighlight()"
            @click="showNodeDetails(node)"
          >
            <!-- 节点背景 -->
            <rect 
              :x="-node.width/2" 
              :y="-node.height/2" 
              :width="node.width" 
              :height="node.height" 
              :fill="node.highlight ? '#e3f2fd' : '#ffffff'"
              :stroke="node.highlight ? '#2196f3' : '#ccc'"
              stroke-width="2"
              rx="4"
              ry="4"
            />
            
            <!-- 表名 -->
            <text 
              :x="0" 
              :y="-node.height/2 + 15" 
              text-anchor="middle" 
              font-size="12" 
              font-weight="bold"
              fill="black"
            >{{ node.label }}</text>
            
            <!-- 关键字段 -->
            <text 
              v-for="(field, i) in node.fields" 
              :key="i"
              :x="0" 
              :y="-node.height/2 + 30 + i * 15" 
              text-anchor="middle" 
              font-size="10"
              fill="#666"
            >{{ field }}</text>
          </g>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';

// 组件属性
const props = defineProps({
  tables: {
    type: Array,
    required: true
  },
  relations: {
    type: Array,
    required: true
  }
});

// 响应式状态
const graphContainer = ref(null);
const svg = ref(null);
const nodes = ref([]);
const edges = ref([]);
const containerWidth = ref(800);
const containerHeight = ref(600);
const layout = ref('force'); // 'force' or 'hierarchical'
const isDragging = ref(false);
const draggedNode = ref(null);
const dragOffset = ref({ x: 0, y: 0 });
const zoom = ref(1);
const translate = ref({ x: 0, y: 0 });

// 计算属性
const nodeMap = computed(() => {
  const map = {};
  props.tables.forEach(table => {
    map[table.id] = table;
  });
  return map;
});

// 初始化节点和边
const initializeGraph = () => {
  // 重置节点和边
  nodes.value = [];
  edges.value = [];
  
  // 创建节点
  props.tables.forEach(table => {
    const node = {
      id: table.id,
      label: table.name,
      fields: table.fields ? table.fields.slice(0, 3) : [], // 只显示前3个字段
      width: Math.max(100, table.name.length * 8),
      height: 60 + (table.fields ? Math.min(table.fields.length, 3) * 15 : 0),
      x: Math.random() * (containerWidth.value - 200) + 100,
      y: Math.random() * (containerHeight.value - 200) + 100,
      highlight: false
    };
    nodes.value.push(node);
  });
  
  // 创建边
  props.relations.forEach(relation => {
    const sourceNode = nodes.value.find(n => n.id === relation.source_table_id);
    const targetNode = nodes.value.find(n => n.id === relation.target_table_id);
    
    if (sourceNode && targetNode) {
      const path = generateEdgePath(sourceNode, targetNode);
      const edge = {
        id: relation.id,
        source: relation.source_table_id,
        target: relation.target_table_id,
        type: relation.type,
        path: path,
        highlight: false,
        sourceField: relation.source_field,
        targetField: relation.target_field
      };
      edges.value.push(edge);
    }
  });
};

// 生成边的路径
const generateEdgePath = (source, target) => {
  const x1 = source.x;
  const y1 = source.y;
  const x2 = target.x;
  const y2 = target.y;
  
  // 使用贝塞尔曲线连接节点
  const controlX1 = (x1 + x2) / 2;
  const controlY1 = y1;
  const controlX2 = (x1 + x2) / 2;
  const controlY2 = y2;
  
  return `M ${x1} ${y1} C ${controlX1} ${controlY1} ${controlX2} ${controlY2} ${x2} ${y2}`;
};

// 布局算法
const applyLayout = () => {
  if (layout.value === 'force') {
    applyForceLayout();
  } else if (layout.value === 'hierarchical') {
    applyHierarchicalLayout();
  }
};

// 力导向布局
const applyForceLayout = () => {
  // 简化版力导向布局
  const nodesArray = [...nodes.value];
  const iterations = 50;
  
  for (let i = 0; i < iterations; i++) {
    // 重复力
    for (let j = 0; j < nodesArray.length; j++) {
      for (let k = j + 1; k < nodesArray.length; k++) {
        const dx = nodesArray[k].x - nodesArray[j].x;
        const dy = nodesArray[k].y - nodesArray[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 0) {
          const force = 100 / (distance * distance);
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;
          
          nodesArray[j].x -= fx;
          nodesArray[j].y -= fy;
          nodesArray[k].x += fx;
          nodesArray[k].y += fy;
        }
      }
    }
    
    // 吸引力
    edges.value.forEach(edge => {
      const sourceNode = nodesArray.find(n => n.id === edge.source);
      const targetNode = nodesArray.find(n => n.id === edge.target);
      
      if (sourceNode && targetNode) {
        const dx = targetNode.x - sourceNode.x;
        const dy = targetNode.y - sourceNode.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 0) {
          const force = distance * 0.05;
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;
          
          sourceNode.x += fx;
          sourceNode.y += fy;
          targetNode.x -= fx;
          targetNode.y -= fy;
        }
      }
    });
  }
  
  // 更新节点位置
  nodes.value = nodesArray;
  
  // 更新边路径
  updateEdgePaths();
};

// 层次布局
const applyHierarchicalLayout = () => {
  // 简化版层次布局
  // 根据关联关系确定层级
  const levels = {};
  const visited = new Set();
  
  // 找到没有入边的节点作为根节点
  const sourceIds = new Set(edges.value.map(e => e.source));
  const targetIds = new Set(edges.value.map(e => e.target));
  
  // 找到根节点（只有出边，没有入边）
  const rootNodes = nodes.value.filter(node => !targetIds.has(node.id));
  
  // 分配层级
  rootNodes.forEach(node => {
    levels[node.id] = 0;
    visited.add(node.id);
  });
  
  let currentLevel = 0;
  let hasMoreNodes = true;
  
  while (hasMoreNodes) {
    hasMoreNodes = false;
    currentLevel++;
    
    // 找到当前层级所有节点的子节点
    const currentLevelNodes = nodes.value.filter(node => levels[node.id] === currentLevel - 1);
    
    currentLevelNodes.forEach(node => {
      const childEdges = edges.value.filter(e => e.source === node.id);
      childEdges.forEach(edge => {
        if (!visited.has(edge.target)) {
          levels[edge.target] = currentLevel;
          visited.add(edge.target);
          hasMoreNodes = true;
        }
      });
    });
  }
  
  // 根据层级和节点数计算位置
  const levelCounts = {};
  nodes.value.forEach(node => {
    const level = levels[node.id] || 0;
    levelCounts[level] = (levelCounts[level] || 0) + 1;
  });
  
  nodes.value.forEach(node => {
    const level = levels[node.id] || 0;
    const count = levelCounts[level];
    const index = nodes.value.filter(n => (levels[n.id] || 0) === level).findIndex(n => n.id === node.id);
    
    node.x = (index + 1) * (containerWidth.value / (count + 1));
    node.y = 100 + level * 150;
  });
  
  updateEdgePaths();
};

// 更新边路径
const updateEdgePaths = () => {
  edges.value = edges.value.map(edge => {
    const sourceNode = nodes.value.find(n => n.id === edge.source);
    const targetNode = nodes.value.find(n => n.id === edge.target);
    
    if (sourceNode && targetNode) {
      return {
        ...edge,
        path: generateEdgePath(sourceNode, targetNode)
      };
    }
    return edge;
  });
};

// 鼠标事件处理
const handleMouseDown = (e) => {
  if (e.target.tagName === 'svg') {
    const rect = svg.value.getBoundingClientRect();
    const x = (e.clientX - rect.left - translate.value.x) / zoom.value;
    const y = (e.clientY - rect.top - translate.value.y) / zoom.value;
    
    // 检查是否点击了节点
    const clickedNode = nodes.value.find(node => {
      const dx = x - node.x;
      const dy = y - node.y;
      return Math.sqrt(dx * dx + dy * dy) < (node.width / 2 + 10);
    });
    
    if (!clickedNode) {
      // 开始拖拽画布
      isDragging.value = true;
      dragOffset.value = { x, y };
    }
  }
};

const handleMouseMove = (e) => {
  if (isDragging.value && !draggedNode.value) {
    // 拖拽画布
    const rect = svg.value.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom.value;
    const y = (e.clientY - rect.top) / zoom.value;
    
    translate.value.x += x - dragOffset.value.x;
    translate.value.y += y - dragOffset.value.y;
    
    dragOffset.value = { x, y };
  } else if (draggedNode.value) {
    // 拖拽节点
    const rect = svg.value.getBoundingClientRect();
    const x = (e.clientX - rect.left - translate.value.x) / zoom.value;
    const y = (e.clientY - rect.top - translate.value.y) / zoom.value;
    
    draggedNode.value.x = x;
    draggedNode.value.y = y;
    
    updateEdgePaths();
  }
};

const handleMouseUp = () => {
  isDragging.value = false;
  draggedNode.value = null;
};

const handleWheel = (e) => {
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  const newZoom = Math.max(0.5, Math.min(3, zoom.value * delta));
  
  // 缩放中心
  const rect = svg.value.getBoundingClientRect();
  const mouseX = (e.clientX - rect.left - translate.value.x) / zoom.value;
  const mouseY = (e.clientY - rect.top - translate.value.y) / zoom.value;
  
  zoom.value = newZoom;
  
  // 调整平移以保持缩放中心不变
  translate.value.x = e.clientX - rect.left - mouseX * zoom.value;
  translate.value.y = e.clientY - rect.top - mouseY * zoom.value;
};

// 节点拖拽
const startDrag = (node) => {
  draggedNode.value = node;
  isDragging.value = true;
};

// 高亮功能
const highlightNode = (node) => {
  nodes.value = nodes.value.map(n => ({
    ...n,
    highlight: n.id === node.id
  }));
  
  edges.value = edges.value.map(edge => ({
    ...edge,
    highlight: edge.source === node.id || edge.target === node.id
  }));
};

const highlightEdge = (edge) => {
  nodes.value = nodes.value.map(node => ({
    ...node,
    highlight: node.id === edge.source || node.id === edge.target
  }));
  
  edges.value = edges.value.map(e => ({
    ...e,
    highlight: e.id === edge.id
  }));
};

const clearHighlight = () => {
  nodes.value = nodes.value.map(node => ({
    ...node,
    highlight: false
  }));
  
  edges.value = edges.value.map(edge => ({
    ...edge,
    highlight: false
  }));
};

// 节点点击事件
const showNodeDetails = (node) => {
  // 触发事件通知父组件显示节点详情
  const event = new CustomEvent('node-click', {
    detail: { node }
  });
  document.dispatchEvent(event);
};

// 布局切换
const setLayout = (newLayout) => {
  layout.value = newLayout;
  applyLayout();
};

// 重置视图
const resetView = () => {
  zoom.value = 1;
  translate.value = { x: 0, y: 0 };
  initializeGraph();
};

// 导出图片
const exportImage = () => {
  const svgElement = svg.value;
  const serializer = new XMLSerializer();
  let source = serializer.serializeToString(svgElement);
  
  // 添加命名空间
  source = source.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"');
  
  // 创建图像
  const img = new Image();
  const svgBlob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(svgBlob);
  
  img.onload = () => {
    const canvas = document.createElement('canvas');
    canvas.width = containerWidth.value;
    canvas.height = containerHeight.value;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    
    // 创建下载链接
    const link = document.createElement('a');
    link.download = 'table-relation-graph.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  };
  
  img.src = url;
};

// 监听数据变化
watch(() => [props.tables, props.relations], () => {
  initializeGraph();
  applyLayout();
}, { deep: true });

// 初始化
onMounted(() => {
  if (graphContainer.value) {
    containerWidth.value = graphContainer.value.offsetWidth;
    containerHeight.value = graphContainer.value.offsetHeight;
  }
  
  initializeGraph();
  applyLayout();
});
</script>

<style scoped>
.table-relation-graph-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.toolbar {
  padding: 10px;
  background-color: #f5f5f5;
  border-bottom: 1px solid #ddd;
  display: flex;
  gap: 10px;
}

.toolbar button {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  cursor: pointer;
  font-size: 12px;
}

.toolbar button:hover {
  background-color: #e8e8e8;
}

.toolbar button.active {
  background-color: #2196f3;
  color: white;
  border-color: #2196f3;
}

.graph-container {
  flex: 1;
  overflow: hidden;
  position: relative;
}

svg {
  background-color: #fafafa;
  cursor: grab;
}

svg:active {
  cursor: grabbing;
}

.edge {
  fill: none;
  stroke: #666;
  transition: stroke-width 0.2s;
}

.edge.foreign-key {
  stroke: #2196f3;
}

.edge.primary-key {
  stroke: #4caf50;
}

.edge.unique {
  stroke: #ff9800;
}

.edge.highlight {
  stroke-width: 3;
  stroke: #2196f3;
}

.nodes g {
  cursor: pointer;
}

.nodes rect {
  transition: fill 0.2s, stroke 0.2s;
}

.nodes text {
  pointer-events: none;
}
</style>