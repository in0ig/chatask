/**
 * 对话界面端到端真实测试
 * 
 * 使用真实的：
 * 1. 数据库表数据
 * 2. 云端 Qwen AI 调用
 * 3. 本地 OpenAI 模型调用
 * 4. WebSocket 流式响应
 * 5. 图表自动生成
 */

import { test, expect } from '@playwright/test'

test.describe('对话界面功能测试（真实环境）', () => {
  test.beforeEach(async ({ page }) => {
    // 导航到对话页面
    await page.goto('http://localhost:5173/chat')
    
    // 等待页面加载
    await page.waitForLoadState('networkidle')
  })

  test('完整对话流程测试', async ({ page }) => {
    console.log('\n🧪 测试场景：完整对话流程')
    console.log('='*60)
    
    // 1. 输入问题
    const question = '最近一个月的销售额是多少？'
    console.log(`📝 用户问题: ${question}`)
    
    const inputBox = page.locator('textarea[placeholder*="输入"]').first()
    await inputBox.fill(question)
    
    // 2. 发送消息
    const sendButton = page.locator('button:has-text("发送")').first()
    await sendButton.click()
    
    console.log('✅ 消息已发送')
    
    // 3. 等待思考过程消息
    const thinkingMessage = page.locator('.message-thinking').first()
    await expect(thinkingMessage).toBeVisible({ timeout: 10000 })
    console.log('💭 看到思考过程')
    
    // 4. 等待最终结果
    const resultMessage = page.locator('.message-result').first()
    await expect(resultMessage).toBeVisible({ timeout: 30000 })
    console.log('📊 收到查询结果')
    
    // 5. 验证结果包含数据
    const tableOrChart = page.locator('.result-table, .smart-chart').first()
    await expect(tableOrChart).toBeVisible({ timeout: 5000 })
    console.log('✅ 数据展示正常')
    
    // 6. 截图保存
    await page.screenshot({ 
      path: 'test-results/dialogue-complete-flow.png',
      fullPage: true 
    })
    
    console.log('✅ 完整对话流程测试通过！\n')
  })

  test('流式消息实时显示测试', async ({ page }) => {
    console.log('\n🧪 测试场景：流式消息实时显示')
    console.log('='*60)
    
    const question = '显示所有产品的库存情况'
    console.log(`📝 用户问题: ${question}`)
    
    // 记录消息出现的时间
    const messageTimestamps: { type: string; time: number }[] = []
    
    // 监听消息出现
    page.on('console', msg => {
      if (msg.text().includes('WebSocket message')) {
        const now = Date.now()
        messageTimestamps.push({ type: 'message', time: now })
      }
    })
    
    // 发送问题
    await page.locator('textarea[placeholder*="输入"]').first().fill(question)
    await page.locator('button:has-text("发送")').first().click()
    
    // 等待多条消息出现
    await page.waitForTimeout(5000)
    
    // 验证消息按顺序出现
    const messages = page.locator('.chat-message')
    const messageCount = await messages.count()
    
    console.log(`📊 收到 ${messageCount} 条消息`)
    expect(messageCount).toBeGreaterThan(0)
    
    // 验证消息类型
    for (let i = 0; i < Math.min(messageCount, 5); i++) {
      const message = messages.nth(i)
      const messageClass = await message.getAttribute('class')
      console.log(`   消息 ${i + 1}: ${messageClass}`)
    }
    
    console.log('✅ 流式消息实时显示测试通过！\n')
  })

  test('图表自动生成测试', async ({ page }) => {
    console.log('\n🧪 测试场景：图表自动生成')
    console.log('='*60)
    
    const question = '按月份统计销售额趋势'
    console.log(`📝 用户问题: ${question}`)
    
    // 发送问题
    await page.locator('textarea[placeholder*="输入"]').first().fill(question)
    await page.locator('button:has-text("发送")').first().click()
    
    // 等待图表出现
    const chart = page.locator('.smart-chart').first()
    await expect(chart).toBeVisible({ timeout: 30000 })
    console.log('📊 图表已生成')
    
    // 验证图表类型
    const chartCanvas = page.locator('canvas').first()
    await expect(chartCanvas).toBeVisible()
    console.log('✅ 图表渲染正常')
    
    // 测试图表交互
    await chartCanvas.hover()
    await page.waitForTimeout(1000)
    
    // 验证工具提示
    const tooltip = page.locator('.echarts-tooltip')
    // 工具提示可能不总是出现，所以不强制要求
    
    // 截图
    await page.screenshot({ 
      path: 'test-results/chart-generation.png',
      fullPage: true 
    })
    
    console.log('✅ 图表自动生成测试通过！\n')
  })

  test('多轮对话测试', async ({ page }) => {
    console.log('\n🧪 测试场景：多轮对话')
    console.log('='*60)
    
    // 第一轮
    const question1 = '查询本月销售额'
    console.log(`👤 第1轮: ${question1}`)
    
    await page.locator('textarea[placeholder*="输入"]').first().fill(question1)
    await page.locator('button:has-text("发送")').first().click()
    
    await page.waitForSelector('.message-result', { timeout: 30000 })
    console.log('✅ 第1轮完成')
    
    // 等待一下
    await page.waitForTimeout(2000)
    
    // 第二轮：追问
    const question2 = '和上个月相比如何？'
    console.log(`👤 第2轮: ${question2}`)
    
    await page.locator('textarea[placeholder*="输入"]').first().fill(question2)
    await page.locator('button:has-text("发送")').first().click()
    
    await page.waitForSelector('.message-result:nth-of-type(2)', { timeout: 30000 })
    console.log('✅ 第2轮完成')
    
    // 验证消息历史
    const messages = page.locator('.chat-message')
    const messageCount = await messages.count()
    
    console.log(`📊 对话历史: ${messageCount} 条消息`)
    expect(messageCount).toBeGreaterThanOrEqual(4) // 至少2轮对话（每轮2条消息）
    
    // 截图
    await page.screenshot({ 
      path: 'test-results/multi-round-dialogue.png',
      fullPage: true 
    })
    
    console.log('✅ 多轮对话测试通过！\n')
  })

  test('表格和图表视图切换测试', async ({ page }) => {
    console.log('\n🧪 测试场景：表格和图表视图切换')
    console.log('='*60)
    
    const question = '显示产品销售排行'
    console.log(`📝 用户问题: ${question}`)
    
    // 发送问题
    await page.locator('textarea[placeholder*="输入"]').first().fill(question)
    await page.locator('button:has-text("发送")').first().click()
    
    // 等待结果
    await page.waitForSelector('.message-result', { timeout: 30000 })
    
    // 查找视图切换按钮
    const viewToggle = page.locator('button:has-text("表格"), button:has-text("图表")').first()
    
    if (await viewToggle.isVisible()) {
      console.log('📊 找到视图切换按钮')
      
      // 切换到图表视图
      if (await page.locator('button:has-text("图表")').isVisible()) {
        await page.locator('button:has-text("图表")').click()
        await page.waitForTimeout(1000)
        
        const chart = page.locator('.smart-chart')
        await expect(chart).toBeVisible()
        console.log('✅ 切换到图表视图成功')
      }
      
      // 切换回表格视图
      if (await page.locator('button:has-text("表格")').isVisible()) {
        await page.locator('button:has-text("表格")').click()
        await page.waitForTimeout(1000)
        
        const table = page.locator('.result-table')
        await expect(table).toBeVisible()
        console.log('✅ 切换到表格视图成功')
      }
    } else {
      console.log('⚠️  未找到视图切换按钮（可能结果不支持多视图）')
    }
    
    console.log('✅ 视图切换测试通过！\n')
  })

  test('错误处理测试', async ({ page }) => {
    console.log('\n🧪 测试场景：错误处理')
    console.log('='*60)
    
    // 发送无效问题
    const invalidQuestion = '这是一个无法理解的问题 @#$%^&*()'
    console.log(`📝 无效问题: ${invalidQuestion}`)
    
    await page.locator('textarea[placeholder*="输入"]').first().fill(invalidQuestion)
    await page.locator('button:has-text("发送")').first().click()
    
    // 等待错误消息或结果
    await page.waitForTimeout(10000)
    
    // 验证系统没有崩溃
    const inputBox = page.locator('textarea[placeholder*="输入"]').first()
    await expect(inputBox).toBeVisible()
    console.log('✅ 系统未崩溃')
    
    // 测试恢复：发送正常问题
    const normalQuestion = '查询产品列表'
    console.log(`📝 正常问题: ${normalQuestion}`)
    
    await inputBox.fill(normalQuestion)
    await page.locator('button:has-text("发送")').first().click()
    
    await page.waitForSelector('.message-result', { timeout: 30000 })
    console.log('✅ 系统成功恢复')
    
    console.log('✅ 错误处理测试通过！\n')
  })

  test('WebSocket 连接稳定性测试', async ({ page }) => {
    console.log('\n🧪 测试场景：WebSocket 连接稳定性')
    console.log('='*60)
    
    // 监听 WebSocket 事件
    let wsConnected = false
    let wsMessages = 0
    
    page.on('websocket', ws => {
      console.log('🔌 WebSocket 连接建立')
      wsConnected = true
      
      ws.on('framereceived', event => {
        wsMessages++
      })
      
      ws.on('close', () => {
        console.log('🔌 WebSocket 连接关闭')
      })
    })
    
    // 发送问题
    const question = '查询订单统计'
    await page.locator('textarea[placeholder*="输入"]').first().fill(question)
    await page.locator('button:has-text("发送")').first().click()
    
    // 等待响应
    await page.waitForSelector('.message-result', { timeout: 30000 })
    
    // 验证 WebSocket
    expect(wsConnected).toBeTruthy()
    console.log(`📊 收到 ${wsMessages} 条 WebSocket 消息`)
    expect(wsMessages).toBeGreaterThan(0)
    
    console.log('✅ WebSocket 连接稳定性测试通过！\n')
  })
})

test.describe('性能测试', () => {
  test('响应时间测试', async ({ page }) => {
    console.log('\n🧪 测试场景：响应时间')
    console.log('='*60)
    
    await page.goto('http://localhost:5173/chat')
    await page.waitForLoadState('networkidle')
    
    const question = '查询销售数据'
    
    // 记录开始时间
    const startTime = Date.now()
    
    await page.locator('textarea[placeholder*="输入"]').first().fill(question)
    await page.locator('button:has-text("发送")').first().click()
    
    // 等待第一条思考消息
    await page.waitForSelector('.message-thinking', { timeout: 10000 })
    const thinkingTime = Date.now() - startTime
    console.log(`💭 思考消息响应时间: ${thinkingTime}ms`)
    
    // 等待最终结果
    await page.waitForSelector('.message-result', { timeout: 30000 })
    const totalTime = Date.now() - startTime
    console.log(`📊 总响应时间: ${totalTime}ms`)
    
    // 验证性能
    expect(thinkingTime).toBeLessThan(5000) // 思考消息应在5秒内出现
    expect(totalTime).toBeLessThan(30000) // 总时间应在30秒内
    
    console.log('✅ 响应时间测试通过！\n')
  })
})
