/**
 * 树形数据处理工具函数
 */

export interface TreeNode {
  id: string | number
  children?: TreeNode[]
  [key: string]: any
}

export interface TreeOptions {
  id?: string
  parentId?: string
  children?: string
}

/**
 * 将扁平数组转换为树形结构
 * @param list 扁平数组
 * @param options 配置选项
 * @returns 树形结构数组
 */
export function listToTree<T extends Record<string, any>>(
  list: T[],
  options: TreeOptions = {}
): (T & { children?: T[] })[] {
  const { id = 'id', parentId = 'parentId', children = 'children' } = options
  
  if (!list || list.length === 0) {
    return []
  }

  // 创建映射表
  const map = new Map<string | number, T & { children?: T[] }>()
  const result: (T & { children?: T[] })[] = []

  // 初始化映射表
  list.forEach(item => {
    const node = { ...item, [children]: [] }
    map.set(item[id], node)
  })

  // 构建树形结构
  list.forEach(item => {
    const node = map.get(item[id])!
    const parentKey = item[parentId]
    
    if (parentKey === null || parentKey === undefined || parentKey === '') {
      // 根节点
      result.push(node)
    } else {
      // 子节点
      const parent = map.get(parentKey)
      if (parent) {
        if (!parent[children]) {
          parent[children] = []
        }
        parent[children]!.push(node)
      } else {
        // 如果找不到父节点，当作根节点处理
        result.push(node)
      }
    }
  })

  return result
}

/**
 * 树形结构转换为扁平数组
 * @param tree 树形结构数组
 * @param options 配置选项
 * @returns 扁平数组
 */
export function treeToList<T extends Record<string, any>>(
  tree: T[],
  options: TreeOptions = {}
): T[] {
  const { children = 'children' } = options
  const result: T[] = []

  function traverse(nodes: T[]) {
    nodes.forEach(node => {
      const { [children]: childNodes, ...rest } = node
      result.push(rest as T)
      
      if (childNodes && Array.isArray(childNodes) && childNodes.length > 0) {
        traverse(childNodes)
      }
    })
  }

  traverse(tree)
  return result
}

/**
 * 在树中查找节点
 * @param tree 树形结构数组
 * @param predicate 查找条件
 * @param options 配置选项
 * @returns 找到的节点或 null
 */
export function findInTree<T extends Record<string, any>>(
  tree: T[],
  predicate: (node: T) => boolean,
  options: TreeOptions = {}
): T | null {
  const { children = 'children' } = options

  function traverse(nodes: T[]): T | null {
    for (const node of nodes) {
      if (predicate(node)) {
        return node
      }
      
      if (node[children] && Array.isArray(node[children]) && node[children].length > 0) {
        const found = traverse(node[children])
        if (found) {
          return found
        }
      }
    }
    return null
  }

  return traverse(tree)
}

/**
 * 获取树的所有叶子节点
 * @param tree 树形结构数组
 * @param options 配置选项
 * @returns 叶子节点数组
 */
export function getTreeLeaves<T extends Record<string, any>>(
  tree: T[],
  options: TreeOptions = {}
): T[] {
  const { children = 'children' } = options
  const leaves: T[] = []

  function traverse(nodes: T[]) {
    nodes.forEach(node => {
      if (!node[children] || !Array.isArray(node[children]) || node[children].length === 0) {
        leaves.push(node)
      } else {
        traverse(node[children])
      }
    })
  }

  traverse(tree)
  return leaves
}

/**
 * 获取节点的所有祖先节点
 * @param tree 树形结构数组
 * @param targetId 目标节点ID
 * @param options 配置选项
 * @returns 祖先节点数组（从根到父节点）
 */
export function getAncestors<T extends Record<string, any>>(
  tree: T[],
  targetId: string | number,
  options: TreeOptions = {}
): T[] {
  const { id = 'id', children = 'children' } = options
  const ancestors: T[] = []

  function traverse(nodes: T[], path: T[]): boolean {
    for (const node of nodes) {
      const currentPath = [...path, node]
      
      if (node[id] === targetId) {
        ancestors.push(...path)
        return true
      }
      
      if (node[children] && Array.isArray(node[children]) && node[children].length > 0) {
        if (traverse(node[children], currentPath)) {
          return true
        }
      }
    }
    return false
  }

  traverse(tree, [])
  return ancestors
}