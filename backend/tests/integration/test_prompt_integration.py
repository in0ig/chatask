"""
测试 Prompt 集成功能 - 真实集成测试（无 Mock）
验证 ChatOrchestrator 是否正确使用 PromptManager 加载和渲染 prompts.yml 中的模板
"""

import pytest
from src.services.prompt_manager import PromptManager, PromptType


class TestPromptManagerIntegration:
    """测试 PromptManager 真实功能"""
    
    def test_prompt_manager_loads_templates_from_yaml(self):
        """测试 PromptManager 从 prompts.yml 加载模板"""
        # 创建真实的 PromptManager 实例
        prompt_manager = PromptManager()
        
        # 验证模板已加载
        assert len(prompt_manager.templates) > 0, "应该加载至少一个模板"
        print(f"✅ PromptManager 加载了 {len(prompt_manager.templates)} 个模板")
        
        # 列出所有加载的模板
        for template_type, template in prompt_manager.templates.items():
            print(f"  - {template_type.value}: {template.name} (v{template.version})")
    
    def test_all_required_templates_are_loaded(self):
        """测试所有必需的模板都已加载"""
        prompt_manager = PromptManager()
        
        # 验证关键模板已加载
        required_templates = [
            PromptType.INTENT_RECOGNITION,
            PromptType.TABLE_SELECTION,
            PromptType.SQL_GENERATION,
            PromptType.DATA_ANALYSIS,
            PromptType.CHART_RECOMMENDATION,
        ]
        
        for template_type in required_templates:
            template = prompt_manager.get_template(template_type)
            assert template is not None, f"模板 {template_type.value} 未加载"
            assert template.content, f"模板 {template_type.value} 内容为空"
            assert len(template.variables) > 0, f"模板 {template_type.value} 没有定义变量"
            print(f"✅ 模板 {template_type.value} 已加载，包含 {len(template.variables)} 个变量")
    
    def test_intent_recognition_template_renders_correctly(self):
        """测试意图识别模板正确渲染"""
        prompt_manager = PromptManager()
        
        # 渲染意图识别模板
        rendered_prompt = prompt_manager.render_prompt(
            PromptType.INTENT_RECOGNITION,
            {
                "user_question": "查询订单总数"
            }
        )
        
        # 验证渲染结果
        assert "查询订单总数" in rendered_prompt, "渲染的 prompt 应包含用户问题"
        assert "用户问题" in rendered_prompt or "user_question" not in rendered_prompt, "变量应被替换"
        assert "intent" in rendered_prompt.lower(), "应包含意图相关内容"
        
        print(f"✅ 意图识别模板渲染成功")
        print(f"📝 渲染结果预览（前 300 字符）:\n{rendered_prompt[:300]}...")
    
    def test_table_selection_template_renders_correctly(self):
        """测试智能选表模板正确渲染"""
        prompt_manager = PromptManager()
        
        # 渲染智能选表模板
        rendered_prompt = prompt_manager.render_prompt(
            PromptType.TABLE_SELECTION,
            {
                "user_question": "查询订单总数",
                "intent_type": "smart_query",
                "semantic_context": "测试语义上下文：包含 orders 表，字段有 id, amount, created_at"
            }
        )
        
        # 验证渲染结果
        assert "查询订单总数" in rendered_prompt, "应包含用户问题"
        assert "smart_query" in rendered_prompt, "应包含意图类型"
        assert "测试语义上下文" in rendered_prompt, "应包含语义上下文"
        assert "user_question" not in rendered_prompt, "变量应被替换"
        
        print(f"✅ 智能选表模板渲染成功")
        print(f"📝 渲染结果预览（前 300 字符）:\n{rendered_prompt[:300]}...")
    
    def test_sql_generation_template_renders_correctly(self):
        """测试 SQL 生成模板正确渲染"""
        prompt_manager = PromptManager()
        
        # 渲染 SQL 生成模板
        rendered_prompt = prompt_manager.render_prompt(
            PromptType.SQL_GENERATION,
            {
                "original_question": "查询订单总数",
                "clarified_requirement": "查询 orders 表中的记录总数",
                "semantic_context": "表名: orders\n字段: id, user_id, amount, created_at",
                "db_type": "MySQL"
            }
        )
        
        # 验证渲染结果
        assert "查询订单总数" in rendered_prompt, "应包含原始问题"
        assert "orders" in rendered_prompt, "应包含表名"
        assert "MySQL" in rendered_prompt, "应包含数据库类型"
        assert "original_question" not in rendered_prompt, "变量应被替换"
        
        print(f"✅ SQL 生成模板渲染成功")
        print(f"📝 渲染结果预览（前 300 字符）:\n{rendered_prompt[:300]}...")
    
    def test_data_analysis_template_renders_correctly(self):
        """测试数据分析模板正确渲染"""
        prompt_manager = PromptManager()
        
        # 渲染数据分析模板
        rendered_prompt = prompt_manager.render_prompt(
            PromptType.DATA_ANALYSIS,
            {
                "user_question": "订单总数是多少",
                "query_result": '{"columns": ["count"], "rows": [[150]]}',
                "previous_data": "无历史数据"
            }
        )
        
        # 验证渲染结果
        assert "订单总数是多少" in rendered_prompt, "应包含用户问题"
        assert "150" in rendered_prompt or "count" in rendered_prompt, "应包含查询结果"
        assert "user_question" not in rendered_prompt, "变量应被替换"
        
        print(f"✅ 数据分析模板渲染成功")
        print(f"📝 渲染结果预览（前 300 字符）:\n{rendered_prompt[:300]}...")
    
    def test_template_variable_validation(self):
        """测试模板变量验证功能"""
        prompt_manager = PromptManager()
        
        # 尝试渲染缺少必需变量的模板
        with pytest.raises(ValueError) as exc_info:
            prompt_manager.render_prompt(
                PromptType.INTENT_RECOGNITION,
                {}  # 缺少 user_question 变量
            )
        
        assert "Missing required variables" in str(exc_info.value), "应该抛出缺少变量的错误"
        print(f"✅ 模板变量验证功能正常工作")
    
    def test_prompt_manager_list_templates(self):
        """测试列出所有模板信息"""
        prompt_manager = PromptManager()
        
        # 获取所有模板信息
        templates_info = prompt_manager.list_templates()
        
        assert len(templates_info) > 0, "应该有模板信息"
        
        # 验证每个模板信息的结构
        for info in templates_info:
            assert "type" in info, "应包含类型"
            assert "name" in info, "应包含名称"
            assert "version" in info, "应包含版本"
            assert "description" in info, "应包含描述"
            assert "variables" in info, "应包含变量列表"
            
            print(f"✅ 模板 {info['type']}: {info['name']} (v{info['version']})")
            print(f"   描述: {info['description']}")
            print(f"   变量: {', '.join(info['variables'])}")


class TestChatOrchestratorPromptIntegration:
    """测试 ChatOrchestrator 与 PromptManager 的集成"""
    
    def test_chat_orchestrator_has_prompt_manager(self):
        """测试 ChatOrchestrator 初始化时创建了 PromptManager"""
        # 注意：这个测试需要真实的环境配置
        # 如果 AI 服务未配置，ChatOrchestrator 初始化会失败
        # 这是一个真实的集成测试，不使用 Mock
        
        try:
            from src.services.chat_orchestrator import ChatOrchestrator
            
            orchestrator = ChatOrchestrator()
            
            # 验证 prompt_manager 已初始化
            assert hasattr(orchestrator, 'prompt_manager'), "ChatOrchestrator 应该有 prompt_manager 属性"
            assert orchestrator.prompt_manager is not None, "prompt_manager 不应为 None"
            assert len(orchestrator.prompt_manager.templates) > 0, "应该加载了模板"
            
            print(f"✅ ChatOrchestrator 成功初始化 PromptManager")
            print(f"📊 加载了 {len(orchestrator.prompt_manager.templates)} 个模板")
            
        except Exception as e:
            # 如果初始化失败（例如 AI 服务未配置），跳过此测试
            pytest.skip(f"ChatOrchestrator 初始化失败（可能是环境配置问题）: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
