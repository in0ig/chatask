# 数据源选择器用户体验优化方案

## 1. 优化目标
基于测试标准 `frontend/tests/unit/components/DataSourceSelector.test.ts`，优化数据源选择器组件的用户体验，确保满足以下测试要求：
1. 测试空状态显示逻辑
2. 测试加载指示器显示
3. 测试错误重试按钮功能
4. 测试数据源选择交互
5. 测试覆盖率 ≥ 80%
6. 100% 测试通过，0 TypeScript 错误

## 2. 当前组件分析
根据前端组件 `DataSourceSelector.vue` 的分析，当前实现具备以下功能：
- 基于 Element Plus 的 `el-dialog` 实现数据源选择弹窗
- 支持搜索、标签页操作（全选/反选/置顶）、单表预览与批量确认
- 使用 `v-model` 双向绑定控制弹窗显示
- 通过 `computed` 属性动态计算已选数量和过滤结果

但存在以下用户体验问题：
- 无空状态提示（当搜索无结果时）
- 无加载指示器（数据源列表加载时）
- 无错误重试机制（数据源加载失败时）
- 未显示数据源类型（MySQL/Excel）
- "置顶"功能未实现实际排序逻辑
- 无键盘快捷键支持

## 3. 优化方案
### 3.1 空状态显示
- 当搜索结果为空时，显示提示信息："未找到匹配的数据源，请尝试其他关键词"
- 使用 Element Plus 的 `el-empty` 组件实现美观的空状态样式

### 3.2 加载指示器
- 在数据源列表加载时，显示骨架屏（skeleton）或 loading 动画
- 使用 Element Plus 的 `el-skeleton` 组件或自定义 loading 状态
- 加载状态由 `loading` 状态变量控制

### 3.3 错误重试按钮
- 当数据源加载失败时，显示错误信息和重试按钮
- 重试按钮触发 `fetchDataSources()` 方法重新获取数据
- 错误状态由 `error` 状态变量控制

### 3.4 数据源类型标识
- 在每个数据源项中显示类型标识，如：`MySQL: users` 或 `Excel: sales_2025.xlsx`
- 使用图标区分数据源类型（数据库图标、文件图标）

### 3.5 置顶功能实现
- 实现"置顶"功能：将选中的数据源移至列表顶部
- 使用数组操作：将选中项从原位置移除，插入到数组开头

### 3.6 键盘快捷键支持
- ESC 键关闭弹窗
- Enter 键确认选择

## 4. 实现计划
1. 修改 `DataSourceSelector.vue` 组件，添加以下状态变量：
   - `loading: boolean`
   - `error: string | null`
   - `emptySearch: boolean`
2. 更新数据获取逻辑，添加加载和错误处理
3. 修改模板，添加空状态、加载指示器和错误重试按钮
4. 实现置顶功能和键盘快捷键支持
5. 更新测试用例，确保覆盖所有新功能

## 5. 测试验证
- 确保测试文件 `frontend/tests/unit/components/DataSourceSelector.test.ts` 包含以下测试用例：
  - 测试空状态显示逻辑
  - 测试加载指示器显示
  - 测试错误重试按钮功能
  - 测试数据源选择交互
- 测试覆盖率 ≥ 80%
- 100% 测试通过，0 TypeScript 错误

## 6. 风险与注意事项
- 所有修改必须保持与现有代码风格一致
- 不得修改组件的公共 API（props 和 emits）
- 优先使用 Element Plus 组件确保样式一致性
- 修改后需在前端项目中运行测试验证

## 7. 参考文档
- @.kiro/specs/data-source-display-fix/requirements.md
- @.kiro/specs/data-source-display-fix/design.md
- @frontend/src/components/DataSource/DataSourceSelector.vue
- frontend/tests/unit/components/DataSourceSelector.test.ts

> 本方案为优化数据源选择器用户体验的正式设计文档，开发人员需严格按照此方案实施。