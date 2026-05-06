/**
 * 通用状态管理类型定义
 */

/**
 * 异步状态接口
 */
export interface AsyncState<T> {
  /** 数据 */
  data: T
  /** 加载状态 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 最后更新时间 */
  lastUpdated?: string
}

/**
 * 分页状态接口
 */
export interface PaginationState {
  /** 当前页码 */
  current: number
  /** 每页大小 */
  pageSize: number
  /** 总数量 */
  total: number
  /** 是否显示快速跳转 */
  showQuickJumper?: boolean
  /** 是否显示页面大小选择器 */
  showSizeChanger?: boolean
}

/**
 * 搜索状态接口
 */
export interface SearchState {
  /** 搜索关键词 */
  keyword: string
  /** 搜索字段 */
  fields: string[]
  /** 高级搜索条件 */
  filters: Record<string, any>
  /** 排序字段 */
  sortField?: string
  /** 排序方向 */
  sortOrder?: 'asc' | 'desc'
}

/**
 * 选择状态接口
 */
export interface SelectionState<T = string> {
  /** 选中的项 */
  selectedKeys: T[]
  /** 选择模式 */
  mode: 'single' | 'multiple'
  /** 是否全选 */
  selectAll: boolean
  /** 半选状态 */
  indeterminate: boolean
}

/**
 * 模态框状态接口
 */
export interface ModalState {
  /** 是否可见 */
  visible: boolean
  /** 模态框标题 */
  title?: string
  /** 模态框数据 */
  data?: any
  /** 模态框模式 */
  mode?: 'create' | 'edit' | 'view'
  /** 是否加载中 */
  loading?: boolean
}

/**
 * 树形数据状态接口
 */
export interface TreeState<T> {
  /** 树形数据 */
  data: T[]
  /** 展开的节点 */
  expandedKeys: string[]
  /** 选中的节点 */
  selectedKeys: string[]
  /** 检查的节点 */
  checkedKeys: string[]
  /** 是否自动展开父节点 */
  autoExpandParent: boolean
}

/**
 * 表格状态接口
 */
export interface TableState<T> {
  /** 表格数据 */
  data: T[]
  /** 分页状态 */
  pagination: PaginationState
  /** 搜索状态 */
  search: SearchState
  /** 选择状态 */
  selection: SelectionState
  /** 加载状态 */
  loading: boolean
  /** 错误信息 */
  error: string | null
}

/**
 * 操作结果接口
 */
export interface OperationResult<T = any> {
  /** 是否成功 */
  success: boolean
  /** 结果数据 */
  data?: T
  /** 消息 */
  message?: string
  /** 错误代码 */
  code?: string
}

/**
 * API 响应接口
 */
export interface ApiResponse<T = any> {
  /** 状态码 */
  code: number
  /** 消息 */
  message: string
  /** 数据 */
  data: T
  /** 是否成功 */
  success: boolean
  /** 时间戳 */
  timestamp: number
}

/**
 * 分页响应接口
 */
export interface PagedResponse<T> {
  /** 数据列表 */
  list: T[]
  /** 总数量 */
  total: number
  /** 当前页码 */
  current: number
  /** 每页大小 */
  pageSize: number
  /** 总页数 */
  pages: number
}

/**
 * 创建异步状态的工厂函数
 */
export function createAsyncState<T>(initialData: T): AsyncState<T> {
  return {
    data: initialData,
    loading: false,
    error: null,
    lastUpdated: undefined
  }
}

/**
 * 创建分页状态的工厂函数
 */
export function createPaginationState(
  current = 1,
  pageSize = 10,
  total = 0
): PaginationState {
  return {
    current,
    pageSize,
    total,
    showQuickJumper: true,
    showSizeChanger: true
  }
}

/**
 * 创建搜索状态的工厂函数
 */
export function createSearchState(): SearchState {
  return {
    keyword: '',
    fields: [],
    filters: {},
    sortField: undefined,
    sortOrder: undefined
  }
}

/**
 * 创建选择状态的工厂函数
 */
export function createSelectionState<T = string>(
  mode: 'single' | 'multiple' = 'multiple'
): SelectionState<T> {
  return {
    selectedKeys: [],
    mode,
    selectAll: false,
    indeterminate: false
  }
}

/**
 * 创建模态框状态的工厂函数
 */
export function createModalState(): ModalState {
  return {
    visible: false,
    title: undefined,
    data: undefined,
    mode: undefined,
    loading: false
  }
}

/**
 * 创建树形状态的工厂函数
 */
export function createTreeState<T>(): TreeState<T> {
  return {
    data: [],
    expandedKeys: [],
    selectedKeys: [],
    checkedKeys: [],
    autoExpandParent: true
  }
}

/**
 * 创建表格状态的工厂函数
 */
export function createTableState<T>(): TableState<T> {
  return {
    data: [],
    pagination: createPaginationState(),
    search: createSearchState(),
    selection: createSelectionState(),
    loading: false,
    error: null
  }
}