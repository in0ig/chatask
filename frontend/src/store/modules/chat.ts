/**
 * 聊天状态管理 Store
 */
import { defineStore } from 'pinia'
import type { ChatState, ChatSession, ChatMessage, WSMessage } from '@/types/chat'
import { isStreamingEnabled } from '@/config/streaming'

export const useChatStore = defineStore('chat', {
  state: (): ChatState => ({
    currentSessionId: null,
    sessions: {},
    isConnected: false,
    isStreaming: false,
    error: null,
    chatMode: 'query' as 'query' | 'report', // 'query' = 智能问数, 'report' = 生成报告
    dataSource: [], // 当前选择的数据源 ID 列表
    selectedDataTables: [] // 当前选择的数据表 ID 列表
  }),

  getters: {
    // 获取当前会话
    currentSession(state): ChatSession | null {
      if (!state.currentSessionId) return null
      return state.sessions[state.currentSessionId] || null
    },

    // 获取当前会话的消息列表
    currentMessages(state): ChatMessage[] {
      if (!state.currentSessionId) return []
      const session = state.sessions[state.currentSessionId]
      return session?.messages || []
    },

    // 获取所有会话列表
    sessionList(state): ChatSession[] {
      return Object.values(state.sessions).sort((a, b) => b.updatedAt - a.updatedAt)
    }
  },

  actions: {
    // 创建新会话
    createSession(title: string = '新对话'): string {
      const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      const session: ChatSession = {
        session_id: sessionId,  // 使用 session_id 而不是 id
        title,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: []
      }
      this.sessions[sessionId] = session
      this.currentSessionId = sessionId
      
      // 保存到 localStorage
      this.saveSessions()
      
      console.log('✅ 新会话已创建并保存:', sessionId, '标题:', title)
      return sessionId
    },

    // 切换会话
    async switchSession(sessionId: string) {
      if (!this.sessions[sessionId]) {
        console.warn(`会话 ${sessionId} 不存在`)
        return
      }
      
      // 立即切换 currentSessionId，让 UI 先响应
      this.currentSessionId = sessionId
      // 清空旧消息，准备加载
      this.sessions[sessionId].messages = []
      
      try {
        // 从后端加载会话详情（包含历史消息）
        const response = await fetch(`/api/sessions/${sessionId}`)
        const data = await response.json()
        
        if (data.success && data.data) {
          const sessionData = data.data
          // local_messages：包含完整 stages 数据的 assistant 消息
          // cloud_messages：user + assistant 交替的精简上下文（用于补充缺失的 user 消息）
          const localMsgs: any[] = sessionData.local_messages || []
          const cloudMsgs: any[] = sessionData.cloud_messages || []

          console.log('📊 [switchSession] local_messages 数量:', localMsgs.length)
          console.log('📊 [switchSession] cloud_messages 数量:', cloudMsgs.length)

          // 检查 local_messages 里是否有 user 消息
          const localHasUserMsgs = localMsgs.some((m: any) => m.role === 'user')

          // 构建最终消息列表：
          // 如果 local_messages 里没有 user 消息（旧数据），
          // 则从 cloud_messages 提取 user 消息，与 local assistant 消息按时间戳交织
          const allMessages: any[] = []

          if (!localHasUserMsgs && cloudMsgs.length > 0) {
            // 兜底：从 cloud_messages 提取 user 消息，local_messages 提供 assistant 消息
            const cloudUserMsgs = cloudMsgs
              .filter((m: any) => m.role === 'user')
              .map((m: any) => ({ ...m, source: 'cloud', timestamp: new Date(m.timestamp).getTime() }))

            const localAssistantMsgs = localMsgs
              .filter((m: any) => {
                const hasContent = m.content && m.content.trim() !== ''
                const hasStages = m.stages && Array.isArray(m.stages) && m.stages.length > 0
                return hasContent || hasStages
              })
              .map((m: any) => ({ ...m, source: 'local', timestamp: new Date(m.timestamp).getTime() }))

            // 合并并按时间戳排序
            allMessages.push(...cloudUserMsgs, ...localAssistantMsgs)
            allMessages.sort((a, b) => a.timestamp - b.timestamp)
            console.log(`📊 [switchSession] 兜底模式：从 cloud 补充 ${cloudUserMsgs.length} 条 user 消息`)
          } else {
            // 正常模式：local_messages 包含完整的 user + assistant 消息
            localMsgs.forEach((msg: any) => {
              const hasContent = msg.content && msg.content.trim() !== ''
              const hasStages = msg.stages && Array.isArray(msg.stages) && msg.stages.length > 0
              if (!hasContent && !hasStages) return
              allMessages.push({ ...msg, source: 'local', timestamp: new Date(msg.timestamp).getTime() })
            })
          }

          // 🔥 预处理：修正脏数据中 role 错误的消息（在去重之前）
          // 历史 bug 导致部分 assistant 消息被以 role="user" 存入数据库
          const correctedMessages = allMessages.map((msg: any) => {
            if (msg.role === 'user') {
              const content = msg.content || ''
              const hasAIMarkers = content.includes('【意图识别】') || 
                                   content.includes('【模型思考】') || 
                                   content.includes('【意图澄清】') ||
                                   content.includes('【SQL生成】') ||
                                   content.includes('【智能选表】')
              const hasStages = msg.stages && Array.isArray(msg.stages) && msg.stages.length > 0
              if (hasAIMarkers || hasStages) {
                console.warn('⚠️ [switchSession] 预处理修正脏数据 role: user → assistant')
                return { ...msg, role: 'assistant' }
              }
            }
            return msg
          })

          // 🔥 两步过滤：
          // 1. 过滤掉 content 为空且没有 stages 的 assistant 消息（真正无价值的占位消息）
          //    注意：有实质内容的 assistant 消息一律保留，即使内容是内部标记文本
          //    因为这些内容是历史对话的有效回复，只是格式特殊
          // 2. 过滤掉孤立的 user 消息（后面没有任何 assistant 消息）
          
          // 第一步：只过滤 content 为空且没有 stages 的 assistant 消息
          const withoutEmptyAssistant = correctedMessages.filter((msg: any) => {
            if (msg.role !== 'assistant') return true
            const hasStages = msg.stages && Array.isArray(msg.stages) && msg.stages.length > 0
            const hasContent = msg.content && msg.content.trim() !== ''
            // 有 stages 或有内容的一律保留
            if (hasStages || hasContent) return true
            // content 为空且没有 stages → 过滤掉
            console.warn('⚠️ [switchSession] 过滤掉空内容且无 stages 的 assistant 消息')
            return false
          })
          
          // 第二步：过滤孤立的 user 消息
          // 宽松策略：只要该 user 消息之后（时间戳更大）存在任意一条 assistant 消息，就保留
          // 避免因为相邻 assistant 消息被过滤而误删有效的 user 消息
          const sortedForCheck = [...withoutEmptyAssistant].sort((a, b) => a.timestamp - b.timestamp)
          
          const filteredMessages = withoutEmptyAssistant.filter((msg: any) => {
            if (msg.role !== 'user') return true
            
            // 找到该 user 消息之后是否有任意 assistant 消息
            const hasFollowingAssistant = sortedForCheck.some(m => 
              m.role === 'assistant' && m.timestamp > msg.timestamp
            )
            
            if (!hasFollowingAssistant) {
              console.warn('⚠️ [switchSession] 过滤掉孤立的 user 消息（后面没有 assistant 消息）')
            }
            return hasFollowingAssistant
          })
          
          // 🔥 去重策略：
          // 先按时间戳排序，然后处理两种重复情况：
          // 1. 连续的相同 user 消息（后端 bug 导致同一问题存了多次）：只保留最后一条
          // 2. 5秒内相同内容的任意重复消息
          
          // 先按时间戳排序
          const sortedAll = [...filteredMessages].sort((a, b) => a.timestamp - b.timestamp)
          
          // 第一步：合并连续的相同 user 消息，只保留最后一条
          // 场景：user A, user A, assistant B → 保留最后一条 user A
          const mergedConsecutive: any[] = []
          for (let i = 0; i < sortedAll.length; i++) {
            const msg = sortedAll[i]
            const next = sortedAll[i + 1]
            // 如果当前是 user 消息，且下一条也是相同内容的 user 消息，跳过当前（保留后面的）
            if (msg.role === 'user' && next && next.role === 'user' && 
                (msg.content || '').trim() === (next.content || '').trim()) {
              console.warn('⚠️ [switchSession] 跳过连续重复 user 消息:', (msg.content || '').substring(0, 30))
              continue
            }
            mergedConsecutive.push(msg)
          }
          
          // 第二步：去除 5 秒内相同内容的重复消息（兜底）
          const deduped: any[] = []
          for (const msg of mergedConsecutive) {
            const content = (msg.content || '').trim()
            const role = msg.role
            const isDup = deduped.some(existing => {
              if (existing.role !== role) return false
              if ((existing.content || '').trim() !== content) return false
              const timeDiff = Math.abs(msg.timestamp - existing.timestamp)
              return timeDiff < 5000
            })
            if (!isDup) {
              deduped.push(msg)
            } else {
              console.warn('⚠️ [switchSession] 去除 5 秒内重复消息:', role, content.substring(0, 30))
            }
          }

          console.log(`📊 加载了 ${deduped.length} 条历史消息（去重前 ${filteredMessages.length} 条）`)
          
          // 恢复历史消息
          const finalMessages = deduped
          finalMessages.forEach((msg: any) => {
            const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
            
            // 🔥 修复：修正脏数据中 role 错误的问题
            // 历史 bug 导致部分 assistant 消息被以 role="user" 存入数据库
            // 判断依据：有 stages 数据，或 content 包含 AI 特征标记
            let correctedRole = msg.role
            if (msg.role === 'user') {
              const content = msg.content || ''
              const hasAIMarkers = content.includes('【意图识别】') || 
                                   content.includes('【模型思考】') || 
                                   content.includes('【意图澄清】') ||
                                   content.includes('【SQL生成】') ||
                                   content.includes('【智能选表】')
              const hasStages = msg.stages && Array.isArray(msg.stages) && msg.stages.length > 0
              if (hasAIMarkers || hasStages) {
                correctedRole = 'assistant'
                console.warn('⚠️ [switchSession] 修正脏数据：role user → assistant，content 包含 AI 特征标记')
              }
            }
            
            // 消息类型：assistant 消息统一用 'text'，不依赖 content 关键词判断
            const messageType = 'text'
            
            // 构建完整的消息对象
            const fullMessage: any = {
              id: messageId,
              role: correctedRole,
              content: msg.content || '',
              timestamp: msg.timestamp,
              type: messageType,
              status: 'received',
              metadata: {}
            }
            
            // 🔥 恢复 stages 数据（如果存在）
            if (msg.stages && Array.isArray(msg.stages)) {
              fullMessage.stages = msg.stages
              // 🔥 历史消息的思考过程默认折叠
              fullMessage.thinkingCollapsed = true
              
              // 🔍 调试：打印所有 stage（包含完整信息）
              console.log('📊 [switchSession] 可用的 stages:', msg.stages.map((s: any) => ({
                id: s.id,
                name: s.name,
                hasMetadata: !!s.metadata
              })))
              
              // 🔥 从 stages 中提取图表数据
              // 注意：数据库中使用 'id' 字段，不是 'stage_id'
              const chartStage = msg.stages.find((s: any) => s.id === 'stage_chart')
              console.log('📊 [switchSession] chartStage:', chartStage)
              
              if (chartStage && chartStage.metadata) {
                try {
                  // 从 metadata 中提取图表类型
                  const metadata = chartStage.metadata
                  
                  console.log('📊 [switchSession] chartStage.metadata:', metadata)
                  
                  if (metadata.chart_type) {
                    fullMessage.chartType = metadata.chart_type
                    console.log(`✅ 恢复了图表类型: ${fullMessage.chartType}`)
                  }
                  
                  // 🔥 检查 metadata 中是否有 chartData（完整的图表数据）
                  if (metadata.chartData) {
                    fullMessage.chartData = metadata.chartData
                    
                    // 🔥 关键修复：将 AI series 和推荐类型注入 chartData，确保切换会话后 SmartChart 能使用 AI 渲染
                    const chartConfig = metadata.chart_config
                    if (chartConfig) {
                      if (chartConfig.chartConfig?.series && chartConfig.chartConfig.series.length > 0) {
                        fullMessage.chartData.series = chartConfig.chartConfig.series
                        console.log(`✅ 注入 AI series 到 chartData: ${chartConfig.chartConfig.series.length} 个 series`)
                      }
                      if (chartConfig.recommendedChart) {
                        fullMessage.chartData.aiRecommendedType = chartConfig.recommendedChart
                        console.log(`✅ 注入 AI 推荐图表类型: ${chartConfig.recommendedChart}`)
                      }
                    }
                    
                    console.log(`✅ 从 chartStage.metadata.chartData 恢复了图表数据: ${metadata.chartData.columns?.length} 列, ${metadata.chartData.rows?.length} 行`)
                  }
                } catch (e) {
                  console.warn('解析图表配置失败:', e)
                }
              }
              
              // 🔥 从 stages 中提取查询结果数据（仅当 chartData 尚未从 stage_chart 恢复时才使用）
              // 注意：stage_chart.metadata.chartData 已包含完整数据 + AI series，优先级最高
              // stage_execute 仅作为兜底，避免覆盖已恢复的 AI series 导致切换会话后图表不一致
              if (!fullMessage.chartData) {
                const sqlExecutionStage = msg.stages.find((s: any) => s.id === 'stage_execute')
                
                console.log('📊 [switchSession] chartData 未从 stage_chart 恢复，尝试从 stage_execute 兜底')
                
                if (sqlExecutionStage && sqlExecutionStage.metadata) {
                  try {
                    const metadata = typeof sqlExecutionStage.metadata === 'string'
                      ? JSON.parse(sqlExecutionStage.metadata)
                      : sqlExecutionStage.metadata
                    
                    const queryResult = metadata.queryResult || metadata
                    
                    if (queryResult && queryResult.columns && queryResult.rows) {
                      fullMessage.chartData = {
                        columns: queryResult.columns,
                        rows: queryResult.rows,
                        metadata: {
                          columnTypes: queryResult.column_types || []
                        }
                      }
                      console.log(`✅ 兜底恢复了图表数据: ${queryResult.columns.length} 列, ${queryResult.rows.length} 行`)
                    } else {
                      console.warn('⚠️ queryResult 缺少 columns 或 rows')
                    }
                  } catch (e) {
                    console.warn('解析查询结果失败:', e)
                  }
                } else {
                  console.warn('⚠️ 未找到查询结果 stage')
                }
              } else {
                console.log('✅ chartData 已从 stage_chart 恢复（含 AI series），跳过 stage_execute 覆盖')
              }
              
              console.log(`✅ 恢复了 ${msg.stages.length} 个流式输出阶段`)
              console.log('📊 [switchSession] fullMessage:', {
                hasChartData: !!fullMessage.chartData,
                chartType: fullMessage.chartType,
                stagesCount: fullMessage.stages.length
              })
            }
            
            this.sessions[sessionId].messages.push(fullMessage)
          })
          
          console.log(`✅ 已切换到会话 ${sessionId}，恢复了 ${deduped.length} 条历史消息`)
        }
      } catch (error) {
        console.error('加载会话历史失败:', error)
        // 即使加载失败，也切换到该会话
        this.currentSessionId = sessionId
      }
    },

    // 删除会话
    deleteSession(sessionId: string) {
      delete this.sessions[sessionId]
      if (this.currentSessionId === sessionId) {
        const sessions = this.sessionList
        this.currentSessionId = sessions.length > 0 ? sessions[0].session_id : null
      }
      // 保存到 localStorage
      this.saveSessions()
    },

    // 添加消息
    addMessage(message: Omit<ChatMessage, 'id' | 'timestamp'>): string {
      if (!this.currentSessionId) {
        this.createSession()
      }

      const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      const newMessage: ChatMessage = {
        ...message,
        id: messageId,
        timestamp: Date.now()
      }

      const session = this.sessions[this.currentSessionId!]
      session.messages.push(newMessage)
      session.updatedAt = Date.now()

      // 保存到 localStorage
      this.saveSessions()

      return messageId
    },

    // 更新消息
    updateMessage(messageId: string, updates: Partial<ChatMessage>) {
      if (!this.currentSessionId) return

      const session = this.sessions[this.currentSessionId]
      const messageIndex = session.messages.findIndex(m => m.id === messageId)
      
      if (messageIndex !== -1) {
        session.messages[messageIndex] = {
          ...session.messages[messageIndex],
          ...updates
        }
        session.updatedAt = Date.now()
      }
    },

    // 删除消息
    removeMessage(messageId: string) {
      if (!this.currentSessionId) return

      const session = this.sessions[this.currentSessionId]
      const messageIndex = session.messages.findIndex(m => m.id === messageId)
      
      if (messageIndex !== -1) {
        session.messages.splice(messageIndex, 1)
        session.updatedAt = Date.now()
      }
    },

    // 追加消息内容（用于流式输出）
    appendMessageContent(messageId: string, content: string) {
      if (!this.currentSessionId) return

      const session = this.sessions[this.currentSessionId]
      const message = session.messages.find(m => m.id === messageId)
      
      if (message) {
        message.content += content
        session.updatedAt = Date.now()
      }
    },

    // 添加阶段到消息
    addStageToMessage(messageId: string, stage: any) {
      if (!this.currentSessionId) return

      const session = this.sessions[this.currentSessionId]
      const message = session.messages.find(m => m.id === messageId)
      
      if (message) {
        if (!message.stages) {
          message.stages = []
        }
        message.stages.push(stage)
        session.updatedAt = Date.now()
      }
    },

    // 更新消息中的阶段
    updateStageInMessage(messageId: string, stageId: string, updates: any) {
      if (!this.currentSessionId) return

      const session = this.sessions[this.currentSessionId]
      const message = session.messages.find(m => m.id === messageId)
      
      if (message && message.stages) {
        const stage = message.stages.find(s => s.id === stageId)
        if (stage) {
          Object.assign(stage, updates)
          session.updatedAt = Date.now()
        }
      }
    },

    // 追加阶段内容
    appendStageContent(messageId: string, stageId: string, content: string) {
      if (!this.currentSessionId) return

      const session = this.sessions[this.currentSessionId]
      const message = session.messages.find(m => m.id === messageId)
      
      if (message && message.stages) {
        const stage = message.stages.find(s => s.id === stageId)
        if (stage) {
          stage.content += content
          session.updatedAt = Date.now()
        }
      }
    },

    // 处理 stage_update WebSocket 消息
    handleStageUpdate(stageId: string, content: string) {
      // 🔍 调试日志：接收到 stage_update 消息
      console.log('🔍 [handleStageUpdate] 接收到增量内容:', {
        stageId,
        contentLength: content.length,
        contentPreview: content.substring(0, 50) + (content.length > 50 ? '...' : ''),
        timestamp: Date.now()
      })
      
      // 检查是否启用流式输出
      if (!isStreamingEnabled()) {
        console.log('⚠️ 流式输出已禁用，忽略 stage_update 消息')
        return
      }
      
      if (!this.currentSessionId) {
        console.warn('⚠️ [handleStageUpdate] 当前没有活动会话')
        return
      }

      const session = this.sessions[this.currentSessionId]
      
      // 找到当前的 assistant 消息（最后一条 assistant 消息）
      const messageIndex = [...session.messages]
        .map((m, idx) => ({ message: m, index: idx }))
        .reverse()
        .find(item => item.message.role === 'assistant')?.index
      
      if (messageIndex === undefined) {
        console.warn('⚠️ [handleStageUpdate] 未找到当前 assistant 消息')
        return
      }
      
      const currentMessage = session.messages[messageIndex]
      
      if (!currentMessage.stages) {
        console.warn('⚠️ [handleStageUpdate] 当前消息没有 stages 数组')
        return
      }
      
      // 找到对应的 stage 索引
      const stageIndex = currentMessage.stages.findIndex(s => s.id === stageId)
      
      if (stageIndex === -1) {
        console.warn('⚠️ [handleStageUpdate] 未找到对应的 stage:', stageId)
        console.log('📋 [handleStageUpdate] 可用的 stages:', currentMessage.stages.map(s => s.id))
        return
      }
      
      const stage = currentMessage.stages[stageIndex]
      
      // 记录更新前的状态
      const oldLength = stage.content.length
      
      // ✅ 关键修复：创建新的 stage 对象并替换，触发 Vue 响应式更新
      const updatedStage = {
        ...stage,
        content: stage.content + content
      }
      
      // 替换整个 stage 对象（触发响应式）
      currentMessage.stages[stageIndex] = updatedStage
      
      // 🔥 强制触发响应式更新：重新赋值整个 stages 数组
      currentMessage.stages = [...currentMessage.stages]
      
      // 记录更新后的状态
      const newLength = updatedStage.content.length
      
      console.log('✅ [handleStageUpdate] 内容已追加（创建新对象）:', {
        stageId,
        oldLength,
        newLength,
        addedLength: newLength - oldLength,
        totalContent: updatedStage.content.length
      })
      
      // 更新时间戳
      session.updatedAt = Date.now()
    },

    // 设置连接状态
    setConnected(connected: boolean) {
      this.isConnected = connected
    },

    // 设置流式状态
    setStreaming(streaming: boolean) {
      this.isStreaming = streaming
    },

    // 设置错误
    setError(error: string | null) {
      this.error = error
    },

    // 清空当前会话
    clearCurrentSession() {
      if (this.currentSessionId) {
        this.sessions[this.currentSessionId].messages = []
      }
    },

    // 编辑消息
    editMessage(messageId: string, newContent: string) {
      if (!this.currentSessionId) return

      const session = this.sessions[this.currentSessionId]
      const message = session.messages.find(m => m.id === messageId)
      
      if (message) {
        message.content = newContent
        session.updatedAt = Date.now()
      }
    },

    // 重发消息
    resendMessage(messageId: string) {
      if (!this.currentSessionId) return

      const session = this.sessions[this.currentSessionId]
      const message = session.messages.find(m => m.id === messageId)
      
      if (message) {
        message.status = 'sending'
        message.timestamp = Date.now()
        session.updatedAt = Date.now()
      }
    },

    // 回溯到消息
    rollbackToMessage(messageId: string) {
      if (!this.currentSessionId) return

      const session = this.sessions[this.currentSessionId]
      const messageIndex = session.messages.findIndex(m => m.id === messageId)
      
      if (messageIndex !== -1) {
        // 删除该消息之后的所有消息
        session.messages = session.messages.slice(0, messageIndex + 1)
        session.updatedAt = Date.now()
      }
    },

    // 导出消息
    exportMessage(messageId: string, format: string) {
      // 导出逻辑在组件中处理，这里只记录操作
      console.log(`Exporting message ${messageId} as ${format}`)
    },

    // 分享消息
    shareMessage(messageId: string, method: string) {
      // 分享逻辑在组件中处理，这里只记录操作
      console.log(`Sharing message ${messageId} via ${method}`)
    },

    // 切换聊天模式
    toggleChatMode() {
      this.chatMode = this.chatMode === 'query' ? 'report' : 'query'
    },

    // 设置数据源
    setDataSource(dataSourceIds: string | string[]) {
      // 支持单个字符串或数组
      this.dataSource = Array.isArray(dataSourceIds) ? dataSourceIds : [dataSourceIds]
    },

    // 设置数据表
    setDataTables(tableIds: string[]) {
      this.selectedDataTables = tableIds
    },

    // 发送消息
    async sendMessage(content: string) {
      // 添加用户消息
      this.addMessage({
        role: 'user',
        type: 'text',
        content,
        status: 'sent'
      })

      // 这里应该调用 API 发送消息
      // 暂时只是添加一个占位的 AI 响应
      this.addMessage({
        role: 'assistant',
        type: 'text',
        content: '这是一个占位响应。实际应用中，这里应该调用后端 API。',
        status: 'sent'
      })
    },

    // 加载会话列表
    async loadSessions() {
      console.log('Loading sessions...')
      try {
        const response = await fetch(`/api/sessions/?limit=50&offset=0`)
        if (response.ok) {
          const data = await response.json()
          if (data.success && data.data.sessions) {
            // 将后端会话数据同步到本地 sessions 对象
            data.data.sessions.forEach((session: any) => {
              if (!this.sessions[session.session_id]) {
                this.sessions[session.session_id] = {
                  session_id: session.session_id,
                  title: session.title || '新对话',
                  createdAt: session.created_at,
                  updatedAt: session.last_activity_at,
                  messages: []
                }
              }
            })
            console.log('✅ 会话列表已从后端加载，数量:', data.data.sessions.length)
          }
        }
      } catch (error) {
        console.warn('⚠️ 从后端加载会话列表失败:', error)
        // 失败时使用本地存储的会话
      }
    },

    // 加载历史记录
    async loadHistory() {
      console.log('Loading history...')
      // 从 localStorage 加载历史记录
      const savedSessions = localStorage.getItem('chatbi_sessions')
      if (savedSessions) {
        try {
          const parsed = JSON.parse(savedSessions)
          // 合并到现有 sessions
          Object.assign(this.sessions, parsed)
          console.log('✅ 历史记录已从 localStorage 加载')
        } catch (error) {
          console.warn('⚠️ 解析历史记录失败:', error)
        }
      }
    },

    // 保存会话到 localStorage
    saveSessions() {
      try {
        localStorage.setItem('chatbi_sessions', JSON.stringify(this.sessions))
        console.log('✅ 会话已保存到 localStorage，数量:', Object.keys(this.sessions).length)
      } catch (error) {
        console.error('❌ 保存会话到 localStorage 失败:', error)
      }
    }
  }
})
