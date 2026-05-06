# 数据准备组件迁移说明

## 组件结构重构 - 任务 1.1

### 新的组件结构

根据设计文档，新的组件结构已按照以下方式重新组织：

#### Views 层级 (frontend/src/views/DataPrep/)
```
DataPrep/
├── DataPreparationManager.vue     # 主容器 (标签页导航) - 待实现
├── DataSources/
│   └── DataSourceList.vue         # 数据源列表页面 - 任务 2.1
├── DataTables/
│   └── DataTableManager.vue       # 数据表管理主页 - 任务 3.1
├── Dictionaries/
│   └── DictionaryManager.vue      # 字典管理主页 - 任务 4.1
└── Relations/
    └── RelationManager.vue        # 关联管理主页 - 任务 5.1
```

#### Components 层级 (frontend/src/components/DataPreparation/)
```
DataPreparation/
├── DataSourceTable.vue            # 数据源表格 - 任务 2.1
├── ConnectionTest.vue              # 连接测试 - 任务 2.3
├── DataTableTree.vue              # 数据表树形组件 - 任务 3.1
├── ExcelImport/                    # Excel 导入组件组 - 任务 3.2
│   ├── FileUpload.vue
│   ├── SheetSelector.vue
│   ├── DataPreview.vue
│   └── ImportWizard.vue
├── DatabaseTableSelector.vue      # 数据库表选择器 - 任务 3.3
├── SqlBuilder.vue                 # SQL 建表 - 任务 3.4
├── TableSyncProgress.vue          # 表同步进度 - 任务 3.5
├── DictionaryItemList.vue         # 字典项列表 - 任务 4.1
├── DictionaryForm.vue             # 字典表单 - 任务 4.2
├── DictionaryItemForm.vue         # 字典项表单 - 任务 4.3
├── DictionaryItemBatchEdit.vue    # 字典项批量编辑 - 任务 4.3
├── RelationList.vue               # 关联列表 - 任务 5.2
├── RelationTable.vue              # 关联表格 - 任务 5.2
├── RelationGraph.vue              # 可视化关联图 - 任务 5.3
├── RelationForm.vue               # 关联配置表单 - 任务 5.4
└── RelationGraphEditor.vue        # 图形编辑功能 - 任务 5.5
```

### 旧组件处理

以下旧组件将在后续任务中被重构或替换：

#### 需要重构的组件
- `DataPreparationManager.vue` - 将在任务 1.2 中更新为新的标签页结构
- `DataSourceList.vue` - 将在任务 2.1 中重构为表格列表布局
- `DataSourceForm.vue` - 将在任务 2.2 中重构，支持所有数据库类型
- `DataTableDetail.vue` - 将在任务 3.1 中重构为详情面板
- `DictionaryTree.vue` - 将在任务 4.1 中重构，支持父子关系
- `DictionaryImportExport.vue` - 将在任务 4.4 中重构

#### 需要移除的组件（卡片式布局）
- `DataTableList.vue` - 替换为树形+详情面板布局
- `DataTableForm.vue` - 功能整合到其他组件中
- `TableRelationList.vue` - 替换为新的关联管理组件
- `TableRelationForm.vue` - 重构为 RelationForm.vue
- `TableRelationGraph.vue` - 重构为 RelationGraph.vue

### 状态管理重构

新的状态管理结构 (`frontend/src/store/modules/dataPreparation.ts`) 已创建，包含：

- 更清晰的状态分组
- 完整的 TypeScript 类型定义
- 模块化的 Actions 设计
- UI 状态管理

### 工具文件

新增工具文件：
- `frontend/src/utils/graphLayout.ts` - 图形布局算法（任务 5.3）

### 实施计划

1. **任务 1.1 (当前)**: 组件结构重构 ✅
2. **任务 1.2**: 更新路由配置
3. **任务 1.3**: 重构状态管理（已完成基础结构）
4. **任务 2.1-8.3**: 按计划实施各功能模块

### 注意事项

- 所有新组件都包含占位符内容，标明将在哪个任务中实现
- 旧组件暂时保留，避免破坏现有功能
- 新的状态管理与旧版本兼容，确保平滑迁移
- 所有组件都遵循 Vue 3 Composition API 规范
- 使用 TypeScript 严格模式，确保类型安全

### 验收标准检查

✅ 创建新的组件目录结构  
✅ 建立清晰的组件层级关系  
⏳ 移除旧的卡片式组件（将在后续任务中完成）

组件结构重构已完成，为后续任务奠定了基础。