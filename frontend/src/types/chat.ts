/**
 * 聊天消息类型定义
 */

// 消息类型
export type MessageType = 'text' | 'sql' | 'table' | 'chart' | 'error' | 'thinking' | 'stage'

// 消息角色
export type MessageRole = 'user' | 'assistant' | 'system'

// 消息状态
export type MessageStatus = 'sending' | 'sent' | 'streaming' | 'completed' | 'error'

// 阶段状态
export type StageStatus = 'in_progress' | 'completed' | 'error'

// 阶段接口
export interface MessageStage {
  id: string
  name: string
  status: StageStatus
  content: string
  collapsed: boolean
  timestamp: number
  metadata?: Record<string, any>
}

// 消息接口
export interface ChatMessage {
  id: string
  role: MessageRole
  type: MessageType
  content: string
  status: MessageStatus
  timestamp: number
  metadata?: Record<string, any>
  // 图表相关字段
  chartData?: any // ChartData 类型
  chartType?: string // 图表类型
  tableData?: any[] // 表格数据
  tableHeaders?: string[] // 表格列头
  viewMode?: 'chart' | 'table' | 'both' // 视图模式
  // 阶段相关字段
  stages?: MessageStage[] // 消息包含的阶段列表
}

// 会话接口
export interface ChatSession {
  session_id: string  // 改为 session_id 以匹配后端 API
  title: string
  createdAt: number
  updatedAt: number
  messages: ChatMessage[]
}

// WebSocket消息接口
export interface WSMessage {
  type: 'message' | 'thinking' | 'result' | 'error' | 'complete' | 'stage_start' | 'stage_update' | 'stage_complete'
  content: string
  messageId?: string
  metadata?: Record<string, any>
  // 阶段相关字段
  stage_id?: string
  stage_name?: string
  stage_status?: StageStatus
  collapsible?: boolean
  collapsed?: boolean
}

// 聊天状态接口
export interface ChatState {
  currentSessionId: string | null
  sessions: Record<string, ChatSession>
  isConnected: boolean
  isStreaming: boolean
  error: string | null
  chatMode: 'query' | 'report' // 'query' = 智能问数, 'report' = 生成报告
  dataSource: string[] // 当前选择的数据源 ID 列表
  selectedDataTables: string[] // 当前选择的数据表 ID 列表
}
