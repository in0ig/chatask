import api from '@/services/api'

// 字典类型定义
export interface Dictionary {
  id: string
  code: string
  name: string
  description?: string
  parent_id?: string
  is_enabled: boolean
  created_at: string
  updated_at: string
  children?: Dictionary[]
}

// 字典项类型定义
export interface DictionaryItem {
  id: string
  dictionary_id: string
  item_key: string
  item_value: string
  description?: string
  sort_order: number
  is_enabled: boolean
  created_at: string
  updated_at: string
}

// 创建字典请求参数
export interface CreateDictionaryRequest {
  code: string
  name: string
  description?: string
  parent_id?: string
  is_enabled?: boolean
}

// 更新字典请求参数
export interface UpdateDictionaryRequest extends Partial<CreateDictionaryRequest> {}

// 创建字典项请求参数
export interface CreateDictionaryItemRequest {
  item_key: string
  item_value: string
  description?: string
  sort_order?: number
  is_enabled?: boolean
}

// 更新字典项请求参数
export interface UpdateDictionaryItemRequest extends Partial<CreateDictionaryItemRequest> {}

// 字典API服务
export const dictionaryApi = {
  // 获取所有字典
  getAll(params?: { page?: number; page_size?: number; search?: string; status?: boolean; parent_id?: string }): Promise<Dictionary[]> {
    return api.get('/dictionaries', { params }).then(response => response.data)
  },
  
  // 获取字典树形结构
  getTree(status?: boolean): Promise<Dictionary[]> {
    return api.get('/dictionaries/tree', { 
      params: status !== undefined ? { status } : {} 
    }).then(response => response.data)
  },
  
  // 根据ID获取单个字典
  getById(id: string): Promise<Dictionary> {
    return api.get(`/dictionaries/${id}`).then(response => response.data)
  },
  
  // 创建新字典
  create(dictionary: CreateDictionaryRequest): Promise<Dictionary> {
    return api.post('/dictionaries', dictionary).then(response => response.data)
  },
  
  // 更新现有字典
  update(id: string, updates: UpdateDictionaryRequest): Promise<Dictionary> {
    return api.put(`/dictionaries/${id}`, updates).then(response => response.data)
  },
  
  // 删除字典
  delete(id: string): Promise<void> {
    return api.delete(`/dictionaries/${id}`).then(response => response.data)
  },

  // 获取字典项列表
  getItems(dictionaryId: string, params?: { page?: number; page_size?: number; search?: string; status?: boolean }): Promise<DictionaryItem[]> {
    return api.get(`/dictionaries/${dictionaryId}/items`, { params }).then(response => response.data)
  },

  // 创建字典项
  createItem(dictionaryId: string, item: CreateDictionaryItemRequest): Promise<DictionaryItem> {
    return api.post(`/dictionaries/${dictionaryId}/items`, item).then(response => response.data)
  },

  // 更新字典项
  updateItem(dictionaryId: string, itemId: string, updates: UpdateDictionaryItemRequest): Promise<DictionaryItem> {
    return api.put(`/dictionaries/${dictionaryId}/items/${itemId}`, updates).then(response => response.data)
  },

  // 删除字典项
  deleteItem(dictionaryId: string, itemId: string): Promise<void> {
    return api.delete(`/dictionaries/${dictionaryId}/items/${itemId}`).then(response => response.data)
  },

  // 批量创建字典项
  batchCreateItems(dictionaryId: string, items: CreateDictionaryItemRequest[]): Promise<{ success_count: number; failed_count: number; failed_items: any[] }> {
    return api.post(`/dictionaries/${dictionaryId}/items/batch`, { items }).then(response => response.data)
  },
  
  // 导出字典
  export(id: string, format: 'excel' | 'csv'): Promise<{ download_url: string; file_name: string }> {
    return api.get(`/dictionaries/${id}/export`, {
      params: { format_type: format }
    }).then(response => response.data)
  },

  // 导入字典
  import(id: string, file: File): Promise<{ success_count: number; failed_count: number; failed_items: any[] }> {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/dictionaries/${id}/import`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }).then(response => response.data)
  }
}
