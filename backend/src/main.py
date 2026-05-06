from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
import sys

# 加载环境变量
load_dotenv()

# 导入日志配置
from src.utils import logger

# 确保日志模块正确加载
try:
    from src.utils import logger
except ImportError as e:
    print(f"Error importing logger: {e}", file=sys.stderr)
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# 导入所有模型以确保它们被正确注册到Base.metadata
# 必须在导入路由之前执行，以确保SQLAlchemy能正确解析所有关系
from src.models import Base
from src.models.data_source_model import DataSource
from src.models.data_preparation_model import DataTable, TableField, Dictionary, DictionaryItem, DynamicDictionaryConfig, TableRelation
from src.models.knowledge_base_model import KnowledgeBase
from src.models.knowledge_item_model import KnowledgeItem
from src.models.database_models import PromptConfig, SessionContext, ConversationMessage, TokenUsageStats
from src.models.dialogue_session_model import DialogueSession
from src.models.fiscal_calendar_model import FiscalCalendar

# 导入数据库配置
from src.database import get_db
from src.database_engine import engine

# 创建应用实例
# redirect_slashes=True（默认）：FastAPI 会对不带斜杠的路径做 307 redirect
# 但 nginx 层已经在 proxy 前补全了斜杠，所以 FastAPI 的 redirect 永远不会触发
app = FastAPI(title="ChatBI Backend", description="Natural Language Query System")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入AI模型服务配置
from src.config.ai_config import init_ai_config, get_ai_config, validate_ai_config, check_required_env_vars
from src.services.ai_model_service import init_ai_service, get_ai_service

# 导入路由
from src.api.data_source_api import router as data_source_router
from src.api.datasources_api import router as datasources_router  # ChatBI 兼容路由
from src.api.query_api import router as query_router
from src.api.settings_api import router as settings_router
# from src.api.session_api import router as session_router  # 暂时禁用，需要修复database_service依赖
from src.api.history_api import router as history_router
from src.api.prompt_api import router as prompt_router
from src.api.context_api import router as context_router
from src.api.multi_turn_api import router as multi_turn_router
from src.api.sql_error_recovery_api import router as sql_error_recovery_router
from src.api.knowledge_base import router as knowledge_base_router
from src.api.knowledge_item import router as knowledge_item_router
from src.api.data_table_api import router as data_table_router
from src.api.table_field import router as table_field_router
from src.api.excel_upload import router as excel_upload_router
from src.api.excel_parser_api import router as excel_parser_router
from src.api.excel_importer_api import router as excel_importer_router
from src.api.table_relation import router as table_relation_router
from src.api.dictionary import router as dictionary_router
from src.api.dynamic_dictionary import router as dynamic_dictionary_router
from src.api.dictionary_version import router as dictionary_version_router
from src.api.table_folder import router as table_folder_router
from src.api.field_mapping import router as field_mapping_router
from src.api.semantic_injection_api import router as semantic_injection_router
from src.api.knowledge_semantic_injection_api import router as knowledge_semantic_injection_router
from src.api.intent_context_manager_api import router as intent_context_manager_router
from src.api.semantic_context_aggregator_api import router as semantic_context_aggregator_router
from src.api.multi_source_data_integration_api import router as multi_source_integration_router
from src.api.ai_chat_api import router as ai_chat_router
from src.api.prompt_template_api import router as prompt_template_router
from src.api.sql_error_learning_api import router as sql_error_learning_router
from src.api.sql_security_api import router as sql_security_router
from src.api.websocket_stream_api import router as websocket_stream_router
from src.api.chat_orchestrator_api import router as chat_orchestrator_router
from src.api.intent_recognition_api import router as intent_recognition_router
from src.api.intent_clarification_api import router as intent_clarification_router
from src.api.semantic_similarity_api import router as semantic_similarity_router
from src.api.intelligent_table_selector_api import router as intelligent_table_selector_router
from src.api.table_selection_validator_api import router as table_selection_validator_router
from src.api.sql_generator_api import router as sql_generator_router
from src.api.sql_executor_api import router as sql_executor_router
from src.api.dialogue_session_api import router as dialogue_session_router
from src.api.local_data_analyzer_api import router as local_data_analyzer_router
from src.api.session_api import router as session_api_router
from src.api.prompt_test_api import router as prompt_test_router
from src.api.fiscal_calendar_api import router as fiscal_calendar_router

# 注意：很多路由器已经在定义时包含了前缀，不需要重复添加
app.include_router(data_source_router)  # 已包含 /api/data-sources 前缀
app.include_router(datasources_router)  # 已包含 /api/datasources 前缀 (ChatBI 兼容路由)
app.include_router(query_router, prefix="/api/query")
app.include_router(settings_router, prefix="/api/settings")
# app.include_router(session_router, prefix="/api/sessions")  # 暂时禁用
app.include_router(history_router, prefix="/api/query")
app.include_router(prompt_router, prefix="/api/prompts")
app.include_router(context_router, prefix="/api")
app.include_router(session_api_router)  # 已包含 /api/sessions 前缀 - 会话管理的主要路由
# 注意：multi_turn_router 已被 session_api_router 替代，不再单独注册以避免路由冲突
# app.include_router(multi_turn_router, prefix="/api/sessions")  # 已禁用，使用 session_api_router
app.include_router(sql_error_recovery_router)  # 已包含 /api/sql-error-recovery 前缀
app.include_router(knowledge_base_router, prefix="/api/knowledge-bases")
app.include_router(knowledge_item_router, prefix="/api/knowledge-items")
app.include_router(data_table_router, prefix="/api/data-tables")
app.include_router(table_field_router)  # 已包含 /api 前缀
app.include_router(excel_upload_router)  # 已包含 /api/data-sources 前缀
app.include_router(excel_parser_router)  # 已包含 /api/excel 前缀
app.include_router(excel_importer_router)  # 已包含 /api/data-tables 前缀
app.include_router(table_relation_router)  # 已包含 /api/table-relations 前缀
app.include_router(dictionary_router)  # 已包含 /api/dictionaries 前缀
app.include_router(dynamic_dictionary_router)  # 已包含 /api/dynamic-dictionaries 前缀
app.include_router(dictionary_version_router, prefix="/api/dictionary-version")
app.include_router(table_folder_router)  # 已包含 /api/table-folders 前缀
app.include_router(field_mapping_router)  # 已包含 /api/field-mappings 前缀
app.include_router(semantic_injection_router)  # 已包含 /api/semantic-injection 前缀
app.include_router(knowledge_semantic_injection_router)  # 已包含 /api/knowledge-semantic 前缀
app.include_router(semantic_context_aggregator_router)  # 已包含 /api/semantic-context 前缀
app.include_router(multi_source_integration_router)  # 已包含 /api/multi-source-integration 前缀
app.include_router(ai_chat_router)  # 已包含 /api/ai-chat 前缀
app.include_router(prompt_template_router)  # 已包含 /api/prompt-templates 前缀
app.include_router(sql_error_learning_router)  # 已包含 /api/sql-error-learning 前缀
app.include_router(sql_security_router)  # 已包含 /api/sql-security 前缀
app.include_router(websocket_stream_router)  # 已包含 /api/stream 前缀
app.include_router(chat_orchestrator_router)  # 已包含 /api/chat 前缀
app.include_router(intent_recognition_router)  # 已包含 /api/intent 前缀
app.include_router(intent_clarification_router)  # 已包含 /api/intent-clarification 前缀
app.include_router(intent_context_manager_router)  # 已包含 /api/intent-context 前缀
app.include_router(semantic_similarity_router)  # 已包含 /api/semantic-similarity 前缀
app.include_router(intelligent_table_selector_router)  # 已包含 /api/intelligent-table-selector 前缀
app.include_router(table_selection_validator_router)  # 已包含 /api/table-selection-validator 前缀
app.include_router(sql_generator_router)  # 已包含 /api/sql-generator 前缀
app.include_router(sql_executor_router)  # 已包含 /api/sql-executor 前缀
app.include_router(dialogue_session_router)  # 已包含 /api/dialogue 前缀
app.include_router(local_data_analyzer_router)  # 已包含 /api/local-analyzer 前缀
app.include_router(prompt_test_router)  # 已包含 /api/prompt-test 前缀
app.include_router(fiscal_calendar_router)  # 已包含 /api/fiscal-calendar 前缀
# session_api_router already registered above (before multi_turn_router)

# 导入数据准备模块的文档配置
from src.api.docs import create_data_prep_openapi_schema

# 根据路由
@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "ChatBI Backend is running"}

@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}

# 数据库健康检查端点
@app.get("/health/db")
def database_health_check():
    """
    检查数据库连接状态
    返回详细的数据库健康信息
    """
    logger.info("Database health check endpoint accessed")
    try:
        # 使用SQLAlchemy引擎测试连接
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return {"status": "healthy", "database": "MySQL"}
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}

# 创建一个独立的函数来处理应用启动时的初始化
async def startup_event_handler():
    """
    应用启动时的初始化处理
    创建所有表并注册路由
    """
    logger.info("Initializing database connection on startup...")
    
    # 在测试模式下不创建表，由测试代码负责表创建
    if os.getenv("TEST_MODE", "false").lower() != "true":
        # 生产模式下创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    else:
        logger.info("TEST_MODE is enabled, skipping table creation (handled by test suite)")
    
    # 初始化AI模型服务
    logger.info("Initializing AI model service...")
    try:
        # 检查环境变量
        env_check = check_required_env_vars()
        if not env_check["all_set"]:
            logger.warning("Some required environment variables are missing:")
            for missing in env_check["missing"]:
                logger.warning(f"  - {missing['name']}: {missing['description']}")
        
        # 初始化AI配置
        ai_config = init_ai_config()
        
        # 验证配置
        validation = validate_ai_config()
        if not validation["valid"]:
            logger.error("AI configuration validation failed:")
            for error in validation["errors"]:
                logger.error(f"  - {error}")
        else:
            logger.info("AI configuration validation passed")
        
        if validation["warnings"]:
            for warning in validation["warnings"]:
                logger.warning(f"  - {warning}")
        
        # 初始化AI服务
        service_config = {
            "qwen_cloud": ai_config.get_qwen_config(),
            "openai_local": ai_config.get_openai_config(),
            "model_routing": ai_config.get_full_config().get("model_routing", {})
        }
        
        ai_service = init_ai_service(service_config)
        logger.info("AI model service initialized successfully")
        
        # 记录启用的模型
        if ai_config.is_qwen_enabled():
            logger.info("✅ Qwen cloud model enabled")
        else:
            logger.warning("⚠️  Qwen cloud model not enabled (missing API key)")
        
        if ai_config.is_openai_enabled():
            logger.info("✅ OpenAI local model enabled")
        else:
            logger.warning("⚠️  OpenAI local model not enabled (missing configuration)")
        
    except Exception as e:
        logger.error(f"Failed to initialize AI model service: {str(e)}")
        logger.warning("AI chat functionality will be disabled")
    
    # 打印所有注册的路由
    logger.info("Registered routes:")
    for route in app.routes:
        # 检查路由类型，WebSocket路由没有methods属性
        if hasattr(route, 'methods'):
            logger.info(f"{route.methods} {route.path}")
        else:
            # WebSocket路由或其他类型的路由
            logger.info(f"WebSocket {route.path}")

# 应用启动时初始化数据库连接和其他服务
@app.on_event("startup")
async def startup_event():
    """
    应用启动时的完整初始化流程：
    1. 初始化数据库连接和创建表
    2. 初始化AI模型服务
    3. 设置自定义OpenAPI文档
    4. 打印所有注册的路由用于调试
    """
    # 1. 数据库初始化
    await startup_event_handler()
    
    # 2. 设置自定义 OpenAPI 文档
    try:
        create_data_prep_openapi_schema(app)
        logger.info("Custom OpenAPI schema for data preparation module has been configured")
    except Exception as e:
        logger.error(f"Failed to setup OpenAPI schema: {str(e)}")
    
    # 3. 打印所有注册的路由用于调试
    logger.info("Registered routes:")
    api_routes = []
    
    for route in app.routes:
        # 检查路由类型，WebSocket路由没有methods属性
        if hasattr(route, 'methods'):
            logger.info(f"{route.methods} {route.path}")
        else:
            # WebSocket路由或其他类型的路由
            logger.info(f"WebSocket {route.path}")
        
        # 收集 API 路径进行验证
        if hasattr(route, 'path') and '/api/' in route.path:
            api_routes.append(route.path)
    
    # 验证 API 路径格式
    logger.info("Validating API path formats...")
    for path in api_routes:
        # 检查重复前缀
        path_segments = path.split('/')
        if path_segments.count('api') > 1:
            logger.warning(f"⚠️  Duplicate 'api' prefix detected in path: {path}")
        
        # 检查资源命名（应该使用复数形式）
        if len(path_segments) >= 3:
            resource_segment = path_segments[2]
            # 检查知识库和知识项资源是否使用复数形式
            if resource_segment in ['knowledge-base', 'knowledge-item']:
                logger.warning(f"⚠️  Resource should be plural: {resource_segment} in {path}")
            elif resource_segment in ['knowledge-bases', 'knowledge-items']:
                logger.info(f"✅ Correct plural resource naming: {resource_segment}")
        
        # 检查路径格式（kebab-case）
        for segment in path_segments:
            if segment and '_' in segment:
                logger.warning(f"⚠️  Path segment should use kebab-case instead of snake_case: {segment} in {path}")
    
    logger.info(f"API path validation completed. Total API routes: {len(api_routes)}")
    logger.info("Application startup completed successfully")

# 应用关闭时清理数据库连接
@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭时清理数据库连接和AI服务
    """
    logger.info("Shutting down application...")
    
    # 关闭AI模型服务
    try:
        ai_service = get_ai_service()
        await ai_service.close()
        logger.info("AI model service closed successfully")
    except Exception as e:
        logger.warning(f"Error closing AI model service: {str(e)}")
    
    # 关闭数据库连接
    logger.info("Closing database connection on shutdown...")
    engine.dispose()

if __name__ == "__main__":
    # 获取模型配置
    model_type = os.getenv('MODEL_TYPE', 'local').lower()
    model_name = os.getenv('QWEN_MODEL_NAME', 'qwen-agent')
    
    # 记录启动配置
    logger.info(f"Starting ChatBI Backend server with MODEL_TYPE='{model_type}', QWEN_MODEL_NAME='{model_name}'")
    
    # 使用更健壮的启动配置
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        workers=1,
        timeout_keep_alive=30
    )