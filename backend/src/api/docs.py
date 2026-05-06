"""
数据准备模块 API 文档配置

此文件配置 FastAPI 的 OpenAPI 文档，为数据准备模块提供完整的 API 文档支持。
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.models import OpenAPI
from typing import Dict, Any
import logging

# 创建日志记录器
logger = logging.getLogger(__name__)

def create_data_prep_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """
    创建数据准备模块的自定义 OpenAPI Schema
    """
    
    if app.openapi_schema:
        return app.openapi_schema
    
    # 获取默认的 OpenAPI schema
    openapi_schema = get_openapi(
        title="ChatBI 数据准备 API",
        version="1.0.0",
        description="""
        ChatBI 数据准备模块提供完整的 Excel 文件处理和数据表管理功能，支持从 Excel 文件导入、解析、验证到创建数据库表的全流程。
        
        ## 功能特性
        
        - **Excel 文件解析**：分析 Excel 文件结构、预览数据、验证数据质量
        - **自动表结构生成**：根据 Excel 数据自动生成数据库表结构
        - **异步导入**：支持大文件异步导入，提供任务状态跟踪
        - **数据表管理**：CRUD 操作，支持数据源关联和字段管理
        - **数据字典**：标准化数据值，支持多级分类
        
        ## 使用指南
        
        1. 首先上传 Excel 文件
        2. 使用 /api/excel/structure 获取文件结构
        3. 使用 /api/excel/generate-schema 生成表结构
        4. 使用 /api/data-tables 创建数据表
        5. 使用 /api/data-tables/import-excel 异步导入数据
        6. 使用 /api/data-tables/import-status/{job_id} 跟踪导入进度
        
        ## 错误处理
        
        所有 API 响应都遵循统一的错误格式：
        {
            "detail": "错误信息"
        }
        
        错误码规范：
        - 400: 请求参数错误
        - 401: 未授权
        - 403: 禁止访问
        - 404: 资源不存在
        - 409: 资源冲突
        - 422: 请求体验证失败
        - 500: 服务器内部错误
        """,
        routes=app.routes,
    )
    
    # 添加标签分组
    openapi_schema["tags"] = [
        {
            "name": "Excel解析",
            "description": "Excel 文件结构分析和数据预览功能"
        },
        {
            "name": "Excel导入",
            "description": "Excel 文件异步导入和数据表创建功能"
        },
        {
            "name": "数据表管理",
            "description": "数据表的CRUD操作和字段管理"
        },
        {
            "name": "数据字典",
            "description": "数据值标准化和字典管理"
        }
    ]
    
    # 确保 components 键存在，如果不存在则创建空字典
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    # 添加全局响应示例
    openapi_schema["components"]["responses"] = {
        "400": {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "表名不能为空"
                            }
                        }
                    }
                }
            }
        },
        "404": {
            "description": "资源不存在",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "数据表不存在"
                            }
                        }
                    }
                }
            }
        },
        "409": {
            "description": "资源冲突",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "数据源下已存在同名表"
                            }
                        }
                    }
                }
            }
        },
        "422": {
            "description": "请求体验证失败",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "loc": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            }
                                        },
                                        "msg": {
                                            "type": "string"
                                        },
                                        "type": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "500": {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "创建数据表失败"
                            }
                        }
                    }
                }
            }
        }
    }
    
    # 添加请求体示例
    openapi_schema["components"]["examples"] = {
        "excel_import_example": {
            "summary": "Excel 导入示例",
            "value": {
                "table_name": "销售数据",
                "sheet_name": "Sheet1",
                "header_row": 1,
                "start_row": 2,
                "create_table": True,
                "replace_existing": False
            }
        },
        "table_create_example": {
            "summary": "数据表创建示例",
            "value": {
                "table_name": "客户信息",
                "source_id": "src-123",
                "description": "客户基本信息表",
                "is_active": True
            }
        }
    }
    
    # 添加安全方案
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # 添加全局安全要求
    openapi_schema["security"] = [
        {
            "BearerAuth": []
        }
    ]
    
    # 配置 Swagger UI 主题
    openapi_schema["info"]["x-logo"] = {
        "url": "https://chatbi.example.com/logo.png",
        "altText": "ChatBI Logo"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# 定义错误码对照表
ERROR_CODES = {
    # 400 Bad Request
    "400_001": "表名不能为空",
    "400_002": "仅支持 .xlsx 和 .xls 文件格式",
    "400_003": "Sheet 名称不能为空",
    "400_004": "数据源ID不能为空",
    "400_005": "文件路径无效",
    "400_006": "行号必须大于0",
    "400_007": "预览行数限制必须在1-1000之间",
    
    # 401 Unauthorized
    "401_001": "未提供认证信息",
    "401_002": "认证信息无效",
    
    # 403 Forbidden
    "403_001": "没有访问权限",
    "403_002": "禁止执行此操作",
    
    # 404 Not Found
    "404_001": "数据表不存在",
    "404_002": "数据源不存在",
    "404_003": "导入任务不存在",
    "404_004": "Sheet 不存在",
    "404_005": "字段不存在",
    
    # 409 Conflict
    "409_001": "数据源下已存在同名表",
    "409_002": "字典值已存在",
    "409_003": "表名已存在",
    
    # 422 Unprocessable Entity
    "422_001": "请求体验证失败",
    "422_002": "字段类型无效",
    "422_003": "数据格式不正确",
    
    # 500 Internal Server Error
    "500_001": "创建数据表失败",
    "500_002": "更新数据表失败",
    "500_003": "删除数据表失败",
    "500_004": "获取数据表列表失败",
    "500_005": "导入任务启动失败",
    "500_006": "获取导入状态失败",
    "500_007": "数据库连接失败",
    "500_008": "Excel文件解析失败",
    "500_009": "文件上传失败",
    "500_010": "同步表结构失败",
    
    # 200 Success (for reference)
    "200_001": "操作成功",
    "200_002": "任务已启动",
    "200_003": "数据已刷新"
}

# 错误处理建议
ERROR_RECOMMENDATIONS = {
    "400_001": "请检查请求参数，确保表名非空",
    "400_002": "请确保上传的文件是 .xlsx 或 .xls 格式",
    "400_003": "请指定有效的 Sheet 名称",
    "400_004": "请提供有效的数据源ID",
    "400_005": "请检查文件路径是否正确，确保文件存在",
    "400_006": "请确保行号为正整数",
    "400_007": "请将预览行数设置在1-1000之间",
    
    "401_001": "请提供有效的认证令牌",
    "401_002": "请重新登录获取新的认证令牌",
    
    "403_001": "请联系管理员获取访问权限",
    "403_002": "您没有执行此操作的权限",
    
    "404_001": "请检查数据表ID是否正确",
    "404_002": "请检查数据源ID是否正确",
    "404_003": "请检查导入任务ID是否正确",
    "404_004": "请检查 Sheet 名称是否正确",
    "404_005": "请检查字段ID是否正确",
    
    "409_001": "请使用不同的表名或删除现有表",
    "409_002": "请使用不同的字典值",
    "409_003": "请使用不同的表名",
    
    "422_001": "请检查请求体格式和字段值",
    "422_002": "请使用有效的字段类型（如：string、integer、date等）",
    "422_003": "请检查数据格式是否符合要求",
    
    "500_001": "请检查数据库连接和权限，重试操作",
    "500_002": "请检查数据库连接和权限，重试操作",
    "500_003": "请检查是否有依赖的字段，先删除依赖项",
    "500_004": "请检查数据库连接，重试操作",
    "500_005": "请检查文件路径和权限，重试操作",
    "500_006": "请检查任务ID是否正确，重试操作",
    "500_007": "请检查数据库服务是否运行，重试操作",
    "500_008": "请检查Excel文件是否损坏，重试操作",
    "500_009": "请检查文件大小和权限，重试操作",
    "500_010": "请检查数据源连接配置，重试操作",
    
    "200_001": "操作成功",
    "200_002": "任务已启动，请使用任务ID查询状态",
    "200_003": "数据已刷新"
}

# 快速开始指南
QUICK_START_GUIDE = """
# 快速开始指南

## 1. 上传 Excel 文件

首先，将 Excel 文件上传到服务器的 uploads 目录，或使用 /api/excel/structure 接口直接提供文件路径。

## 2. 分析文件结构

使用以下接口获取 Excel 文件的结构信息：

```bash
curl -X GET "http://localhost:8000/api/excel/structure?file_path=/path/to/your/file.xlsx" \
-H "accept: application/json"
```

## 3. 生成表结构

根据文件结构生成数据库表结构：

```bash
curl -X GET "http://localhost:8000/api/excel/generate-schema?file_path=/path/to/your/file.xlsx&sheet_name=Sheet1&table_name=customers" \
-H "accept: application/json"
```

## 4. 创建数据表

使用生成的表结构创建数据表：

```bash
curl -X POST "http://localhost:8000/api/data-tables" \
-H "accept: application/json" \
-H "Content-Type: application/json" \
-d '{
  "table_name": "customers",
  "source_id": "src-123",
  "description": "客户基本信息表",
  "is_active": true
}'
```

## 5. 异步导入数据

使用异步导入功能将数据导入到数据表：

```bash
curl -X POST "http://localhost:8000/api/data-tables/import-excel" \
-F "file=@/path/to/your/file.xlsx" \
-F "table_name=customers" \
-F "sheet_name=Sheet1" \
-F "header_row=1" \
-F "start_row=2" \
-F "create_table=true" \
-F "replace_existing=false"
```

## 6. 跟踪导入进度

使用任务ID查询导入进度：

```bash
curl -X GET "http://localhost:8000/api/data-tables/import-status/{job_id}" \
-H "accept: application/json"
```

## 7. 管理数据表

您可以使用标准的 CRUD 操作管理数据表：

- GET /api/data-tables - 获取数据表列表
- GET /api/data-tables/{table_id} - 获取数据表详情
- PUT /api/data-tables/{table_id} - 更新数据表
- DELETE /api/data-tables/{table_id} - 删除数据表

## 8. 管理数据字典

使用数据字典标准化数据值：

- GET /api/dictionary - 获取字典列表
- POST /api/dictionary - 创建字典项
- PUT /api/dictionary/{id} - 更新字典项
- DELETE /api/dictionary/{id} - 删除字典项
"""

# 示例请求和响应
EXAMPLES = {
    "get_excel_structure": {
        "request": {
            "method": "GET",
            "url": "/api/excel/structure",
            "params": {
                "file_path": "/uploads/1769526356-test.xlsx"
            }
        },
        "response": {
            "success": True,
            "data": {
                "file_name": "1769526356-test.xlsx",
                "sheets": [
                    {
                        "name": "Sheet1",
                        "rows": 100,
                        "columns": 5,
                        "headers": ["ID", "姓名", "年龄", "城市", "注册日期"],
                        "data_types": ["integer", "string", "integer", "string", "date"]
                    }
                ]
            }
        }
    },
    "generate_table_schema": {
        "request": {
            "method": "GET",
            "url": "/api/excel/generate-schema",
            "params": {
                "file_path": "/uploads/1769526356-test.xlsx",
                "sheet_name": "Sheet1",
                "table_name": "customers"
            }
        },
        "response": {
            "success": True,
            "data": {
                "table_name": "customers",
                "columns": [
                    {
                        "name": "id",
                        "type": "INTEGER",
                        "nullable": False,
                        "primary_key": True
                    },
                    {
                        "name": "name",
                        "type": "VARCHAR(255)",
                        "nullable": False
                    },
                    {
                        "name": "age",
                        "type": "INTEGER",
                        "nullable": True
                    },
                    {
                        "name": "city",
                        "type": "VARCHAR(255)",
                        "nullable": True
                    },
                    {
                        "name": "register_date",
                        "type": "DATE",
                        "nullable": True
                    }
                ],
                "constraints": [
                    "PRIMARY KEY (id)",
                    "UNIQUE (name)"
                ]
            }
        }
    },
    "create_data_table": {
        "request": {
            "method": "POST",
            "url": "/api/data-tables",
            "json": {
                "table_name": "customers",
                "source_id": "src-123",
                "description": "客户基本信息表",
                "is_active": True
            }
        },
        "response": {
            "id": "dt-456",
            "table_name": "customers",
            "source_id": "src-123",
            "description": "客户基本信息表",
            "is_active": True,
            "row_count": 0,
            "column_count": 5,
            "created_at": "2026-01-30T10:00:00Z",
            "updated_at": "2026-01-30T10:00:00Z"
        }
    },
    "import_excel": {
        "request": {
            "method": "POST",
            "url": "/api/data-tables/import-excel",
            "form_data": {
                "file": "<file>",
                "table_name": "customers",
                "sheet_name": "Sheet1",
                "header_row": "1",
                "start_row": "2",
                "create_table": "true",
                "replace_existing": "false"
            }
        },
        "response": {
            "job_id": "import_1706523456_123456",
            "status": "pending",
            "progress": 0.0,
            "created_at": "2026-01-30T10:00:00Z"
        }
    },
    "get_import_status": {
        "request": {
            "method": "GET",
            "url": "/api/data-tables/import-status/import_1706523456_123456"
        },
        "response": {
            "job_id": "import_1706523456_123456",
            "status": "completed",
            "progress": 100.0,
            "created_at": "2026-01-30T10:00:00Z",
            "completed_at": "2026-01-30T10:01:30Z",
            "result": {
                "imported_rows": 95,
                "failed_rows": 0,
                "table_id": "dt-456"
            }
        }
    }
}

# 错误码对照表
ERROR_CODE_TABLE = """
| 错误码 | 错误信息 | 建议解决方案 |
|--------|----------|--------------|
| 400_001 | 表名不能为空 | 请检查请求参数，确保表名非空 |
| 400_002 | 仅支持 .xlsx 和 .xls 文件格式 | 请确保上传的文件是 .xlsx 或 .xls 格式 |
| 400_003 | Sheet 名称不能为空 | 请指定有效的 Sheet 名称 |
| 400_004 | 数据源ID不能为空 | 请提供有效的数据源ID |
| 400_005 | 文件路径无效 | 请检查文件路径是否正确，确保文件存在 |
| 400_006 | 行号必须大于0 | 请确保行号为正整数 |
| 400_007 | 预览行数限制必须在1-1000之间 | 请将预览行数设置在1-1000之间 |
| 401_001 | 未提供认证信息 | 请提供有效的认证令牌 |
| 401_002 | 认证信息无效 | 请重新登录获取新的认证令牌 |
| 403_001 | 没有访问权限 | 请联系管理员获取访问权限 |
| 403_002 | 禁止执行此操作 | 您没有执行此操作的权限 |
| 404_001 | 数据表不存在 | 请检查数据表ID是否正确 |
| 404_002 | 数据源不存在 | 请检查数据源ID是否正确 |
| 404_003 | 导入任务不存在 | 请检查导入任务ID是否正确 |
| 404_004 | Sheet 不存在 | 请检查 Sheet 名称是否正确 |
| 404_005 | 字段不存在 | 请检查字段ID是否正确 |
| 409_001 | 数据源下已存在同名表 | 请使用不同的表名或删除现有表 |
| 409_002 | 字典值已存在 | 请使用不同的字典值 |
| 409_003 | 表名已存在 | 请使用不同的表名 |
| 422_001 | 请求体验证失败 | 请检查请求体格式和字段值 |
| 422_002 | 字段类型无效 | 请使用有效的字段类型（如：string、integer、date等） |
| 422_003 | 数据格式不正确 | 请检查数据格式是否符合要求 |
| 500_001 | 创建数据表失败 | 请检查数据库连接和权限，重试操作 |
| 500_002 | 更新数据表失败 | 请检查数据库连接和权限，重试操作 |
| 500_003 | 删除数据表失败 | 请检查是否有依赖的字段，先删除依赖项 |
| 500_004 | 获取数据表列表失败 | 请检查数据库连接，重试操作 |
| 500_005 | 导入任务启动失败 | 请检查文件路径和权限，重试操作 |
| 500_006 | 获取导入状态失败 | 请检查任务ID是否正确，重试操作 |
| 500_007 | 数据库连接失败 | 请检查数据库服务是否运行，重试操作 |
| 500_008 | Excel文件解析失败 | 请检查Excel文件是否损坏，重试操作 |
| 500_009 | 文件上传失败 | 请检查文件大小和权限，重试操作 |
| 500_010 | 同步表结构失败 | 请检查数据源连接配置，重试操作 |
"""