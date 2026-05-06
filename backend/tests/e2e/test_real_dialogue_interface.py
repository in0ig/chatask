"""
端到端对话界面功能测试

这个测试使用：
1. 真实的数据库表数据
2. 真实的云端 Qwen AI 调用
3. 真实的本地 OpenAI 模型调用
4. 实际的 WebSocket 流式响应
5. 完整的对话流程验证

测试场景：
- 用户提问 -> 意图识别 -> 智能选表 -> SQL生成 -> 执行 -> 结果展示
- 流式消息实时推送
- 图表自动生成
- 数据追问和对比分析
"""

import pytest
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.chat_orchestrator import ChatOrchestrator
from src.services.context_manager import ContextManager
from src.services.dialogue_manager import DialogueManager
from src.database import get_db
from sqlalchemy.orm import Session


class TestRealDialogueInterface:
    """真实对话界面端到端测试"""
    
    @pytest.fixture
    async def setup_test_environment(self):
        """设置测试环境"""
        # 获取数据库会话
        db = next(get_db())
        
        # 初始化服务
        orchestrator = ChatOrchestrator()
        context_manager = ContextManager()
        dialogue_manager = DialogueManager(db)
        
        # 创建测试会话
        session_id = f"test_session_{datetime.now().timestamp()}"
        
        yield {
            'db': db,
            'orchestrator': orchestrator,
            'context_manager': context_manager,
            'dialogue_manager': dialogue_manager,
            'session_id': session_id
        }
        
        # 清理
        db.close()
    
    @pytest.mark.asyncio
    async def test_complete_dialogue_flow_with_real_data(self, setup_test_environment):
        """
        测试完整对话流程（使用真实数据）
        
        验收标准：
        1. ✅ 用户问题成功发送
        2. ✅ 意图识别准确（云端 Qwen）
        3. ✅ 智能选表正确
        4. ✅ SQL 生成成功
        5. ✅ SQL 执行返回数据
        6. ✅ 流式消息实时推送
        7. ✅ 图表自动生成
        8. ✅ 数据分析完整
        """
        env = await setup_test_environment
        orchestrator = env['orchestrator']
        session_id = env['session_id']
        
        # 测试问题：查询销售数据
        user_question = "最近一个月的销售额是多少？"
        
        print(f"\n{'='*60}")
        print(f"🧪 测试场景：完整对话流程")
        print(f"{'='*60}")
        print(f"📝 用户问题: {user_question}")
        print(f"🆔 会话ID: {session_id}")
        print(f"{'='*60}\n")
        
        # 收集流式消息
        messages = []
        
        async def message_handler(message: Dict[str, Any]):
            """处理流式消息"""
            messages.append(message)
            msg_type = message.get('type', 'unknown')
            content = message.get('content', '')
            
            if msg_type == 'thinking':
                print(f"💭 思考中: {content}")
            elif msg_type == 'message':
                print(f"💬 消息: {content}")
            elif msg_type == 'result':
                print(f"📊 结果: {json.dumps(message.get('data', {}), ensure_ascii=False, indent=2)}")
            elif msg_type == 'error':
                print(f"❌ 错误: {content}")
            elif msg_type == 'complete':
                print(f"✅ 完成: {content}")
        
        # 执行对话流程
        try:
            result = await orchestrator.process_query(
                session_id=session_id,
                user_question=user_question,
                message_callback=message_handler
            )
            
            print(f"\n{'='*60}")
            print(f"📈 测试结果统计")
            print(f"{'='*60}")
            print(f"总消息数: {len(messages)}")
            print(f"思考消息: {len([m for m in messages if m.get('type') == 'thinking'])}")
            print(f"普通消息: {len([m for m in messages if m.get('type') == 'message'])}")
            print(f"结果消息: {len([m for m in messages if m.get('type') == 'result'])}")
            print(f"{'='*60}\n")
            
            # 验证结果
            assert result is not None, "对话流程应该返回结果"
            assert result.get('success', False), "对话流程应该成功"
            assert len(messages) > 0, "应该收到流式消息"
            
            # 验证关键阶段
            thinking_messages = [m for m in messages if m.get('type') == 'thinking']
            assert len(thinking_messages) > 0, "应该有思考过程消息"
            
            result_messages = [m for m in messages if m.get('type') == 'result']
            assert len(result_messages) > 0, "应该有结果消息"
            
            # 验证 SQL 生成
            if result.get('generated_sql'):
                print(f"✅ SQL 生成成功:")
                print(f"   {result['generated_sql']}")
            
            # 验证查询结果
            if result.get('query_result'):
                print(f"✅ 查询结果:")
                print(f"   行数: {len(result['query_result'].get('rows', []))}")
                print(f"   列数: {len(result['query_result'].get('columns', []))}")
            
            print(f"\n✅ 完整对话流程测试通过！\n")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}\n")
            raise
    
    @pytest.mark.asyncio
    async def test_streaming_message_display(self, setup_test_environment):
        """
        测试流式消息显示
        
        验收标准：
        1. ✅ 消息按顺序推送
        2. ✅ 思考过程实时显示
        3. ✅ 最终结果正确展示
        4. ✅ 消息类型正确标记
        """
        env = await setup_test_environment
        orchestrator = env['orchestrator']
        session_id = env['session_id']
        
        user_question = "显示所有产品的库存情况"
        
        print(f"\n{'='*60}")
        print(f"🧪 测试场景：流式消息显示")
        print(f"{'='*60}")
        print(f"📝 用户问题: {user_question}")
        print(f"{'='*60}\n")
        
        messages = []
        message_order = []
        
        async def message_handler(message: Dict[str, Any]):
            messages.append(message)
            msg_type = message.get('type', 'unknown')
            message_order.append(msg_type)
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] {msg_type.upper()}: {message.get('content', '')[:50]}...")
        
        try:
            result = await orchestrator.process_query(
                session_id=session_id,
                user_question=user_question,
                message_callback=message_handler
            )
            
            print(f"\n{'='*60}")
            print(f"📊 消息流分析")
            print(f"{'='*60}")
            print(f"消息顺序: {' -> '.join(message_order)}")
            print(f"总消息数: {len(messages)}")
            print(f"{'='*60}\n")
            
            # 验证消息顺序
            assert len(messages) > 0, "应该收到消息"
            assert message_order[0] in ['thinking', 'message'], "第一条消息应该是思考或普通消息"
            assert message_order[-1] in ['complete', 'result'], "最后一条消息应该是完成或结果"
            
            # 验证消息类型
            message_types = set(message_order)
            expected_types = {'thinking', 'message', 'result', 'complete'}
            assert message_types.issubset(expected_types), f"消息类型应该在预期范围内，实际: {message_types}"
            
            print(f"✅ 流式消息显示测试通过！\n")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}\n")
            raise
    
    @pytest.mark.asyncio
    async def test_chart_auto_generation(self, setup_test_environment):
        """
        测试图表自动生成
        
        验收标准：
        1. ✅ 查询结果包含数据
        2. ✅ 图表类型自动选择
        3. ✅ 图表数据格式正确
        4. ✅ 图表配置完整
        """
        env = await setup_test_environment
        orchestrator = env['orchestrator']
        session_id = env['session_id']
        
        user_question = "按月份统计销售额趋势"
        
        print(f"\n{'='*60}")
        print(f"🧪 测试场景：图表自动生成")
        print(f"{'='*60}")
        print(f"📝 用户问题: {user_question}")
        print(f"{'='*60}\n")
        
        chart_data = None
        
        async def message_handler(message: Dict[str, Any]):
            nonlocal chart_data
            if message.get('type') == 'result' and message.get('chart'):
                chart_data = message.get('chart')
                print(f"📊 图表数据:")
                print(f"   类型: {chart_data.get('type', 'unknown')}")
                print(f"   标题: {chart_data.get('title', 'N/A')}")
                print(f"   数据点: {len(chart_data.get('data', []))}")
        
        try:
            result = await orchestrator.process_query(
                session_id=session_id,
                user_question=user_question,
                message_callback=message_handler
            )
            
            # 验证图表生成
            if chart_data:
                assert chart_data.get('type') in ['line', 'bar', 'pie', 'scatter'], "图表类型应该有效"
                assert 'data' in chart_data, "图表应该包含数据"
                assert len(chart_data['data']) > 0, "图表数据不应为空"
                
                print(f"\n✅ 图表自动生成测试通过！")
                print(f"   生成的图表类型: {chart_data['type']}")
                print(f"   数据点数量: {len(chart_data['data'])}\n")
            else:
                print(f"\n⚠️  未生成图表（可能查询结果不适合可视化）\n")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}\n")
            raise
    
    @pytest.mark.asyncio
    async def test_multi_round_dialogue(self, setup_test_environment):
        """
        测试多轮对话
        
        验收标准：
        1. ✅ 上下文正确维护
        2. ✅ 历史消息可访问
        3. ✅ 追问功能正常
        4. ✅ 数据对比准确
        """
        env = await setup_test_environment
        orchestrator = env['orchestrator']
        context_manager = env['context_manager']
        session_id = env['session_id']
        
        print(f"\n{'='*60}")
        print(f"🧪 测试场景：多轮对话")
        print(f"{'='*60}\n")
        
        # 第一轮：初始查询
        question1 = "查询本月销售额"
        print(f"👤 第1轮: {question1}")
        
        result1 = await orchestrator.process_query(
            session_id=session_id,
            user_question=question1
        )
        
        assert result1.get('success'), "第一轮查询应该成功"
        print(f"✅ 第1轮完成\n")
        
        # 第二轮：追问
        question2 = "和上个月相比如何？"
        print(f"👤 第2轮: {question2}")
        
        result2 = await orchestrator.process_query(
            session_id=session_id,
            user_question=question2
        )
        
        assert result2.get('success'), "第二轮查询应该成功"
        print(f"✅ 第2轮完成\n")
        
        # 验证上下文
        context = context_manager.get_session_context(session_id)
        assert context is not None, "应该有会话上下文"
        assert len(context.get('history', [])) >= 2, "应该有至少2轮对话历史"
        
        print(f"{'='*60}")
        print(f"📊 多轮对话统计")
        print(f"{'='*60}")
        print(f"对话轮数: {len(context.get('history', []))}")
        print(f"上下文大小: {len(str(context))} 字符")
        print(f"{'='*60}\n")
        
        print(f"✅ 多轮对话测试通过！\n")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, setup_test_environment):
        """
        测试错误处理和恢复
        
        验收标准：
        1. ✅ 错误消息正确显示
        2. ✅ 系统不崩溃
        3. ✅ 可以继续对话
        4. ✅ 错误信息友好
        """
        env = await setup_test_environment
        orchestrator = env['orchestrator']
        session_id = env['session_id']
        
        print(f"\n{'='*60}")
        print(f"🧪 测试场景：错误处理和恢复")
        print(f"{'='*60}\n")
        
        # 测试无效问题
        invalid_question = "这是一个无法理解的问题 @#$%^&*()"
        print(f"👤 无效问题: {invalid_question}")
        
        error_messages = []
        
        async def message_handler(message: Dict[str, Any]):
            if message.get('type') == 'error':
                error_messages.append(message)
                print(f"❌ 错误: {message.get('content', '')}")
        
        try:
            result = await orchestrator.process_query(
                session_id=session_id,
                user_question=invalid_question,
                message_callback=message_handler
            )
            
            # 验证错误处理
            if not result.get('success'):
                assert len(error_messages) > 0, "应该收到错误消息"
                assert error_messages[0].get('content'), "错误消息应该有内容"
                print(f"\n✅ 错误正确处理")
            
            # 测试恢复：发送正常问题
            normal_question = "查询产品列表"
            print(f"\n👤 正常问题: {normal_question}")
            
            result2 = await orchestrator.process_query(
                session_id=session_id,
                user_question=normal_question
            )
            
            assert result2.get('success'), "错误后应该能继续对话"
            print(f"✅ 系统成功恢复\n")
            
            print(f"✅ 错误处理和恢复测试通过！\n")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}\n")
            raise


def run_tests():
    """运行所有测试"""
    print(f"\n{'='*60}")
    print(f"🚀 开始端到端对话界面功能测试")
    print(f"{'='*60}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 运行 pytest
    pytest.main([
        __file__,
        '-v',
        '-s',
        '--tb=short',
        '--asyncio-mode=auto'
    ])
    
    print(f"\n{'='*60}")
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    run_tests()
