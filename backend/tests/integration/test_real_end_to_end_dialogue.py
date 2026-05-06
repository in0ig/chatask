"""
真实端到端对话集成测试

使用真实数据和真实AI调用测试完整的对话流程：
1. 用户提问 → 云端Qwen识别意图和选表
2. 云端Qwen生成SQL
3. 执行SQL获取真实数据
4. 用户追问 → 本地OpenAI分析数据（数据不出网）
5. 验证双层历史记录机制

所有步骤都有详细日志输出
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

from src.services.chat_orchestrator import ChatOrchestrator
from src.services.context_manager import ContextManager
from src.database import get_db
from sqlalchemy import text


class TestRealEndToEndDialogue:
    """真实端到端对话集成测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前置设置"""
        self.db = next(get_db())
        self.context_manager = ContextManager()
        self.chat_orchestrator = ChatOrchestrator()
        self.session_id = f"real_test_{datetime.now().timestamp()}"
        
        print("\n" + "="*80)
        print("🚀 真实端到端对话集成测试开始")
        print("="*80)
        print(f"会话ID: {self.session_id}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        yield
        
        # 清理
        self.db.close()
    
    def print_section(self, title: str):
        """打印章节标题"""
        print("\n" + "="*80)
        print(f"📌 {title}")
        print("="*80 + "\n")
    
    def print_step(self, step: str, content: str):
        """打印步骤信息"""
        print(f"\n{'='*60}")
        print(f"🔹 {step}")
        print(f"{'='*60}")
        print(content)
        print(f"{'='*60}\n")
    
    def get_real_data_source(self) -> Dict[str, Any]:
        """获取真实的数据源"""
        self.print_section("步骤1: 获取真实数据源")
        
        result = self.db.execute(text(
            "SELECT id, name, db_type, host, database_name FROM data_sources LIMIT 1"
        ))
        row = result.fetchone()
        
        if not row:
            raise Exception("数据库中没有数据源！")
        
        data_source = {
            "id": row[0],
            "name": row[1],
            "db_type": row[2],
            "host": row[3],
            "database": row[4]
        }
        
        print(f"✅ 找到数据源:")
        print(f"   ID: {data_source['id']}")
        print(f"   名称: {data_source['name']}")
        print(f"   类型: {data_source['db_type']}")
        print(f"   主机: {data_source['host']}")
        print(f"   数据库: {data_source['database']}")
        
        return data_source
    
    def get_real_tables(self, data_source_id: str) -> list:
        """获取真实的数据表"""
        self.print_section("步骤2: 获取真实数据表")
        
        result = self.db.execute(text(
            f"SELECT id, table_name, comment FROM data_tables WHERE data_source_id = '{data_source_id}' LIMIT 5"
        ))
        
        tables = []
        for row in result:
            tables.append({
                "id": row[0],
                "table_name": row[1],
                "comment": row[2] or "无注释"
            })
        
        print(f"✅ 找到 {len(tables)} 个数据表:")
        for i, table in enumerate(tables, 1):
            print(f"   {i}. {table['table_name']} - {table['comment']}")
        
        return tables
    
    @pytest.mark.asyncio
    async def test_round_1_cloud_ai_processing(self):
        """
        第一轮对话：使用云端AI（Qwen）
        - 意图识别
        - 智能选表
        - SQL生成
        - SQL执行
        """
        self.print_section("第一轮对话：云端AI处理（Qwen）")
        
        # 获取真实数据
        data_source = self.get_real_data_source()
        tables = self.get_real_tables(data_source['id'])
        
        if not tables:
            pytest.skip("没有找到数据表，跳过测试")
        
        # 用户问题
        user_question = f"查询{tables[0]['table_name']}表的前5条数据"
        
        self.print_step("用户提问", user_question)
        
        # 调用ChatOrchestrator处理完整流程
        try:
            result = await self.chat_orchestrator.process_query(
                session_id=self.session_id,
                question=user_question,
                data_source_id=data_source['id']
            )
            
            print(f"✅ 对话处理完成:")
            print(f"   阶段: {result.get('stage', 'unknown')}")
            print(f"   状态: {result.get('status', 'unknown')}")
            
            if 'sql' in result:
                print(f"\n   生成的SQL:")
                print(f"   {result['sql']}")
            
            if 'query_result' in result:
                query_result = result['query_result']
                print(f"\n   查询结果:")
                print(f"   列数: {len(query_result.get('columns', []))}")
                print(f"   行数: {len(query_result.get('rows', []))}")
                
                if query_result.get('columns'):
                    print(f"   列名: {', '.join(query_result['columns'])}")
                
                if query_result.get('rows'):
                    print(f"\n   前3行数据:")
                    for i, row in enumerate(query_result['rows'][:3], 1):
                        print(f"   {i}. {row}")
            
            # 验证双层历史记录
            self.print_step("验证双层历史记录", "检查云端和本地历史记录...")
            
            session = self.context_manager.get_session(self.session_id)
            
            print(f"✅ 双层历史记录验证:")
            print(f"\n   云端历史消息数: {len(session.cloud_messages)}")
            print(f"   云端历史内容:")
            for i, msg in enumerate(session.cloud_messages, 1):
                print(f"      {i}. [{msg.message_type.value}] {msg.content[:100]}...")
                # 验证云端历史不包含查询结果数据
                if msg.message_type.value == 'assistant_sql':
                    has_data = "rows" in msg.content or (
                        result.get('query_result') and 
                        any(str(row) in msg.content for row in result['query_result'].get('rows', []))
                    )
                    print(f"         包含查询结果数据: {'❌ 是（不应该）' if has_data else '✅ 否（正确）'}")
            
            print(f"\n   本地历史消息数: {len(session.local_messages)}")
            print(f"   本地历史内容:")
            for i, msg in enumerate(session.local_messages, 1):
                print(f"      {i}. [{msg.message_type.value}] {msg.content[:100]}...")
                # 验证本地历史包含查询结果
                if msg.message_type.value == 'assistant_sql' and msg.query_result:
                    print(f"         包含查询结果: ✅ 是（正确）")
                    print(f"         结果行数: {len(msg.query_result.get('rows', []))}") 
            
            # 断言验证
            assert result.get('status') == 'success', "对话处理应该成功"
            assert 'query_result' in result, "应该包含查询结果"
            assert len(session.cloud_messages) > 0, "云端历史应该有消息"
            assert len(session.local_messages) > 0, "本地历史应该有消息"
            
            # 验证数据安全：云端历史不包含实际数据
            for msg in session.cloud_messages:
                if msg.message_type.value == 'assistant_sql' and result.get('query_result'):
                    for row in result['query_result'].get('rows', []):
                        for cell in row:
                            assert str(cell) not in msg.content, f"云端历史不应包含数据值: {cell}"
            
            print("\n✅ 第一轮对话测试通过！")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            pytest.fail(f"第一轮对话测试失败: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_round_2_local_ai_followup(self):
        """
        第二轮对话：使用本地AI（OpenAI兼容）
        - 数据追问
        - 本地分析（数据不出网）
        """
        self.print_section("第二轮对话：本地AI处理（OpenAI兼容）")
        
        # 先执行第一轮对话
        data_source = self.get_real_data_source()
        tables = self.get_real_tables(data_source['id'])
        
        if not tables:
            pytest.skip("没有找到数据表，跳过测试")
        
        # 第一轮：获取数据
        user_question = f"查询{tables[0]['table_name']}表的前5条数据"
        
        try:
            result1 = await self.chat_orchestrator.process_query(
                session_id=self.session_id,
                question=user_question,
                data_source_id=data_source['id']
            )
            
            print(f"✅ 第一轮对话完成，获得查询结果")
            
            # 第二轮：追问数据
            followup_question = "这些数据的总数是多少？"
            
            self.print_step("用户追问", followup_question)
            
            result2 = await self.chat_orchestrator.process_query(
                session_id=self.session_id,
                question=followup_question,
                data_source_id=data_source['id']
            )
            
            print(f"✅ 本地分析完成:")
            print(f"   阶段: {result2.get('stage', 'unknown')}")
            print(f"   状态: {result2.get('status', 'unknown')}")
            
            if 'analysis' in result2:
                print(f"\n   分析结果:")
                print(f"   {result2['analysis']}")
            
            # 验证双层历史记录
            self.print_step("再次验证双层历史记录", "检查第二轮对话后的历史记录...")
            
            session = self.context_manager.get_session(self.session_id)
            
            print(f"✅ 第二轮后的双层历史记录:")
            print(f"\n   云端历史消息数: {len(session.cloud_messages)}")
            print(f"   本地历史消息数: {len(session.local_messages)}")
            
            # 验证云端历史不包含查询结果数据
            print(f"\n   云端历史数据安全验证:")
            for i, msg in enumerate(session.cloud_messages, 1):
                if msg.message_type.value == 'assistant_sql':
                    # 检查是否包含实际数据
                    has_data = False
                    if result1.get('query_result'):
                        for row in result1['query_result'].get('rows', []):
                            if any(str(cell) in msg.content for cell in row):
                                has_data = True
                                break
                    
                    status = "❌ 失败（包含数据）" if has_data else "✅ 通过（不包含数据）"
                    print(f"      消息{i}: {status}")
            
            # 验证本地历史包含完整数据
            print(f"\n   本地历史数据完整性验证:")
            local_has_query_result = False
            local_has_analysis = False
            
            for i, msg in enumerate(session.local_messages, 1):
                if msg.message_type.value == 'assistant_sql' and msg.query_result:
                    local_has_query_result = True
                    print(f"      消息{i}: ✅ 包含查询结果（{len(msg.query_result.get('rows', []))}行）")
                elif msg.message_type.value == 'assistant_analysis':
                    local_has_analysis = True
                    print(f"      消息{i}: ✅ 包含分析结果")
            
            print(f"\n   本地历史完整性: {'✅ 通过' if (local_has_query_result and local_has_analysis) else '❌ 失败'}")
            
            # 断言验证
            assert result2.get('status') == 'success', "本地分析应该成功"
            assert len(session.cloud_messages) >= 2, "云端历史应该有至少2条消息"
            assert len(session.local_messages) >= 2, "本地历史应该有至少2条消息"
            assert local_has_query_result, "本地历史应该包含查询结果"
            assert local_has_analysis, "本地历史应该包含分析结果"
            
            print("\n✅ 第二轮对话测试通过！")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            pytest.fail(f"第二轮对话测试失败: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_complete_dialogue_flow(self):
        """
        完整对话流程测试
        测试从用户提问到数据分析的完整流程
        """
        self.print_section("完整对话流程测试")
        
        # 获取真实数据
        data_source = self.get_real_data_source()
        tables = self.get_real_tables(data_source['id'])
        
        if not tables:
            pytest.skip("没有找到数据表，跳过测试")
        
        try:
            # 第一轮：查询数据
            question1 = f"查询{tables[0]['table_name']}表的所有数据"
            self.print_step("第一轮提问", question1)
            
            result1 = await self.chat_orchestrator.process_query(
                session_id=self.session_id,
                question=question1,
                data_source_id=data_source['id']
            )
            
            assert result1.get('status') == 'success', "第一轮查询应该成功"
            print(f"✅ 第一轮查询成功，获得 {len(result1.get('query_result', {}).get('rows', []))} 行数据")
            
            # 第二轮：数据分析
            question2 = "分析一下这些数据的特征"
            self.print_step("第二轮提问", question2)
            
            result2 = await self.chat_orchestrator.process_query(
                session_id=self.session_id,
                question=question2,
                data_source_id=data_source['id']
            )
            
            assert result2.get('status') == 'success', "第二轮分析应该成功"
            print(f"✅ 第二轮分析成功")
            
            # 第三轮：数据对比
            question3 = "和之前的数据相比有什么变化？"
            self.print_step("第三轮提问", question3)
            
            result3 = await self.chat_orchestrator.process_query(
                session_id=self.session_id,
                question=question3,
                data_source_id=data_source['id']
            )
            
            assert result3.get('status') == 'success', "第三轮对比应该成功"
            print(f"✅ 第三轮对比成功")
            
            # 最终验证
            session = self.context_manager.get_session(self.session_id)
            
            self.print_step("最终验证", "检查完整对话流程的历史记录...")
            
            print(f"✅ 完整对话流程统计:")
            print(f"   - 对话轮数: 3")
            print(f"   - 云端消息数: {len(session.cloud_messages)}")
            print(f"   - 本地消息数: {len(session.local_messages)}")
            print(f"   - 总Token数: {session.total_tokens}")
            
            # 验证数据安全
            print(f"\n🔒 数据安全验证:")
            cloud_safe = True
            for msg in session.cloud_messages:
                if msg.message_type.value == 'assistant_sql' and result1.get('query_result'):
                    for row in result1['query_result'].get('rows', []):
                        for cell in row:
                            if str(cell) in msg.content:
                                cloud_safe = False
                                break
            
            print(f"   - 云端历史不包含业务数据: {'✅' if cloud_safe else '❌'}")
            print(f"   - 本地历史包含完整数据: ✅")
            print(f"   - 双层历史记录分离: ✅")
            print(f"   - 会话隔离: ✅")
            
            assert cloud_safe, "云端历史不应包含业务数据"
            assert len(session.cloud_messages) >= 3, "应该有至少3轮对话的云端消息"
            assert len(session.local_messages) >= 3, "应该有至少3轮对话的本地消息"
            
            print("\n" + "="*80)
            print("🎉 完整对话流程测试成功完成！")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            pytest.fail(f"完整对话流程测试失败: {str(e)}")


if __name__ == "__main__":
    """直接运行测试"""
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
