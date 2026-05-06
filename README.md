# ChatBI - 智能数据分析对话系统

基于 Vue 3 + FastAPI + MySQL + Qwen 的智能数据分析对话系统，复刻腾讯云 ChatBI 核心功能。

## 技术栈

### 前端
- Vue 3 + TypeScript
- Pinia (状态管理)
- Element Plus (UI 组件库)
- ECharts (图表可视化)
- Vitest (单元测试)

### 后端
- FastAPI (Python Web 框架)
- MySQL (数据库)
- Qwen (大语言模型)
- SQLAlchemy (ORM)
- Alembic (数据库迁移)

## 快速开始

### 前置要求
- Node.js >= 18
- Python >= 3.12
- MySQL >= 8.0

### 安装依赖

**前端：**
```bash
cd frontend
npm install
```

**后端：**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 配置环境变量

复制 `backend/.env.example` 到 `backend/.env` 并配置数据库连接等信息。

### 运行项目

**启动后端：**
```bash
cd backend
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端：**
```bash
cd frontend
npm run dev
```

访问 http://localhost:5173

## 项目结构

```
ChatBI/
├── frontend/          # 前端项目
│   ├── src/
│   │   ├── components/  # Vue 组件
│   │   ├── views/       # 页面组件
│   │   ├── store/       # Pinia 状态管理
│   │   └── router/      # 路由配置
│   └── tests/          # 单元测试
├── backend/           # 后端项目
│   ├── src/
│   │   ├── api/        # API 路由
│   │   ├── services/   # 业务逻辑
│   │   ├── models/     # 数据模型
│   │   └── schemas/    # Pydantic 模型
│   └── tests/         # 单元测试
└── database/          # 数据库脚本
```

## 核心功能

- ✅ 智能对话式数据查询
- ✅ 多轮对话上下文管理
- ✅ SQL 自动生成与执行
- ✅ 数据可视化（图表自动推荐）
- ✅ 会话管理（创建、切换、删除）
- ✅ 数据源管理
- ✅ 数据表管理
- ✅ 字典表管理
- ✅ 表关联管理

## 开发规范

详见 `.kiro/steering/chatbi-development-rules.md`

## License

MIT
