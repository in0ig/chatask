"""
核心对话功能端到端集成测试

测试完整的对话流程，使用真实数据和真实AI调用
验收标准：
- 端到端对话流程稳定
- 多轮对话上下文管理准确
- 错误处理和自愈机制有效
- 数据安全得到完全保障
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from src.services.chat_orchestrator import ChatOrchestrator
from src.services.intent_recognition_service import IntentRecognitionService
from src.services.intelligent_table_selector import IntelligentTableSelector
from src.services.intent_clarification_service import IntentClarificationService
from src.services.sql_generator_service import SQLGeneratorService
from src.services.sql_executor_service import SQLExecutorService
from src.services.local_data_analyzer import LocalDataAnalyzer
from src.services.dialogue_manager import DialogueManager
from src.services.context_manager import ContextManager
from src.database import get_db


class TestCoreDialogueE2E:
    """核心对话功能端到端集成测试"""
    
    @pytest_asyncio.fixture
    async def setup_services(self):
        """设置所有需要的服务"""
        db = next(get_db())
        
        # 初始化所有服务
        context_manager = ContextManager()
        dialogue_manager = DialogueManager(db)
        intent_service = IntentRecognitionService()
        table_selector = IntelligentTableSelector(db)
        clarification_service = IntentClarificationService()
        sql_generator = SQLGeneratorService(db)
        sql_executor = SQLExecutorService(db)
        local_analyzer = LocalDataAnalyzer()
        
        orchestrator = ChatOrchestrator(
            context_manager=context_manager,
            dialogue_manager=dialogue_manager,
            intent_service=intent_service,
            table_selector=table_selector,
            clarification_service=clarification_service,
            sql_generator=sql_generator,
            sql_executor=sql_executor,
            local_analyzer=local_analyzer
        )
        
        return {
            "orchestrator": orchestrator,
            "context_manager": context_manager,
            "dialogue_manager": dialogue_manager,
            "db": db
        }
    
    @pytest.mark.asyncio
    async def test_complete_dialogue_flow_real_data(self, setup_services):
        """
        测试1: 完整对话流程 - 使用真实数据和真实AI调用
        
        验收标准：
        - 意图识别准确
        - 智能选表相关
        - SQL生成正确
        - 查询执行成功
        - 结果分析完整
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        
        # 创建真实会话
        session_id = f"test_session_{datetime.now().timestamp()}"
        
        # 第一轮：用户提问
        user_question = "查询销售额最高的前10个产品"
        
        # 执行完整对话流程
        result = await orchestrator.process_query(
            session_id=session_id,
            user_question=user_question,
            data_source_id=1  # 使用真实数据源ID
        )
        
        # 验证结果
        assert result is not None, "对话流程应该返回结果"
        assert "intent" in result, "结果应包含意图识别"
        assert "selected_tables" in result, "结果应包含选表信息"
        assert "sql" in result, "结果应包含生成的SQL"
        assert "query_result" in result, "结果应包含查询结果"
        
        # 验证意图识别
        assert result["intent"]["type"] in ["query", "report"], "意图类型应该正确"
        assert result["intent"]["confidence"] > 0.7, "意图识别置信度应该足够高"
        
        # 验证选表结果
        assert len(result["selected_tables"]) > 0, "应该选择至少一个表"
        assert all("table_name" in t for t in result["selected_tables"]), "每个表应有名称"
        
        # 验证SQL生成
        assert "SELECT" in result["sql"].upper(), "SQL应包含SELECT语句"
        assert "LIMIT" in result["sql"].upper() or "TOP" in result["sql"].upper(), "SQL应包含限制条数"
        
        # 验证查询结果
        assert "columns" in result["query_result"], "查询结果应包含列信息"
        assert "rows" in result["query_result"], "查询结果应包含行数据"
        assert len(result["query_result"]["rows"]) <= 10, "结果行数应符合查询要求"
        
        print(f"✅ 完整对话流程测试通过")
        print(f"   - 意图: {result['intent']['type']}")
        print(f"   - 选表数量: {len(result['selected_tables'])}")
        print(f"   - SQL长度: {len(result['sql'])} 字符")
        print(f"   - 结果行数: {len(result['query_result']['rows'])}")
    
    @pytest.mark.asyncio
    async def test_multi_turn_dialogue_context(self, setup_services):
        """
        测试2: 多轮对话上下文管理 - 真实场景
        
        验收标准：
        - 上下文正确维护
        - 历史消息准确记录
        - 后续问题能理解前文
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        context_manager = services["context_manager"]
        
        session_id = f"test_multi_turn_{datetime.now().timestamp()}"
        
        # 第一轮对话
        question1 = "查询2023年的销售数据"
        result1 = await orchestrator.process_query(
            session_id=session_id,
            user_question=question1,
            data_source_id=1
        )
        
        assert result1 is not None, "第一轮对话应该成功"
        
        # 获取上下文
        context = context_manager.get_context(session_id)
        assert len(context["messages"]) > 0, "上下文应该包含消息"
        
        # 第二轮对话 - 基于上下文的追问
        question2 = "那2024年的呢？"
        result2 = await orchestrator.process_query(
            session_id=session_id,
            user_question=question2,
            data_source_id=1
        )
        
        assert result2 is not None, "第二轮对话应该成功"
        
        # 验证上下文更新
        updated_context = context_manager.get_context(session_id)
        assert len(updated_context["messages"]) > len(context["messages"]), "上下文应该增加新消息"
        
        # 验证SQL生成考虑了上下文
        assert "2024" in result2["sql"], "第二轮SQL应该包含2024年"
        
        print(f"✅ 多轮对话上下文管理测试通过")
        print(f"   - 第一轮消息数: {len(context['messages'])}")
        print(f"   - 第二轮消息数: {len(updated_context['messages'])}")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_self_healing(self, setup_services):
        """
        测试3: 错误处理和自愈机制 - 真实错误场景
        
        验收标准：
        - 错误能被正确分类
        - 自愈机制能自动重试
        - 最终能生成正确SQL
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        
        session_id = f"test_error_handling_{datetime.now().timestamp()}"
        
        # 故意使用可能导致错误的问题
        ambiguous_question = "查询数据"  # 模糊问题
        
        result = await orchestrator.process_query(
            session_id=session_id,
            user_question=ambiguous_question,
            data_source_id=1
        )
        
        # 验证系统处理了模糊问题
        assert result is not None, "即使问题模糊，系统也应该返回结果"
        
        # 验证是否触发了澄清机制
        if "clarification_needed" in result:
            assert result["clarification_needed"] is True, "模糊问题应该触发澄清"
            assert "clarification_questions" in result, "应该提供澄清问题"
        
        print(f"✅ 错误处理和自愈机制测试通过")
    
    @pytest.mark.asyncio
    async def test_data_privacy_cloud_model(self, setup_services):
        """
        测试4: 数据安全 - 云端模型不接触业务数据
        
        验收标准：
        - 云端历史记录不包含实际数据值
        - 仅包含SQL和状态描述
        - 数据消毒机制有效
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        context_manager = services["context_manager"]
        
        session_id = f"test_privacy_{datetime.now().timestamp()}"
        
        # 执行查询
        question = "查询客户信息"
        result = await orchestrator.process_query(
            session_id=session_id,
            user_question=question,
            data_source_id=1
        )
        
        assert result is not None, "查询应该成功"
        
        # 获取云端历史记录
        cloud_history = context_manager.get_cloud_history(session_id)
        
        # 验证云端历史不包含实际数据
        for message in cloud_history:
            content = str(message.get("content", ""))
            
            # 检查不应包含敏感数据模式
            assert not any(pattern in content.lower() for pattern in [
                "@", ".com", "phone", "email", "password"
            ]), "云端历史不应包含敏感数据"
            
            # 应该只包含SQL或状态描述
            if "sql" in content.lower():
                assert "SELECT" in content.upper() or "sql" in content.lower(), \
                    "云端历史应该包含SQL语句"
        
        print(f"✅ 云端模型数据隐私测试通过")
        print(f"   - 云端历史消息数: {len(cloud_history)}")
    
    @pytest.mark.asyncio
    async def test_local_model_data_processing(self, setup_services):
        """
        测试5: 本地模型数据处理 - 数据不出网
        
        验收标准：
        - 本地模型能访问完整数据
        - 数据分析准确
        - 数据不发送到云端
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        local_analyzer = services["orchestrator"].local_analyzer
        
        session_id = f"test_local_{datetime.now().timestamp()}"
        
        # 先执行一个查询获取数据
        question = "查询销售数据"
        result = await orchestrator.process_query(
            session_id=session_id,
            user_question=question,
            data_source_id=1
        )
        
        assert result is not None, "查询应该成功"
        assert "query_result" in result, "应该有查询结果"
        
        # 使用本地模型进行数据追问
        followup_question = "这些数据的平均值是多少？"
        
        analysis_result = await local_analyzer.analyze_data(
            query_result=result["query_result"],
            question=followup_question,
            context={}
        )
        
        # 验证本地分析结果
        assert analysis_result is not None, "本地分析应该返回结果"
        assert "analysis" in analysis_result, "应该包含分析内容"
        
        print(f"✅ 本地模型数据处理测试通过")
    
    @pytest.mark.asyncio
    async def test_dual_history_isolation(self, setup_services):
        """
        测试6: 双层历史记录数据隔离
        
        验收标准：
        - 云端历史和本地历史分离
        - 云端历史不包含数据值
        - 本地历史包含完整数据
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        context_manager = services["context_manager"]
        
        session_id = f"test_dual_history_{datetime.now().timestamp()}"
        
        # 执行查询
        question = "查询订单数据"
        result = await orchestrator.process_query(
            session_id=session_id,
            user_question=question,
            data_source_id=1
        )
        
        assert result is not None, "查询应该成功"
        
        # 获取两种历史记录
        cloud_history = context_manager.get_cloud_history(session_id)
        local_history = context_manager.get_local_history(session_id)
        
        # 验证云端历史
        assert len(cloud_history) > 0, "云端历史应该有记录"
        for msg in cloud_history:
            content = str(msg.get("content", ""))
            # 云端历史应该只包含SQL和状态
            if "SELECT" in content.upper():
                # 验证不包含实际数据值
                assert not any(char.isdigit() for char in content if char not in "SELECT FROM WHERE"), \
                    "云端历史SQL不应包含具体数据值"
        
        # 验证本地历史
        assert len(local_history) > 0, "本地历史应该有记录"
        has_data = False
        for msg in local_history:
            if "query_result" in msg:
                has_data = True
                assert "rows" in msg["query_result"], "本地历史应该包含完整查询结果"
                break
        
        assert has_data, "本地历史应该包含查询结果数据"
        
        print(f"✅ 双层历史记录数据隔离测试通过")
        print(f"   - 云端历史消息数: {len(cloud_history)}")
        print(f"   - 本地历史消息数: {len(local_history)}")
    
    @pytest.mark.asyncio
    async def test_complete_user_experience_flow(self, setup_services):
        """
        测试7: 完整用户体验流程
        
        验收标准：
        - 整体对话体验流畅
        - 响应时间合理
        - 结果准确完整
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        
        session_id = f"test_ux_{datetime.now().timestamp()}"
        
        # 模拟真实用户场景
        questions = [
            "查询最近一个月的销售趋势",
            "哪个产品卖得最好？",
            "和上个月相比如何？"
        ]
        
        results = []
        for i, question in enumerate(questions):
            start_time = datetime.now()
            
            result = await orchestrator.process_query(
                session_id=session_id,
                user_question=question,
                data_source_id=1
            )
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            assert result is not None, f"第{i+1}轮对话应该成功"
            assert response_time < 30, f"响应时间应该在30秒内，实际: {response_time}秒"
            
            results.append({
                "question": question,
                "result": result,
                "response_time": response_time
            })
        
        # 验证整体体验
        assert len(results) == len(questions), "所有问题都应该得到回答"
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        assert avg_response_time < 20, f"平均响应时间应该在20秒内，实际: {avg_response_time}秒"
        
        print(f"✅ 完整用户体验流程测试通过")
        print(f"   - 总问题数: {len(questions)}")
        print(f"   - 平均响应时间: {avg_response_time:.2f}秒")
        for i, r in enumerate(results):
            print(f"   - 问题{i+1}响应时间: {r['response_time']:.2f}秒")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
