/**
 * A simple force-directed layout algorithm for graph visualization.
 * This is a placeholder and can be replaced with a more robust library like d3-force.
 */

export interface Node {
  id: string;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface Link {
  source: string | Node;
  target: string | Node;
}

export interface LayoutOptions {
  width: number;
  height: number;
  iterations?: number;
  chargeStrength?: number;
  linkDistance?: number;
}

/**
 * Calculates the positions of nodes in a graph.
 * @param nodes - Array of nodes.
 * @param links - Array of links between nodes.
 * @param options - Layout configuration.
 * @returns The nodes with updated x and y positions.
 */
export function simpleForceLayout(nodes: Node[], links: Link[], options: LayoutOptions) {
  const {
    width,
    height,
    iterations = 100,
    chargeStrength = -30,
    linkDistance = 50,
  } = options;

  // Initialize node positions randomly
  nodes.forEach(node => {
    node.x = node.x ?? Math.random() * width;
    node.y = node.y ?? Math.random() * height;
    node.vx = 0;
    node.vy = 0;
  });

  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  for (let i = 0; i < iterations; i++) {
    // Apply charge force (repulsion)
    for (const nodeA of nodes) {
      for (const nodeB of nodes) {
        if (nodeA === nodeB) continue;
        const dx = nodeB.x! - nodeA.x!;
        const dy = nodeB.y! - nodeA.y!;
        let distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < 1) distance = 1;

        const force = chargeStrength / (distance * distance);
        const forceX = (dx / distance) * force;
        const forceY = (dy / distance) * force;
        
        nodeA.vx! += forceX;
        nodeA.vy! += forceY;
      }
    }

    // Apply link force (attraction)
    for (const link of links) {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      const source = nodeMap.get(sourceId);
      const target = nodeMap.get(targetId);

      if (!source || !target) continue;

      const dx = target.x! - source.x!;
      const dy = target.y! - source.y!;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      const displacement = distance - linkDistance;
      const force = displacement * 0.1; // Spring stiffness
      
      const forceX = (dx / distance) * force;
      const forceY = (dy / distance) * force;

      source.vx! += forceX;
      source.vy! += forceY;
      target.vx! -= forceX;
      target.vy! -= forceY;
    }

    // Update positions and apply damping
    for (const node of nodes) {
      node.x! += node.vx!;
      node.y! += node.vy!;
      
      // Damping to prevent infinite oscillation
      node.vx! *= 0.9;
      node.vy! *= 0.9;

      // Keep nodes within bounds
      node.x = Math.max(0, Math.min(width, node.x!));
      node.y = Math.max(0, Math.min(height, node.y!));
    }
  }

  return nodes;
}
// Additional interfaces and functions for RelationGraph component
interface TableNode {
  id: string;
  label: string;
  x: number;
  y: number;
}

interface RelationLink {
  source: string;
  target: string;
}

interface CalculateLayoutOptions {
  width: number;
  height: number;
  nodeWidth?: number;
  nodeHeight?: number;
  iterations?: number;
  repulsionStrength?: number;
  attractionStrength?: number;
  damping?: number;
}

interface LayoutResult {
  nodes: TableNode[];
  links: RelationLink[];
}

/**
 * 简单的力导向布局算法
 * 使用物理模拟来计算节点位置
 */
export function calculateLayout(
  inputNodes: { id: string; label: string }[],
  inputLinks: { source: string; target: string }[],
  options: CalculateLayoutOptions = { width: 800, height: 600 }
): LayoutResult {
  const {
    width = 800,
    height = 600,
    nodeWidth = 180,
    nodeHeight = 120,
    iterations = 100,
    repulsionStrength = 1000,
    attractionStrength = 0.1,
    damping = 0.9,
  } = options;

  // 初始化节点位置
  const nodes: TableNode[] = inputNodes.map((node, index) => ({
    ...node,
    x: Math.random() * (width - nodeWidth) + nodeWidth / 2,
    y: Math.random() * (height - nodeHeight) + nodeHeight / 2,
  }));

  // 如果只有一个节点，居中显示
  if (nodes.length === 1) {
    nodes[0].x = width / 2 - nodeWidth / 2;
    nodes[0].y = height / 2 - nodeHeight / 2;
    return { nodes, links: inputLinks };
  }

  // 如果只有两个节点，水平排列
  if (nodes.length === 2) {
    const spacing = Math.min(width / 3, 300);
    nodes[0].x = width / 2 - spacing / 2 - nodeWidth / 2;
    nodes[0].y = height / 2 - nodeHeight / 2;
    nodes[1].x = width / 2 + spacing / 2 - nodeWidth / 2;
    nodes[1].y = height / 2 - nodeHeight / 2;
    return { nodes, links: inputLinks };
  }

  // 力导向布局迭代
  for (let iteration = 0; iteration < iterations; iteration++) {
    const forces: { x: number; y: number }[] = nodes.map(() => ({ x: 0, y: 0 }));

    // 计算排斥力（所有节点对之间）
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x;
        const dy = nodes[j].y - nodes[i].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 0) {
          const force = repulsionStrength / (distance * distance);
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;
          
          forces[i].x -= fx;
          forces[i].y -= fy;
          forces[j].x += fx;
          forces[j].y += fy;
        }
      }
    }

    // 计算吸引力（连接的节点之间）
    inputLinks.forEach(link => {
      const sourceIndex = nodes.findIndex(n => n.id === link.source);
      const targetIndex = nodes.findIndex(n => n.id === link.target);
      
      if (sourceIndex !== -1 && targetIndex !== -1) {
        const dx = nodes[targetIndex].x - nodes[sourceIndex].x;
        const dy = nodes[targetIndex].y - nodes[sourceIndex].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 0) {
          const force = distance * attractionStrength;
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;
          
          forces[sourceIndex].x += fx;
          forces[sourceIndex].y += fy;
          forces[targetIndex].x -= fx;
          forces[targetIndex].y -= fy;
        }
      }
    });

    // 应用力并更新位置
    nodes.forEach((node, index) => {
      node.x += forces[index].x * damping;
      node.y += forces[index].y * damping;
      
      // 边界约束
      node.x = Math.max(nodeWidth / 2, Math.min(width - nodeWidth / 2, node.x));
      node.y = Math.max(nodeHeight / 2, Math.min(height - nodeHeight / 2, node.y));
    });
  }

  // 调整最终位置，确保节点不重叠
  const minDistance = Math.max(nodeWidth, nodeHeight) * 1.2;
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[j].x - nodes[i].x;
      const dy = nodes[j].y - nodes[i].y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      
      if (distance < minDistance && distance > 0) {
        const overlap = minDistance - distance;
        const moveX = (dx / distance) * overlap * 0.5;
        const moveY = (dy / distance) * overlap * 0.5;
        
        nodes[i].x -= moveX;
        nodes[i].y -= moveY;
        nodes[j].x += moveX;
        nodes[j].y += moveY;
        
        // 重新应用边界约束
        nodes[i].x = Math.max(nodeWidth / 2, Math.min(width - nodeWidth / 2, nodes[i].x));
        nodes[i].y = Math.max(nodeHeight / 2, Math.min(height - nodeHeight / 2, nodes[i].y));
        nodes[j].x = Math.max(nodeWidth / 2, Math.min(width - nodeWidth / 2, nodes[j].x));
        nodes[j].y = Math.max(nodeHeight / 2, Math.min(height - nodeHeight / 2, nodes[j].y));
      }
    }
  }

  return { nodes, links: inputLinks };
}