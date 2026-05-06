import { test, expect } from '@playwright/test'

test('张三下了几单？流式输出验证（内容变化）', async ({ page }) => {
  await page.goto('http://localhost:5174/')
  await page.waitForLoadState('networkidle')

  // 输入问题
  const question = '张三下了几单？'
  const inputBox = page.locator('textarea[placeholder*="输入"]').first()
  await inputBox.fill(question)

  // 发送消息
  const sendButton = page.locator('button:has-text("发送")').first()
  await sendButton.click()

  // 监听流式内容变化
  const stageSelector = '.message-thinking, .stage-thinking, .message-result, .stage-result'
  const stage = page.locator(stageSelector).first()

  let lastContent = ''
  let changeCount = 0
  const start = Date.now()
  const timeout = 30000

  // 检查内容多次变化
  while (Date.now() - start < timeout) {
    if (await stage.isVisible()) {
      const content = await stage.textContent() || ''
      if (content.length > 0 && content !== lastContent) {
        if (lastContent && content.length > lastContent.length) {
          changeCount++
        }
        lastContent = content
      }
      if (content.includes('张三') && /\d+/.test(content)) {
        break
      }
    }
    await page.waitForTimeout(300)
  }

  // 断言内容变化次数
  expect(changeCount).toBeGreaterThanOrEqual(2)
  expect(lastContent).toContain('张三')
  expect(lastContent).toMatch(/\d+/)

  await page.screenshot({
    path: 'test-results/zhangsan-order-streaming.png',
    fullPage: true
  })

  console.log(`✅ 内容变化次数: ${changeCount}`)
  console.log('✅ 张三下单数流式对话流式性测试通过！')
})
