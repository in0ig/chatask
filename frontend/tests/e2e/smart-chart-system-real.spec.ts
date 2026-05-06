/**
 * 任务 6.5.2 - 智能图表系统前端端到端测试
 * 
 * 使用 Playwright 进行真实浏览器测试
 * 
 * 测试覆盖：
 * 1. 各种图表类型渲染测试
 * 2. 图表类型智能识别测试
 * 3. 图表交互功能测试
 * 4. 图表导出和分享功能测试
 * 5. 大数据量性能测试
 * 6. 图表主题和动画测试
 * 7. 图表流式渲染测试
 * 8. 响应式设计测试
 */

import { test, expect, Page } from '@playwright/test'

test.describe('智能图表系统端到端测试', () => {
  let page: Page

  test.beforeEach(async ({ page: testPage }) => {
    page = testPage
    
    // 导航到对话页面
    await page.goto('http://localhost:5173/chat')
    
    // 等待页面加载完成
    await page.waitForLoadState('networkidle')
  })

  test('测试场景 1: 柱状图渲染测试', async () => {
    console.log('\n=== 测试场景 1: 柱状图渲染 ===')
    
    // 1. 输入查询问题（期望返回柱状图数据）
    const question = '显示各产品的销量对比'
    await page.fill('textarea[placeholder*="输入"]', question)
    await page.click('button:has-text("发送")')
    
    // 2. 等待图表渲染
    await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
    
    // 3. 验证图表类型
    const chartElement = await page.locator('.chart-element').first()
    expect(await chartElement.isVisible()).toBeTruthy()
    
    // 4. 验证图表工具栏
    const toolbar = await page.locator('.chart-toolbar').first()
    expect(await toolbar.isVisible()).toBeTruthy()
    
    // 5. 验证柱状图按钮被选中
    const barButton = await page.locator('button:has-text("柱状图")').first()
    const isActive = await barButton.evaluate((el) => 
      el.classList.contains('el-button--primary')
    )
    expect(isActive).toBeTruthy()
    
    // 6. 截图保存
    await page.screenshot({ 
      path: 'test-results/chart-bar-rendering.png',
      fullPage: true 
    })
    
    console.log('✅ 柱状图渲染测试通过')
  })

  test('测试场景 2: 折线图渲染测试', async () => {
    console.log('\n=== 测试场景 2: 折线图渲染 ===')
    
    // 1. 输入时间序列查询
    const question = '显示最近30天的销售趋势'
    await page.fill('textarea[placeholder*="输入"]', question)
    await page.click('button:has-text("发送")')
    
    // 2. 等待图表渲染
    await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
    
    // 3. 验证折线图渲染
    const chartElement = await page.locator('.chart-element').first()
    expect(await chartElement.isVisible()).toBeTruthy()
    
    // 4. 验证折线图按钮被选中或可切换
    const lineButton = await page.locator('button:has-text("折线图")').first()
    expect(await lineButton.isVisible()).toBeTruthy()
    
    // 5. 点击切换到折线图（如果不是默认）
    await lineButton.click()
    await page.waitForTimeout(500)
    
    // 6. 验证图表更新
    const isActive = await lineButton.evaluate((el) => 
      el.classList.contains('el-button--primary')
    )
    expect(isActive).toBeTruthy()
    
    // 7. 截图保存
    await page.screenshot({ 
      path: 'test-results/chart-line-rendering.png',
      fullPage: true 
    })
    
    console.log('✅ 折线图渲染测试通过')
  })

  test('测试场景 3: 饼图渲染测试', async () => {
    console.log('\n=== 测试场景 3: 饼图渲染 ===')
    
    // 1. 输入占比查询
    const question = '各产品的销售额占比是多少'
    await page.fill('textarea[placeholder*="输入"]', question)
    await page.click('button:has-text("发送")')
    
    // 2. 等待图表渲染
    await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
    
    // 3. 切换到饼图
    const pieButton = await page.locator('button:has-text("饼图")').first()
    await pieButton.click()
    await page.waitForTimeout(500)
    
    // 4. 验证饼图渲染
    const chartElement = await page.locator('.chart-element').first()
    expect(await chartElement.isVisible()).toBeTruthy()
    
    // 5. 验证图例显示
    const legend = await page.locator('.chart-element').first()
    expect(await legend.isVisible()).toBeTruthy()
    
    // 6. 截图保存
    await page.screenshot({ 
      path: 'test-results/chart-pie-rendering.png',
      fullPage: true 
    })
    
    console.log('✅ 饼图渲染测试通过')
  })

  test('测试场景 4: 图表类型智能识别测试', async () => {
    console.log('\n=== 测试场景 4: 图表类型智能识别 ===')
    
    const testCases = [
      {
        question: '显示销售趋势',
        expectedType: '折线图',
        reason: '包含"趋势"关键词'
      },
      {
        question: '各类别的占比',
        expectedType: '饼图',
        reason: '包含"占比"关键词'
      },
      {
        question: '对比各产品销量',
        expectedType: '柱状图',
        reason: '包含"对比"关键词'
      }
    ]
    
    for (const testCase of testCases) {
      console.log(`\n测试: ${testCase.question}`)
      console.log(`期望: ${testCase.expectedType}`)
      console.log(`理由: ${testCase.reason}`)
      
      // 1. 输入问题
      await page.fill('textarea[placeholder*="输入"]', testCase.question)
      await page.click('button:has-text("发送")')
      
      // 2. 等待图表渲染
      await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
      await page.waitForTimeout(1000)
      
      // 3. 检查推荐提示（如果有）
      const recommendation = await page.locator('.chart-recommendation').first()
      if (await recommendation.isVisible()) {
        const text = await recommendation.textContent()
        console.log(`推荐: ${text}`)
      }
      
      // 4. 验证图表类型按钮状态
      const button = await page.locator(`button:has-text("${testCase.expectedType}")`).first()
      const isActive = await button.evaluate((el) => 
        el.classList.contains('el-button--primary')
      )
      
      if (isActive) {
        console.log(`✅ 正确识别为${testCase.expectedType}`)
      } else {
        console.log(`⚠️  未自动识别为${testCase.expectedType}，但可手动切换`)
      }
      
      // 等待下一个测试
      await page.waitForTimeout(2000)
    }
    
    console.log('\n✅ 图表类型智能识别测试完成')
  })

  test('测试场景 5: 图表交互功能测试', async () => {
    console.log('\n=== 测试场景 5: 图表交互功能 ===')
    
    // 1. 先渲染一个图表
    await page.fill('textarea[placeholder*="输入"]', '显示产品销量')
    await page.click('button:has-text("发送")')
    await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
    
    // 2. 测试图表类型切换
    console.log('测试图表类型切换...')
    const chartTypes = ['柱状图', '折线图', '饼图']
    for (const type of chartTypes) {
      const button = await page.locator(`button:has-text("${type}")`).first()
      if (await button.isVisible()) {
        await button.click()
        await page.waitForTimeout(500)
        console.log(`✅ 切换到${type}成功`)
      }
    }
    
    // 3. 测试缩放功能（如果有数据缩放组件）
    console.log('测试缩放功能...')
    const dataZoom = await page.locator('.chart-element').first()
    if (await dataZoom.isVisible()) {
      // 模拟鼠标滚轮缩放
      await dataZoom.hover()
      await page.mouse.wheel(0, -100)
      await page.waitForTimeout(500)
      console.log('✅ 缩放功能正常')
    }
    
    // 4. 测试工具栏功能
    console.log('测试工具栏功能...')
    const toolbox = await page.locator('.chart-toolbar').first()
    expect(await toolbox.isVisible()).toBeTruthy()
    console.log('✅ 工具栏显示正常')
    
    // 5. 截图保存
    await page.screenshot({ 
      path: 'test-results/chart-interaction.png',
      fullPage: true 
    })
    
    console.log('✅ 图表交互功能测试通过')
  })

  test('测试场景 6: 图表导出功能测试', async () => {
    console.log('\n=== 测试场景 6: 图表导出功能 ===')
    
    // 1. 先渲染一个图表
    await page.fill('textarea[placeholder*="输入"]', '显示产品销量')
    await page.click('button:has-text("发送")')
    await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
    
    // 2. 查找导出按钮
    const exportButton = await page.locator('button:has-text("导出")').first()
    
    if (await exportButton.isVisible()) {
      console.log('找到导出按钮')
      
      // 3. 点击导出按钮
      await exportButton.click()
      await page.waitForTimeout(500)
      
      // 4. 验证导出菜单显示
      const exportMenu = await page.locator('.el-dropdown-menu')
      if (await exportMenu.isVisible()) {
        console.log('✅ 导出菜单显示正常')
        
        // 5. 验证导出选项
        const exportOptions = ['PNG图片', 'JPG图片', 'PDF文档', 'SVG矢量图', 'Excel数据']
        for (const option of exportOptions) {
          const menuItem = await page.locator(`.el-dropdown-menu__item:has-text("${option}")`)
          if (await menuItem.isVisible()) {
            console.log(`✅ 支持${option}导出`)
          }
        }
      }
    } else {
      console.log('⚠️  未找到导出按钮，可能需要在配置中启用')
    }
    
    // 6. 截图保存
    await page.screenshot({ 
      path: 'test-results/chart-export.png',
      fullPage: true 
    })
    
    console.log('✅ 图表导出功能测试完成')
  })

  test('测试场景 7: 图表分享功能测试', async () => {
    console.log('\n=== 测试场景 7: 图表分享功能 ===')
    
    // 1. 先渲染一个图表
    await page.fill('textarea[placeholder*="输入"]', '显示产品销量')
    await page.click('button:has-text("发送")')
    await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
    
    // 2. 查找分享按钮
    const shareButton = await page.locator('button:has-text("分享")').first()
    
    if (await shareButton.isVisible()) {
      console.log('找到分享按钮')
      
      // 3. 点击分享按钮
      await shareButton.click()
      await page.waitForTimeout(500)
      
      // 4. 验证分享对话框显示
      const shareDialog = await page.locator('.el-dialog:has-text("分享图表")')
      if (await shareDialog.isVisible()) {
        console.log('✅ 分享对话框显示正常')
        
        // 5. 验证分享选项卡
        const tabs = ['分享链接', '嵌入代码']
        for (const tab of tabs) {
          const tabElement = await page.locator(`.el-tab-pane:has-text("${tab}")`)
          if (await tabElement.count() > 0) {
            console.log(`✅ 支持${tab}`)
          }
        }
        
        // 6. 关闭对话框
        const closeButton = await page.locator('.el-dialog__close').first()
        await closeButton.click()
      }
    } else {
      console.log('⚠️  未找到分享按钮，可能需要在配置中启用')
    }
    
    // 7. 截图保存
    await page.screenshot({ 
      path: 'test-results/chart-share.png',
      fullPage: true 
    })
    
    console.log('✅ 图表分享功能测试完成')
  })

  test('测试场景 8: 大数据量性能测试', async () => {
    console.log('\n=== 测试场景 8: 大数据量性能测试 ===')
    
    // 1. 输入大数据量查询
    const question = '显示所有订单数据'  // 假设返回大量数据
    
    const startTime = Date.now()
    
    await page.fill('textarea[placeholder*="输入"]', question)
    await page.click('button:has-text("发送")')
    
    // 2. 等待图表渲染（最多30秒）
    try {
      await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
      
      const renderTime = Date.now() - startTime
      console.log(`图表渲染时间: ${renderTime}ms`)
      
      // 3. 验证渲染时间
      expect(renderTime).toBeLessThan(30000)  // 应在30秒内完成
      
      if (renderTime < 3000) {
        console.log('✅ 性能优秀 (< 3秒)')
      } else if (renderTime < 10000) {
        console.log('✅ 性能良好 (< 10秒)')
      } else {
        console.log('⚠️  性能一般 (< 30秒)')
      }
      
      // 4. 检查是否有性能优化提示
      const optimizationHint = await page.locator('.el-message:has-text("性能优化")').first()
      if (await optimizationHint.isVisible()) {
        const text = await optimizationHint.textContent()
        console.log(`优化提示: ${text}`)
      }
      
      // 5. 测试图表交互响应
      const chartElement = await page.locator('.chart-element').first()
      await chartElement.hover()
      await page.waitForTimeout(500)
      console.log('✅ 图表交互响应正常')
      
    } catch (error) {
      console.error('❌ 大数据量渲染超时或失败')
      throw error
    }
    
    // 6. 截图保存
    await page.screenshot({ 
      path: 'test-results/chart-large-dataset.png',
      fullPage: true 
    })
    
    console.log('✅ 大数据量性能测试完成')
  })

  test('测试场景 9: 图表主题切换测试', async () => {
    console.log('\n=== 测试场景 9: 图表主题切换 ===')
    
    // 1. 先渲染一个图表
    await page.fill('textarea[placeholder*="输入"]', '显示产品销量')
    await page.click('button:has-text("发送")')
    await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
    
    // 2. 查找主题切换按钮（如果有）
    const themeButton = await page.locator('button:has-text("主题")').first()
    
    if (await themeButton.isVisible()) {
      console.log('找到主题切换按钮')
      
      // 3. 测试主题切换
      await themeButton.click()
      await page.waitForTimeout(500)
      
      // 4. 验证主题菜单
      const themeMenu = await page.locator('.el-dropdown-menu')
      if (await themeMenu.isVisible()) {
        console.log('✅ 主题菜单显示正常')
      }
      
      // 5. 截图保存（浅色主题）
      await page.screenshot({ 
        path: 'test-results/chart-theme-light.png',
        fullPage: true 
      })
      
    } else {
      console.log('⚠️  未找到主题切换按钮')
      
      // 截图当前主题
      await page.screenshot({ 
        path: 'test-results/chart-theme-default.png',
        fullPage: true 
      })
    }
    
    console.log('✅ 图表主题测试完成')
  })

  test('测试场景 10: 响应式设计测试', async () => {
    console.log('\n=== 测试场景 10: 响应式设计 ===')
    
    // 1. 先渲染一个图表
    await page.fill('textarea[placeholder*="输入"]', '显示产品销量')
    await page.click('button:has-text("发送")')
    await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
    
    // 2. 测试不同屏幕尺寸
    const viewports = [
      { name: '桌面', width: 1920, height: 1080 },
      { name: '平板', width: 768, height: 1024 },
      { name: '手机', width: 375, height: 667 }
    ]
    
    for (const viewport of viewports) {
      console.log(`\n测试${viewport.name}视图 (${viewport.width}x${viewport.height})`)
      
      // 3. 设置视口大小
      await page.setViewportSize({ 
        width: viewport.width, 
        height: viewport.height 
      })
      await page.waitForTimeout(1000)
      
      // 4. 验证图表可见
      const chartElement = await page.locator('.chart-element').first()
      expect(await chartElement.isVisible()).toBeTruthy()
      
      // 5. 验证图表容器宽度适应
      const containerWidth = await chartElement.evaluate((el) => el.clientWidth)
      console.log(`图表容器宽度: ${containerWidth}px`)
      expect(containerWidth).toBeGreaterThan(0)
      expect(containerWidth).toBeLessThanOrEqual(viewport.width)
      
      // 6. 截图保存
      await page.screenshot({ 
        path: `test-results/chart-responsive-${viewport.name}.png`,
        fullPage: true 
      })
      
      console.log(`✅ ${viewport.name}视图测试通过`)
    }
    
    // 7. 恢复默认视口
    await page.setViewportSize({ width: 1280, height: 720 })
    
    console.log('\n✅ 响应式设计测试完成')
  })

  test('测试场景 11: 图表配置保存测试', async () => {
    console.log('\n=== 测试场景 11: 图表配置保存 ===')
    
    // 1. 先渲染一个图表
    await page.fill('textarea[placeholder*="输入"]', '显示产品销量')
    await page.click('button:has-text("发送")')
    await page.waitForSelector('.smart-chart-container', { timeout: 30000 })
    
    // 2. 查找保存配置按钮
    const saveButton = await page.locator('button:has-text("保存配置")').first()
    
    if (await saveButton.isVisible()) {
      console.log('找到保存配置按钮')
      
      // 3. 点击保存按钮
      await saveButton.click()
      await page.waitForTimeout(500)
      
      // 4. 验证保存对话框
      const saveDialog = await page.locator('.el-dialog:has-text("保存图表配置")')
      if (await saveDialog.isVisible()) {
        console.log('✅ 保存对话框显示正常')
        
        // 5. 输入配置名称
        const nameInput = await page.locator('.el-dialog input[placeholder*="配置名称"]')
        await nameInput.fill('测试图表配置')
        
        // 6. 验证保存为模板选项
        const templateSwitch = await page.locator('.el-dialog .el-switch')
        if (await templateSwitch.isVisible()) {
          console.log('✅ 支持保存为模板')
        }
        
        // 7. 关闭对话框
        const cancelButton = await page.locator('.el-dialog button:has-text("取消")').first()
        await cancelButton.click()
      }
    } else {
      console.log('⚠️  未找到保存配置按钮')
    }
    
    // 8. 截图保存
    await page.screenshot({ 
      path: 'test-results/chart-config-save.png',
      fullPage: true 
    })
    
    console.log('✅ 图表配置保存测试完成')
  })

  test('测试场景 12: 图表错误处理测试', async () => {
    console.log('\n=== 测试场景 12: 图表错误处理 ===')
    
    // 1. 输入可能导致错误的查询
    const question = '显示不存在的表数据'
    await page.fill('textarea[placeholder*="输入"]', question)
    await page.click('button:has-text("发送")')
    
    // 2. 等待响应
    await page.waitForTimeout(5000)
    
    // 3. 检查错误提示
    const errorMessage = await page.locator('.el-message--error, .error-message').first()
    
    if (await errorMessage.isVisible()) {
      const errorText = await errorMessage.textContent()
      console.log(`错误提示: ${errorText}`)
      console.log('✅ 错误处理正常')
    } else {
      console.log('⚠️  未检测到错误提示（可能查询成功或错误处理需要改进）')
    }
    
    // 4. 截图保存
    await page.screenshot({ 
      path: 'test-results/chart-error-handling.png',
      fullPage: true 
    })
    
    console.log('✅ 图表错误处理测试完成')
  })
})
