# ChatBI 项目优化方案

基于对 Claude Code 项目源码的研究，提出以下 6 个优化方向的具体方案。

**文档版本**: v1.0  
**创建日期**: 2026-04-09  
**参考项目**: Claude Code (src/tools/, src/skills/, src/context/, src/history/)

---

## 目录

1. [财务日历日期推断优化](#1-财务日历日期推断优化)
2. [Agent 主导架构改造](#2-agent 主导架构改造)
3. [Prompt 优化](#3-prompt 优化)
4. [上下文管理和压缩](#4-上下文管理和压缩)
5. [Harness 框架评估](#5-harness 框架评估)
6. [Skill 和 Tool 化分析](#6-skill 和 tool 化分析)

---

## 1. 财务日历日期推断优化

### 当前问题

- 财务日历在推断时容易弄错日期
- 放在 prompt 中会存在写死的问题，模型容易产生幻觉
- 农历/节假日日期模型自行推断极易出错（如 2026 年春节模型可能混淆为 1 月 29 日，实际是 2 月 17 日）

### Claude Code 借鉴方案

Claude Code 使用 **动态上下文注入** 模式，在对话开始前动态获取真实状态：

```typescript
// src/Tool.ts - getGitStatus
// 在对话开始前动态获取真实状态，而不是写死在 prompt 中
export const getGitStatus = memoize(async (): Promise<string | null> => {
  const [branch, mainBranch, status, log, userName] = await Promise.all([
    getBranch(),
    getDefaultBranch(),
    gitStatusShort(),
    gitLog(),
    getGitUser()
  ]);
  // 动态生成上下文信息
  return `Current branch: ${branch}...`;
});
```

### 优化方案

#### 方案 A：Tool 化财务日历查询（推荐）

```python
# src/tools/fiscal_calendar_tool.py

from harness import Tool
from typing import Optional, List

class FiscalCalendarTool(Tool):
    """
    财务日历查询工具 - 动态查询真实日期
    
    使用场景:
    - 用户提到"2026 年 1 月第二周" → 查询返回 FW22 的具体日期
    - 用户提到"春节" → 查询知识库中的节假日事件
    - 用户提到"上个月最后一周" → 先确定月份，再查财周
    
    返回格式:
    {
        "fw_label": "FW22",
        "start_date": "2026-01-05",
        "end_date": "2026-01-11",
        "fy_n": 2026,
        "fm_n": 1
    }
    """
    
    name = "fiscal_calendar"
    description = "查询财务日历，将自然日期/节假日转换为财周日期范围"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string", 
                "description": "日期查询，如'2026 年 1 月第二周'、'春节'、'上个月最后一周'"
            },
            "reference_date": {
                "type": "string",
                "description": "参考日期 (用于相对时间计算)，ISO 格式"
            }
        },
        "required": ["query"]
    }
    
    async def invoke(
        self, 
        query: str, 
        reference_date: Optional[str] = None
    ) -> dict:
        """
        查询财务日历
        """
        from src.services.time_resolver import FiscalCalendarRepository
        from src.models.fiscal_calendar_model import FiscalCalendar
        
        repo = FiscalCalendarRepository()
        
        # 1. 解析查询类型
        parsed = await self._parse_query(query, reference_date)
        
        if parsed["type"] == "holiday":
            # 查询节假日事件（知识库）
            result = await self._lookup_holiday(parsed["name"])
        elif parsed["type"] == "month_week":
            # 查询自然月中的第 N 个财周
            result = await repo.lookup_month_week(
                year=parsed["year"],
                month=parsed["month"],
                week_index=parsed["week_index"]
            )
        elif parsed["type"] == "relative":
            # 相对时间（上周/本周/上月）
            result = await repo.lookup_relative(parsed["offset"], parsed["unit"])
        else:
            # 直接财周查询
            result = await repo.lookup_by_label(parsed["fw_label"])
        
        if not result:
            return {
                "error": f"未找到匹配的财务日历：{query}",
                "suggestion": "请检查日期格式或使用更明确的财周标签 (如 FW22)"
            }
        
        return {
            "fw_label": result.fw_label,
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "fy_n": result.fy_n,
            "fm_n": result.fm_n,
            "fw_n": result.fw_n,
            "days_in_week": result.fw_n_days
        }
    
    async def _parse_query(self, query: str, reference_date: Optional[str]) -> dict:
        """解析查询类型"""
        # 节假日匹配
        holiday_names = ["春节", "国庆", "中秋", "元旦", "清明", "端午", "圣诞"]
        for name in holiday_names:
            if name in query:
                return {"type": "holiday", "name": name}
        
        # 第 N 周匹配
        import re
        week_pattern = r"(\d{4}) 年 (\d{1,2}) 月第 (\d+|-1) 周"
        match = re.search(week_pattern, query)
        if match:
            return {
                "type": "month_week",
                "year": int(match.group(1)),
                "month": int(match.group(2)),
                "week_index": int(match.group(3))
            }
        
        # 相对时间匹配
        if "上周" in query:
            return {"type": "relative", "offset": -1, "unit": "week"}
        if "本周" in query:
            return {"type": "relative", "offset": 0, "unit": "week"}
        
        # 默认：尝试解析为财周标签
        fw_match = re.search(r"FW(\d+)", query)
        if fw_match:
            return {"type": "fw_label", "fw_label": f"FW{fw_match.group(1)}"}
        
        return {"type": "unknown", "query": query}
    
    async def _lookup_holiday(self, name: str) -> Optional[dict]:
        """从知识库查询节假日日期"""
        from sqlalchemy import select
        from src.models.knowledge_item_model import KnowledgeItem
        from src.database import get_db
        
        db = next(get_db())
        try:
            # 查询知识库中的节假日事件
            stmt = select(KnowledgeItem).where(
                KnowledgeItem.title.ilike(f"%{name}%"),
                KnowledgeItem.category == "holiday_event"
            )
            result = db.execute(stmt).first()
            
            if result:
                item = result[0]
                return {
                    "fw_label": item.metadata.get("fw_label"),
                    "start_date": item.start_date.isoformat(),
                    "end_date": item.end_date.isoformat()
                }
        finally:
            db.close()
        
        return None
```

#### 方案 B：Service 层预解析

```python
# src/services/chat_orchestrator.py 中修改

async def _execute_chat_pipeline(
    self, 
    context: ChatContext, 
    user_question: str, 
    data_source_id: Optional[str]
) -> Dict[str, Any]:
    """
    执行完整对话流水线
    """
    # ... 现有代码 ...
    
    # 🔥 新增：在调用模型前，预解析财务日历
    fiscal_context = await self._resolve_fiscal_dates(user_question, context)
    context.metadata['fiscal_context'] = fiscal_context
    
    # 将财务日历信息注入到 semantic_context
    if fiscal_context.get('resolved_dates'):
        context.metadata['semantic_context'] += f"\n\n财务日历解析结果:\n{fiscal_context['resolved_dates']}"
    
    # ... 继续后续流程 ...

async def _resolve_fiscal_dates(
    self, 
    user_question: str, 
    context: ChatContext
) -> dict:
    """
    预解析财务日历日期
    在发送给模型前，先查询真实日期范围
    """
    from src.services.time_resolver import TimeResolver
    
    resolver = TimeResolver()
    resolved = await resolver.resolve_all(user_question)
    
    return {
        "original_expressions": resolved.expressions,
        "resolved_dates": [
            {
                "expression": expr,
                "fw_label": date.fw_label,
                "start_date": date.start_date.isoformat(),
                "end_date": date.end_date.isoformat()
            }
            for expr, date in resolved.items()
        ],
        "requires_model_injection": len(resolved) > 0
    }
```

### 实施步骤

1. **Phase 1 (1-2 天)**: 创建 `FiscalCalendarTool`
2. **Phase 2 (1 天)**: 在意图澄清阶段自动调用 Tool
3. **Phase 3 (1 天)**: 修改 prompt 移除硬编码日期逻辑
4. **Phase 4 (1 天)**: 测试和验证

---

## 2. Agent 主导架构改造

### 当前问题

- 思考链路是串行的：意图识别 → 选表 → 澄清 → 思考 → SQL 生成 → 执行 → 分析
- 不是 Agent 主导 + 子 Agent 协作模式
- 错误无法隔离，某个环节失败影响整个流程

### Claude Code 借鉴方案

Claude Code 使用 **Coordinator + AgentTool** 架构：

```
src/coordinator/          # 主协调器
src/tools/AgentTool/      # Agent 子任务执行
src/Task.ts               # 任务管理
```

### 优化方案

#### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    ChatOrchestratorAgent                     │
│                     (主 Agent 协调器)                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   IntentAgent   │  │  TableSelector  │  │ ClarifyAgent│ │
│  │   (意图识别)    │  │   Agent (选表)   │  │ (意图澄清)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   ThinkingAgent │  │  SQLGenerator   │  │ ChartAgent  │ │
│  │   (模型思考)    │  │   Agent (SQL 生成)│  │ (图表推荐)  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  AnalysisAgent  │  │  SummaryAgent   │                  │
│  │  (数据分析)     │  │  (结果描述)      │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

#### 代码实现

```python
# src/agents/base_agent.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    consumed_tokens: int = 0
    execution_time_ms: int = 0


class BaseAgent(ABC):
    """Agent 基类"""
    
    name: str
    description: str
    version: str = "1.0"
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """执行 Agent 任务"""
        pass
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        return True
    
    async def _log(self, level: str, message: str, **kwargs):
        """日志记录"""
        from src.utils.logger import logger
        log_msg = f"[{self.name}] {message}"
        if level == "info":
            logger.info(log_msg, **kwargs)
        elif level == "error":
            logger.error(log_msg, **kwargs)
        elif level == "warning":
            logger.warning(log_msg, **kwargs)
```

```python
# src/agents/intent_agent.py

from .base_agent import BaseAgent, AgentResult
import json

class IntentAgent(BaseAgent):
    """
    意图识别 Agent
    负责识别用户问题的意图类型
    """
    
    name = "intent_agent"
    description = "识别用户问题意图 (query/report/followup)"
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行意图识别
        
        Args:
            input_data: {
                "user_question": str,
                "history_context": str,
                "current_date": str
            }
        
        Returns:
            AgentResult with data: {
                "intent": "query" | "report" | "followup",
                "confidence": float,
                "reasoning": str
            }
        """
        from src.services.ai_model_service import get_ai_service
        
        await self._log("info", f"开始意图识别：{input_data.get('user_question', '')[:50]}...")
        
        # 构建 prompt
        prompt = self._build_prompt(input_data)
        
        # 调用模型
        ai_service = get_ai_service()
        response = await ai_service.call_model(
            prompt=prompt,
            stage="intent_recognition"
        )
        
        # 解析结果
        try:
            result_data = json.loads(response["content"])
            return AgentResult(
                success=True,
                data=result_data,
                consumed_tokens=response.get("tokens_used", 0),
                execution_time_ms=int(response.get("response_time", 0) * 1000)
            )
        except json.JSONDecodeError as e:
            return AgentResult(
                success=False,
                data={"intent": "unknown"},
                error=f"意图解析失败：{str(e)}",
                consumed_tokens=response.get("tokens_used", 0)
            )
    
    def _build_prompt(self, input_data: Dict[str, Any]) -> str:
        """构建意图识别 prompt"""
        from src.services.prompt_manager import get_prompt_manager
        
        prompt_manager = get_prompt_manager()
        return prompt_manager.render(
            template_name="intent_recognition",
            variables=input_data
        )
```

```python
# src/agents/orchestrator_agent.py

from .base_agent import BaseAgent, AgentResult
from .intent_agent import IntentAgent
from .table_selector_agent import TableSelectorAgent
from .sql_generator_agent import SQLGeneratorAgent
from .data_analysis_agent import DataAnalysisAgent
from typing import List, Tuple

class OrchestratorAgent(BaseAgent):
    """
    主协调 Agent
    负责任务分解和子 Agent 调度
    """
    
    name = "orchestrator_agent"
    description = "协调多个子 Agent 完成对话任务"
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        # 初始化子 Agent
        self.sub_agents = {
            "intent": IntentAgent(),
            "table_selector": TableSelectorAgent(),
            "sql_generator": SQLGeneratorAgent(),
            "data_analysis": DataAnalysisAgent(),
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行完整对话流程
        
        Args:
            input_data: {
                "session_id": str,
                "user_question": str,
                "data_source_id": Optional[str],
                "history_messages": Optional[List[Dict]]
            }
        """
        session_id = input_data.get("session_id")
        user_question = input_data.get("user_question")
        
        await self._log("info", f"开始处理会话 {session_id}")
        
        # 1. 意图识别
        intent_result = await self.sub_agents["intent"].execute({
            "user_question": user_question,
            "history_context": self._build_history_context(input_data),
            "current_date": self._get_current_date()
        })
        
        if not intent_result.success:
            return AgentResult(
                success=False,
                data={},
                error=f"意图识别失败：{intent_result.error}"
            )
        
        intent_type = intent_result.data.get("intent")
        await self._log("info", f"意图识别结果：{intent_type}")
        
        # 2. 根据意图决定后续流程
        if intent_type == "query":
            return await self._execute_query_flow(input_data, intent_result)
        elif intent_type == "report":
            return await self._execute_report_flow(input_data, intent_result)
        else:
            return await self._execute_followup_flow(input_data, intent_result)
    
    async def _execute_query_flow(
        self, 
        input_data: Dict[str, Any],
        intent_result: AgentResult
    ) -> AgentResult:
        """执行查询流程"""
        # 并行执行选表和意图澄清
        table_result, clarify_result = await asyncio.gather(
            self.sub_agents["table_selector"].execute({
                "user_question": input_data["user_question"],
                "intent_type": intent_result.data["intent"],
                "semantic_context": await self._build_semantic_context(input_data)
            }),
            self.sub_agents["clarify"].execute({
                "user_question": input_data["user_question"],
                "intent_type": intent_result.data["intent"],
                "selected_tables": []
            }),
            return_exceptions=True
        )
        
        # 3. SQL 生成
        sql_result = await self.sub_agents["sql_generator"].execute({
            "original_question": input_data["user_question"],
            "clarified_requirement": clarify_result.data,
            "selected_tables": table_result.data.get("tables", []),
            "semantic_context": await self._build_semantic_context(input_data)
        })
        
        # 4. SQL 执行
        execution_result = await self._execute_sql(sql_result.data.get("sql"))
        
        # 5. 数据分析
        analysis_result = await self.sub_agents["data_analysis"].execute({
            "user_question": input_data["user_question"],
            "query_result": execution_result,
            "thinking_result": sql_result.data
        })
        
        return AgentResult(
            success=True,
            data={
                "intent": intent_result.data,
                "tables": table_result.data,
                "sql": sql_result.data,
                "execution": execution_result,
                "analysis": analysis_result.data
            }
        )
```

### 收益

- **并行执行**: 选表和意图澄清可并行
- **错误隔离**: 单个 Agent 失败不影响其他环节
- **独立优化**: 每个 Agent 可单独测试和调优
- **可复用**: Agent 可在不同场景复用

### 实施步骤

1. **Phase 1 (3 天)**: 创建 BaseAgent 和 4 个核心 Agent
2. **Phase 2 (2 天)**: 创建 OrchestratorAgent
3. **Phase 3 (2 天)**: 并行执行支持
4. **Phase 4 (2 天)**: 测试和迁移

---

## 3. Prompt 优化

### 当前问题

- `prompts.yml` 有 10+ 个 prompt，比较混乱
- 缺少统一的 Prompt 管理框架
- Prompt 内容、工具使用指南、输出格式混在一起

### Claude Code 借鉴方案

Claude Code 的 Skill 系统采用结构化文档：

```
src/skills/bundled/claude-api/skill.md

结构:
1. What This Skill Covers
2. Working Rules
3. Reading Guide
4. Response Style
```

### 优化方案

#### 新的 Prompt 组织结构

```yaml
# backend/config/prompts.yml

# ==================== 系统级指令 ====================

system_core:
  name: "系统核心指令"
  description: "定义 AI 角色、边界、通用规则"
  category: "system"
  content: |
    你是 ChatBI 数据分析助手，专门帮助用户查询和分析数据库。
    
    ## 核心原则
    1. 只生成 SELECT 查询，不执行写操作
    2. 结果 LIMIT 不超过 100 条
    3. 优先使用财周字段 (FW_N) 而非日期范围
    4. 业务术语必须查字典映射
    5. 农历节日日期必须查知识库，禁止自行推断
    
    ## 能力边界
    - 支持：数据查询、图表推荐、趋势分析、对比分析
    - 不支持：数据修改、外部 API 调用、非数据库问题
    
    ## 输出语言
    - 用户用中文提问 → 用中文回答
    - 用户用英文提问 → 用英文回答
    - 业务术语保持原文 (如 Paid Attendance 不翻译)

system_security:
  name: "安全规则"
  description: "SQL 安全、数据权限等安全相关规则"
  category: "system"
  content: |
    ## SQL 安全规则
    1. 禁止生成 INSERT/UPDATE/DELETE/TRUNCATE/DROP
    2. 禁止使用子查询进行数据修改
    3. 禁止使用存储过程调用
    
    ## 数据权限
    1. 只查询用户有权限访问的表
    2. 不暴露敏感字段 (密码、token、密钥)

# ==================== 工作流 Prompts ====================

workflow_intent_recognition:
  name: "意图识别"
  description: "识别用户问题意图类型"
  category: "workflow"
  stage: "intent_recognition"
  variables: ["user_question", "history_context", "current_date"]
  output_format: "json"
  content: |
    分析用户问题，返回 JSON:
    {
      "intent": "query" | "report" | "followup",
      "confidence": 0-1,
      "reasoning": "判断理由"
    }

workflow_table_selection:
  name: "智能选表"
  description: "根据用户问题选择相关数据表"
  category: "workflow"
  stage: "table_selection"
  variables: ["user_question", "intent_type", "semantic_context", "history_context"]
  output_format: "json"
  content: |
    根据用户问题选择数据表，返回 JSON:
    {
      "selectedTables": [{"tableName": "...", "relevanceScore": 0-1, "reasoning": "..."}],
      "overallReasoning": "..."
    }

workflow_intent_clarification:
  name: "意图澄清"
  description: "展示 AI 对用户问题的理解"
  category: "workflow"
  stage: "intent_clarification"
  variables: ["user_question", "intent_type", "selected_tables", "semantic_context"]
  output_format: "json"
  content: |
    展示你对问题的理解:
    {
      "needsClarification": true/false,
      "clarificationText": "我理解您的问题是：...",
      "fiscalTimeQueries": []
    }

workflow_thinking:
  name: "模型思考"
  description: "分析问题并说明解决思路"
  category: "workflow"
  stage: "thinking"
  variables: ["user_question", "selected_tables", "semantic_context"]
  output_format: "text"
  content: |
    分析用户问题并说明解决思路:
    1. 问题分析
    2. 解决思路
    3. 查询意图判断 (汇总/明细)
    4. SELECT 字段清单

workflow_sql_generation:
  name: "SQL 生成"
  description: "根据澄清后的需求生成 SQL 查询"
  category: "workflow"
  stage: "sql_generation"
  variables: ["original_question", "clarified_requirement", "thinking_result", "semantic_context"]
  output_format: "json"
  content: |
    生成 SQL 查询:
    {
      "sql": "SELECT ...",
      "explanation": "SQL 逻辑说明",
      "estimatedRows": "预估行数"
    }

workflow_chart_recommendation:
  name: "图表推荐"
  description: "推荐合适的图表类型并生成配置"
  category: "workflow"
  stage: "chart_recommendation"
  variables: ["user_question", "query_result", "thinking_result"]
  output_format: "json"
  content: |
    推荐图表类型:
    {
      "recommendedChart": "bar" | "line" | "pie" | "combo" | "table",
      "chartConfig": {...}
    }

workflow_result_description:
  name: "数据结果描述"
  description: "生成商务报告风格的数据摘要"
  category: "workflow"
  stage: "result_description"
  variables: ["user_question", "query_result", "intent_type"]
  output_format: "text"
  content: |
    生成数据摘要:
    - L1 单值：一句话回答
    - L2/L3: 三段式 (Executive Summary + Key Findings + Data Insight)

# ==================== 工具使用指南 ====================

tool_fiscal_calendar:
  name: "财务日历使用指南"
  description: "何时及如何使用财务日历工具"
  category: "tool_guide"
  rules:
    - "用户提到'第 N 周'、'最后一周'时必须调用 fiscal_calendar_tool"
    - "简单相对时间 (上周/本周) 用 TimeResolver 正则处理"
    - "农历节日日期必须查知识库，禁止自行推断"
    - "不要假设春节日期，2025 年=1 月 29 日，2026 年=2 月 17 日"

tool_dictionary_lookup:
  name: "字典查询使用指南"
  description: "业务术语映射规则"
  category: "tool_guide"
  rules:
    - "业务术语 (Paid Attendance) → 查 dictionary"
    - "地理分组 (Domestic/Other China) → 查 dictionary_items"
    - "值不翻译，使用字典定义的原始值"

tool_knowledge_search:
  name: "知识库搜索指南"
  description: "何时查询知识库获取业务规则"
  category: "tool_guide"
  rules:
    - "节假日事件 → 查 knowledge_items (category=holiday_event)"
    - "业务规则 → 查 knowledge_items (category=business_rule)"
    - "表级别知识 → 查 knowledge_items (category=table_knowledge)"

# ==================== 输出格式规范 ====================

format_data_description:
  name: "数据摘要格式"
  description: "数据结果描述的输出格式规范"
  category: "format"
  rules:
    - "L1 单值：一句话回答，包含关键数值"
    - "L2/L3: 三段式 (Executive Summary + Key Findings + Data Insight)"
    - "Three-in-One 格式：[entity] [metric] was [current], [abs_change] / [pct_change] up/down vs. PY"
    - "术语不翻译：Paid Attendance 不翻译为付费到场人数"
    - "禁止主观词：显著、大幅、明显、值得关注"

format_chart_config:
  name: "图表配置格式"
  description: "图表推荐的输出格式规范"
  category: "format"
  rules:
    - "series 必须是数组"
    - "data[].name 是分类标签，data[].value 是数值"
    - "Combo 图：绝对值 type=bar/yAxisIndex=0, 比率 type=line/yAxisIndex=1"
    - "L1 单数字结果：recommendedChart=table, series=[]"

format_sql_generation:
  name: "SQL 生成格式"
  description: "SQL 生成的输出格式和验证规则"
  category: "format"
  rules:
    - "必须包含 LIMIT 子句，LIMIT ≤ 100"
    - "数值格式化：整数 ROUND(x,0), 百分比 ROUND(x,2)"
    - "别名避免 MySQL 保留字"
    - "GROUP BY 表达式必须与 SELECT 非聚合表达式完全一致"
```

#### PromptManager 改进

```python
# src/services/prompt_manager.py

class PromptManager:
    """增强的 Prompt 管理器"""
    
    def __init__(self):
        self.templates = self._load_templates()
        self.tool_guides = self._load_tool_guides()
        self.format_rules = self._load_format_rules()
    
    def render(
        self, 
        template_name: str, 
        variables: Dict[str, Any],
        include_context: Optional[List[str]] = None
    ) -> str:
        """
        渲染 Prompt 模板
        
        Args:
            template_name: 模板名称 (如 workflow_intent_recognition)
            variables: 变量字典
            include_context: 要包含的上下文类型 (system/tool_guide/format)
        
        Returns:
            完整的 Prompt 字符串
        """
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # 构建完整 Prompt
        parts = []
        
        # 1. 系统核心指令 (可选)
        if include_context and "system" in include_context:
            parts.append(self.templates["system_core"]["content"])
            parts.append(self.templates["system_security"]["content"])
        
        # 2. 主模板内容
        content = self._substitute_variables(template["content"], variables)
        parts.append(content)
        
        # 3. 工具使用指南 (可选)
        if include_context and "tool_guide" in include_context:
            relevant_guides = self._get_relevant_tool_guides(template_name)
            for guide in relevant_guides:
                parts.append(f"\n## 工具使用规则\n{guide['rules']}")
        
        # 4. 输出格式规范 (可选)
        if include_context and "format" in include_context:
            relevant_formats = self._get_relevant_format_rules(template_name)
            for rule in relevant_formats:
                parts.append(f"\n## 输出格式\n{rule['rules']}")
        
        return "\n\n".join(parts)
    
    def _get_relevant_tool_guides(self, template_name: str) -> List[Dict]:
        """获取相关工具指南"""
        mapping = {
            "workflow_intent_clarification": ["tool_fiscal_calendar"],
            "workflow_sql_generation": ["tool_dictionary_lookup", "tool_fiscal_calendar"],
            "workflow_result_description": ["tool_dictionary_lookup"]
        }
        guide_names = mapping.get(template_name, [])
        return [self.tool_guides[name] for name in guide_names if name in self.tool_guides]
```

### 实施步骤

1. **Phase 1 (2 天)**: 重构 prompts.yml 结构
2. **Phase 2 (1 天)**: 改进 PromptManager 支持分类加载
3. **Phase 3 (1 天)**: 更新各阶段调用使用新结构

---

## 4. 上下文管理和压缩

### 当前问题

- 历史对话全部堆在 `history_context` 变量中
- 没有压缩策略
- 长对话会导致 prompt 超长

### Claude Code 借鉴方案

```typescript
// src/history.ts - 历史管理
// src/utils/pasteStore.ts - 大内容外部存储

// 关键设计:
// 1. 历史条目 JSONL 格式存储
// 2. 大内容 (>1024 字符) 外部存储，用 hash 引用
// 3. 会话级别隔离
// 4. 元数据提取 (时间范围、筛选条件等)
```

### 优化方案

```python
# src/services/context_manager.py

import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MessageEntry:
    """消息条目"""
    id: str
    session_id: str
    role: str  # "user" | "assistant"
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    tokens: int = 0


class ContextManager:
    """增强的上下文管理器"""
    
    def __init__(self):
        self.summary_threshold = 5  # 超过 5 轮对话开始摘要
        self.max_history_turns = 10  # 最多保留 10 轮原始历史
        self.max_content_length = 2000  # 内容超过此长度使用摘要
        self.metadata_cache: Dict[str, Dict] = {}
    
    async def build_history_context(
        self, 
        session_id: str,
        max_tokens: int = 4000
    ) -> str:
        """
        构建历史对话上下文，带压缩策略
        
        压缩策略:
        1. 短对话 (≤5 轮): 直接拼接
        2. 中等对话 (5-10 轮): 保留原始
        3. 长对话 (>10 轮): 早期对话摘要 + 最近 N 轮
        4. 超长内容 (>2000 字): 内容摘要
        """
        messages = self.load_messages(session_id)
        
        if not messages:
            return ""
        
        # 1. 短对话：直接拼接
        if len(messages) <= self.summary_threshold:
            return self._format_messages(messages)
        
        # 2. 长对话：摘要 + 最近 N 轮
        early_messages = messages[:-self.max_history_turns]
        recent_messages = messages[-self.max_history_turns:]
        
        # 生成早期对话摘要
        summary = await self._summarize_conversation(early_messages)
        
        # 格式化输出
        parts = []
        
        if summary:
            parts.append(f"=== 历史对话摘要 ===\n{summary}")
        
        parts.append(f"\n=== 最近对话 ===\n{self._format_messages(recent_messages)}")
        
        return "\n".join(parts)
    
    def add_user_message(
        self, 
        session_id: str, 
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        添加用户消息
        同时提取关键元数据用于后续检索
        """
        # 提取元数据
        extracted_metadata = self._extract_metadata(content)
        if metadata:
            extracted_metadata.update(metadata)
        
        # 存储消息
        entry = MessageEntry(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=content,
            metadata=extracted_metadata,
            timestamp=datetime.now()
        )
        
        self._store_entry(entry)
        
        # 更新缓存
        self._update_metadata_cache(session_id, extracted_metadata)
        
        return entry.id
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        从消息中提取关键信息
        用于后续检索和摘要生成
        """
        import re
        
        metadata = {
            "time_range": None,
            "filters": [],
            "metrics": [],
            "dimensions": [],
            "has_comparison": False
        }
        
        # 时间范围提取
        time_patterns = [
            (r" (上周 | 本周 | 上月 | 本月 | 上季度 | 本季度)", "relative"),
            (r"(\d{4}) 年 (\d{1,2}) 月", "year_month"),
            (r"(\d{4}-\d{2}-\d{2})", "date"),
            (r"FW(\d+)", "fiscal_week"),
            (r"FM(\d+)", "fiscal_month"),
        ]
        
        for pattern, time_type in time_patterns:
            match = re.search(pattern, content)
            if match:
                metadata["time_range"] = {
                    "type": time_type,
                    "raw": match.group(0)
                }
                break
        
        # 筛选条件提取
        filter_keywords = ["渠道", "地区", "品类", "票型", "paid", "niche", "comp"]
        for keyword in filter_keywords:
            if keyword.lower() in content.lower():
                metadata["filters"].append(keyword)
        
        # 指标提取
        metric_keywords = ["attendance", "销售额", "订单", "数量", "金额", "占比", "增长率"]
        for keyword in metric_keywords:
            if keyword.lower() in content.lower():
                metadata["metrics"].append(keyword)
        
        # 维度提取
        dimension_keywords = ["各渠道", "各地区", "各品类", "分布", "趋势", "对比"]
        for keyword in dimension_keywords:
            if keyword.lower() in content.lower():
                metadata["dimensions"].append(keyword)
        
        # 对比分析判断
        comparison_keywords = ["同比", "环比", "对比", "vs", "yoy", "mom", "增长", "下降"]
        metadata["has_comparison"] = any(
            kw.lower() in content.lower() for kw in comparison_keywords
        )
        
        return metadata
    
    async def _summarize_conversation(self, messages: List[MessageEntry]) -> str:
        """
        使用模型摘要早期对话
        保留关键信息：时间范围、筛选条件、查询主题
        """
        from src.services.ai_model_service import get_ai_service
        
        # 构建摘要输入
        conversation_text = self._format_messages(messages, max_content_length=500)
        
        prompt = f"""
请摘要以下对话历史，保留关键信息:

{conversation_text}

摘要要求:
1. 时间范围 (如"上周"、"2026 年 1 月")
2. 筛选条件 (如"niche 渠道"、"付费用户")
3. 查询主题 (如"Attendance 分布"、"销售趋势")
4. 数据结果的关键数值 (如有)

用中文摘要，限制在 200 字以内。
"""
        
        ai_service = get_ai_service()
        response = await ai_service.call_model(
            prompt=prompt,
            stage="summary"
        )
        
        return response["content"]
    
    def get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话的累积元数据
        用于快速检索而无需加载完整历史
        """
        if session_id in self.metadata_cache:
            return self.metadata_cache[session_id]
        
        # 从数据库聚合元数据
        metadata = self._aggregate_session_metadata(session_id)
        self.metadata_cache[session_id] = metadata
        return metadata
    
    def _update_metadata_cache(self, session_id: str, new_metadata: Dict):
        """更新会话元数据缓存"""
        if session_id not in self.metadata_cache:
            self.metadata_cache[session_id] = {
                "time_ranges": [],
                "all_filters": [],
                "all_metrics": [],
                "last_query_topic": None
            }
        
        cached = self.metadata_cache[session_id]
        
        if new_metadata.get("time_range"):
            cached["time_ranges"].append(new_metadata["time_range"])
        
        cached["all_filters"].extend(new_metadata.get("filters", []))
        cached["all_metrics"].extend(new_metadata.get("metrics", []))
        
        # 更新最后查询主题
        if new_metadata.get("metrics"):
            cached["last_query_topic"] = new_metadata["metrics"][0]
```

### 实施步骤

1. **Phase 1 (2 天)**: 创建 ContextManager 新类
2. **Phase 2 (1 天)**: 实现元数据提取
3. **Phase 3 (1 天)**: 实现摘要生成
4. **Phase 4 (1 天)**: 集成到 chat_orchestrator

---

## 5. Harness 框架评估

### Harness 框架的价值（从 Claude Code 看）

| 组件 | Claude Code 实现 | 价值 |
|------|-----------------|------|
| 技能管理 | `src/skills/bundled/` + `loadSkillsDirs.ts` | 结构化技能注册 |
| 工具系统 | `src/tools/BashTool/` etc. | 统一 Tool 接口 |
| 权限控制 | `src/types/permissions.ts` | 细粒度权限 |
| 状态管理 | `src/state/AppState.ts` | 统一状态容器 |
| 会话历史 | `src/history.ts` + JSONL | 高效历史存储 |

### 你的项目评估

| 维度 | ChatBI 现状 | Harness 价值 | 建议 |
|------|-------------|--------------|------|
| 技能管理 | prompts.yml 集中配置 | 结构化技能目录 | ✅ 值得借鉴 |
| 工具系统 | API 路由分散 | 统一 Tool 接口 | ✅ 值得借鉴 |
| 权限控制 | 无显式权限 | 细粒度权限 | ⚠️ 可选 |
| 状态管理 | context.metadata | AppState 模式 | ✅ 值得借鉴 |
| 会话历史 | 数据库 + ContextManager | JSONL+ 摘要 | ✅ 值得借鉴 |

### 建议方案

**不引入完整 Harness，但借鉴核心设计:**

```python
# src/harness/__init__.py
"""
ChatBI Harness Framework - 简化版
借鉴 Claude Code 的核心设计
"""

from .skill import Skill
from .tool import Tool
from .agent import Agent
from .state import AppState

__all__ = ["Skill", "Tool", "Agent", "AppState"]
```

```python
# src/harness/skill.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class Skill(ABC):
    """
    技能基类
    用于封装需要领域知识的复杂任务
    """
    
    name: str
    description: str
    version: str = "1.0"
    variables: List[str] = []
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技能
        Args:
            context: 包含 variables 中定义的变量
        Returns:
            执行结果
        """
        pass
    
    def validate(self, context: Dict[str, Any]) -> bool:
        """验证输入"""
        for var in self.variables:
            if var not in context:
                return False
        return True
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取技能元数据"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "variables": self.variables
        }
```

```python
# src/harness/tool.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class Tool(ABC):
    """
    工具基类
    用于封装确定性的函数调用
    """
    
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
    
    @abstractmethod
    async def invoke(self, **kwargs) -> Any:
        """
        调用工具
        Args:
            **kwargs: 工具参数
        Returns:
            调用结果
        """
        pass
    
    def validate_input(self, kwargs: Dict[str, Any]) -> bool:
        """验证输入参数"""
        # 简化版验证，实际可使用 jsonschema
        return True
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取工具元数据"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }
```

```python
# src/harness/state.py

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

@dataclass
class TokenStats:
    """Token 使用统计"""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0

@dataclass
class AppState:
    """
    应用状态容器
    类似 Claude Code 的 AppState
    """
    # 当前会话
    current_session: Optional[str] = None
    
    # 数据选择
    selected_tables: List[str] = field(default_factory=list)
    selected_data_source: Optional[str] = None
    
    # 语义上下文
    semantic_context: Dict[str, Any] = field(default_factory=dict)
    
    # Token 统计
    token_usage: TokenStats = field(default_factory=TokenStats)
    
    # 执行状态
    current_stage: str = ""
    error_state: Optional[Dict[str, Any]] = None
    
    # 用户偏好
    response_language: str = "zh"
    
    def update(self, **kwargs):
        """更新状态"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "current_session": self.current_session,
            "selected_tables": self.selected_tables,
            "semantic_context": self.semantic_context,
            "token_usage": {
                "total_tokens": self.token_usage.total_tokens,
                "estimated_cost": self.token_usage.estimated_cost
            },
            "current_stage": self.current_stage,
            "response_language": self.response_language
        }
```

### 实施建议

1. **创建简化版 Harness** (`src/harness/`)
2. **逐步迁移现有代码到 Harness 接口**
3. **不追求完整框架，只取核心设计**

---

## 6. Skill 和 Tool 化分析

### 功能分类

| 功能 | 当前形式 | 建议 | 理由 |
|------|----------|------|------|
| 意图识别 | Prompt → API | **Skill** | 需要领域知识判断 |
| 智能选表 | Prompt → API | **Skill** | 依赖业务理解 |
| SQL 生成 | Prompt → API | **Skill** | 复杂推理任务 |
| 数据分析 | Prompt → API | **Skill** | 需要业务洞察 |
| 结果描述 | Prompt → API | **Skill** | 需要业务洞察 |
| 图表推荐 | Prompt → API | **Skill** | 需要业务理解 |
| 财务日历查询 | Service | **Tool** | 确定性数据库查询 |
| 字典查询 | Service | **Tool** | 确定性查找 |
| 表关联查询 | Service | **Tool** | 确定性数据结构 |
| Token 统计 | Service | **Tool** | 数据检索 |
| 知识库检索 | Service | **Tool** | 向量搜索 + 检索 |

### Skill 实现示例

```python
# src/skills/sql_generation_skill.py

from harness import Skill
from typing import Dict, Any

class SQLGenerationSkill(Skill):
    """
    SQL 生成 Skill
    根据用户问题、表结构和语义上下文生成 SQL
    """
    
    name = "sql_generation"
    description = "根据用户问题和表结构生成 SQL 查询"
    version = "3.0"
    variables = [
        "original_question",
        "clarified_requirement", 
        "thinking_result",
        "semantic_context",
        "db_type"
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        from src.services.prompt_manager import get_prompt_manager
        from src.services.ai_model_service import get_ai_service
        from src.services.sql_security_validator import SQLSecurityService
        
        self.prompt_manager = get_prompt_manager()
        self.ai_service = get_ai_service()
        self.sql_validator = SQLSecurityService()
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 SQL 生成
        
        Args:
            context: 包含 variables 中定义的变量
        
        Returns:
            {
                "sql": str,
                "explanation": str,
                "estimatedRows": str,
                "validation": dict,
                "success": bool,
                "error": Optional[str]
            }
        """
        # 1. 验证上下文
        if not self.validate(context):
            return {
                "success": False,
                "error": "Missing required context variables"
            }
        
        # 2. 构建 prompt
        prompt = self.prompt_manager.render(
            template_name="workflow_sql_generation",
            variables=context,
            include_context=["system", "tool_guide", "format"]
        )
        
        # 3. 调用模型
        import asyncio
        response = asyncio.run(self.ai_service.call_model(
            prompt=prompt,
            stage="sql_generation"
        ))
        
        # 4. 提取 SQL
        sql = self._extract_sql(response["content"])
        
        if not sql:
            return {
                "success": False,
                "error": "Failed to extract SQL from response"
            }
        
        # 5. 验证 SQL
        validation = self.sql_validator.validate(sql)
        
        return {
            "success": validation.get("valid", False),
            "sql": sql,
            "explanation": self._extract_explanation(response["content"]),
            "estimatedRows": self._extract_estimated_rows(response["content"]),
            "validation": validation,
            "tokens_used": response.get("tokens_used", 0)
        }
    
    def _extract_sql(self, content: str) -> Optional[str]:
        """从响应中提取 SQL"""
        import re
        patterns = [
            r'```sql\s*(.*?)\s*```',
            r'```\s*(SELECT.*?)\s*```',
            r'(SELECT\s+.*?(?:;|$))'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                sql = match.group(1).strip()
                sql = re.sub(r'\s+', ' ', sql)
                return sql.rstrip(';')
        
        return None
```

### Tool 实现示例

```python
# src/tools/fiscal_calendar_tool.py

from harness import Tool
from typing import Dict, Any, Optional

class FiscalCalendarTool(Tool):
    """
    财务日历查询 Tool
    查询财务日历，将自然日期转换为财周
    """
    
    name = "fiscal_calendar"
    description = "查询财务日历，将自然日期/节假日转换为财周日期范围"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "日期查询，如'2026 年 1 月第二周'、'春节'"
            },
            "reference_date": {
                "type": "string",
                "description": "参考日期 (用于相对时间计算)"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        from src.services.time_resolver import TimeResolver
        self.time_resolver = TimeResolver()
    
    async def invoke(self, query: str, reference_date: Optional[str] = None) -> Dict[str, Any]:
        """
        查询财务日历
        
        Returns:
            {
                "fw_label": "FW22",
                "start_date": "2026-01-05",
                "end_date": "2026-01-11",
                "fy_n": 2026,
                "fm_n": 1,
                "fw_n": 22
            }
        """
        result = await self.time_resolver.resolve_fiscal_query(query, reference_date)
        
        if not result:
            return {
                "success": False,
                "error": f"未找到匹配的财务日历：{query}"
            }
        
        return {
            "success": True,
            "fw_label": result.fw_label,
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "fy_n": result.fy_n,
            "fm_n": result.fm_n,
            "fw_n": result.fw_n
        }
```

### 目录结构建议

```
backend/src/
├── harness/                    # 简化版 Harness 框架
│   ├── __init__.py
│   ├── skill.py
│   ├── tool.py
│   ├── agent.py
│   └── state.py
├── skills/                     # 技能目录
│   ├── __init__.py
│   ├── intent_recognition.py
│   ├── table_selection.py
│   ├── sql_generation.py
│   ├── data_analysis.py
│   ├── result_description.py
│   └── chart_recommendation.py
├── tools/                      # 工具目录
│   ├── __init__.py
│   ├── fiscal_calendar_tool.py
│   ├── dictionary_lookup_tool.py
│   ├── table_relation_tool.py
│   ├── knowledge_search_tool.py
│   └── token_stats_tool.py
└── agents/                     # Agent 目录
    ├── __init__.py
    ├── base_agent.py
    ├── intent_agent.py
    ├── table_selector_agent.py
    ├── orchestrator_agent.py
    └── ...
```

---

## 实施优先级

| 优先级 | 优化方向 | 预计工作量 | 收益 | 依赖 |
|--------|----------|------------|------|------|
| **P0** | Prompt 结构重组 | 2-3 天 | 降低维护成本 | 无 |
| **P0** | 财务日历 Tool 化 | 2-3 天 | 解决日期幻觉 | 无 |
| **P1** | Harness 框架基础 | 2-3 天 | 代码组织清晰 | 无 |
| **P1** | Skill/Tool分类实现 | 3-5 天 | 可测试性提升 | Harness |
| **P1** | 上下文压缩 | 2-3 天 | 支持更长对话 | 无 |
| **P2** | Agent 架构改造 | 1-2 周 | 并行/错误隔离 | Skill |

---

## 参考资源

### Claude Code 源码
- Tool 系统：`/Users/zhanh391/PC/Project/claude/claude-code-rev-main/src/tools/`
- Skill 系统：`/Users/zhanh391/PC/Project/claude/claude-code-rev-main/src/skills/`
- 历史管理：`/Users/zhanh391/PC/Project/claude/claude-code-rev-main/src/history.ts`
- 上下文管理：`/Users/zhanh391/PC/Project/claude/claude-code-rev-main/src/context.ts`
- 状态管理：`/Users/zhanh391/PC/Project/claude/claude-code-rev-main/src/state/`

### 相关文档
- [Claude Code Repository Guidelines](/Users/zhanh391/PC/Project/claude/claude-code-rev-main/README.md)
- [Claude Code Restored Source](/Users/zhanh391/PC/Project/claude/claude-code-rev-main/AGENTS.md)
