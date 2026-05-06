// 通用 API 响应类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// 数据源类型
export interface DataSource {
  id: number
  name: string
  type: string
  host?: string
  port?: number
  database?: string
  username?: string
  password?: string
  description?: string
  is_enabled: boolean
  created_at: string
  updated_at: string
}

// 数据表类型
export interface DataTable {
  id: number
  name: string
  source_id: number
  table_name: string
  description?: string
  row_count?: number
  is_enabled: boolean
  created_at: string
  updated_at: string
}

// 表字段类型
export interface TableField {
  id: number
  table_id: number
  name: string
  type: string
  is_primary_key: boolean
  is_nullable: boolean
  default_value?: string
  description?: string
  created_at: string
  updated_at: string
}

// 字典类型
export interface Dictionary {
  id: string  // UUID string, not number
  name: string
  code: string
  dict_type: string  // Changed from 'type' to 'dict_type'
  parent_id?: string  // UUID string, not number
  description?: string
  status: boolean  // Changed from 'is_enabled' to 'status'
  sort_order?: number
  created_by?: string
  created_at: string
  updated_at: string
}

// 字典项类型
export interface DictionaryItem {
  id: string  // UUID string, not number
  dictionary_id: string  // UUID string, not number
  item_key: string
  item_value: string
  description?: string
  sort_order: number
  status: boolean  // Changed from 'is_enabled' to 'status'
  extra_data?: any
  created_by?: string
  created_at: string
  updated_at: string
}

// 表关系类型
export interface TableRelation {
  id: number
  name: string
  source_table_id: number
  source_field_id: number
  target_table_id: number
  target_field_id: number
  relation_type: string
  description?: string
  is_enabled: boolean
  created_at: string
  updated_at: string
}

// 字段映射类型
export interface FieldMapping {
  id?: number
  table_id: number
  field_id: number
  dictionary_id?: number
  business_name?: string
  description?: string
  is_enabled: boolean
  created_at?: string
  updated_at?: string
}

// 数据准备状态类型
export interface DataPreparationState {
  loading: boolean
  error: string | null
}