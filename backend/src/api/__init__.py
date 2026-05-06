from .context_api import router as context_router
from .data_source_api import router as data_source_router
from .history_api import router as history_router
from .multi_turn_api import router as multi_turn_router
from .prompt_api import router as prompt_router
from .query_api import router as query_router
# from .session_api import router as session_router  # 暂时禁用，需要修复database_service依赖
from .settings_api import router as settings_router
# from .sql_error_recovery_api import router as sql_error_recovery_router  # 暂时禁用，需要修复database_service依赖
from .knowledge_base import router as knowledge_base_router

# 导出所有路由器
routers = [
    context_router,
    data_source_router,
    history_router,
    multi_turn_router,
    prompt_router,
    query_router,
    # session_router,  # 暂时禁用
    settings_router,
    # sql_error_recovery_router,  # 暂时禁用
    knowledge_base_router
]