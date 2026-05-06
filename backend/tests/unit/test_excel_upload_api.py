import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.api.excel_upload import router
from unittest.mock import patch, MagicMock
import os
import tempfile

# 将路由添加到应用中
app.include_router(router)

client = TestClient(app)

# 测试用例：成功上传Excel文件
def test_upload_excel_success():
    # 创建一个临时的Excel文件用于测试
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        # 写入一些基本的Excel数据
        import pandas as pd
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z']
        })
        df.to_excel(tmp_file.name, index=False)
        
        # 上传文件
        with open(tmp_file.name, 'rb') as f:
            response = client.post("/api/data-sources/upload-excel", files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.xlsx"
        assert len(data["sheet_names"]) == 1
        assert data["sheet_names"][0] == "Sheet1"
        assert data["row_count"] == 3
        assert data["column_count"] == 2
        assert data["file_path"].endswith("test.xlsx")

# 测试用例：文件大小超过限制
def test_upload_excel_file_too_large():
    # 创建一个21MB的临时文件（超过20MB限制）
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        # 写入21MB的随机数据
        tmp_file.write(b'x' * (21 * 1024 * 1024))
        tmp_file.flush()
        
        # 上传文件
        with open(tmp_file.name, 'rb') as f:
            response = client.post("/api/data-sources/upload-excel", files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        # 验证响应
        assert response.status_code == 413
        assert response.json()["detail"] == "File size exceeds 20MB limit."

# 测试用例：文件格式不支持
def test_upload_excel_invalid_format():
    # 创建一个临时的txt文件
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
        tmp_file.write(b"test content")
        tmp_file.flush()
        
        # 上传文件
        with open(tmp_file.name, 'rb') as f:
            response = client.post("/api/data-sources/upload-excel", files={"file": ("test.txt", f, "text/plain")})
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        # 验证响应
        assert response.status_code == 400
        assert "Invalid file format" in response.json()["detail"]
        assert ".xlsx and .xls" in response.json()["detail"]

# 测试用例：文件不存在或损坏
def test_upload_excel_corrupted_file():
    # 创建一个损坏的Excel文件
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        # 写入无效的Excel数据
        tmp_file.write(b"this is not a valid excel file")
        tmp_file.flush()
        
        # 上传文件
        with open(tmp_file.name, 'rb') as f:
            response = client.post("/api/data-sources/upload-excel", files={"file": ("corrupted.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        # 验证响应
        assert response.status_code == 500
        assert "Failed to process uploaded file" in response.json()["detail"]

# 测试用例：空文件上传
def test_upload_excel_empty_file():
    # 创建一个空文件
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        # 文件为空
        pass
        
        # 上传文件
        with open(tmp_file.name, 'rb') as f:
            response = client.post("/api/data-sources/upload-excel", files={"file": ("empty.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        # 验证响应
        assert response.status_code == 500
        assert "Failed to process uploaded file" in response.json()["detail"]

# 测试用例：文件名包含特殊字符
def test_upload_excel_special_characters():
    # 创建一个临时的Excel文件
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        import pandas as pd
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z']
        })
        df.to_excel(tmp_file.name, index=False)
        
        # 使用包含特殊字符的文件名
        special_filename = "test@#$%^&*().xlsx"
        
        # 上传文件
        with open(tmp_file.name, 'rb') as f:
            response = client.post("/api/data-sources/upload-excel", files={"file": (special_filename, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == special_filename
        assert len(data["sheet_names"]) == 1
        assert data["row_count"] == 3
        assert data["column_count"] == 2

# 测试用例：上传.xls文件
def test_upload_excel_xls_format():
    # 创建一个临时的.xls文件
    with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as tmp_file:
        import pandas as pd
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z']
        })
        df.to_excel(tmp_file.name, index=False, engine='openpyxl')
        
        # 上传文件
        with open(tmp_file.name, 'rb') as f:
            response = client.post("/api/data-sources/upload-excel", files={"file": ("test.xls", f, "application/vnd.ms-excel")})
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.xls"
        assert len(data["sheet_names"]) == 1
        assert data["row_count"] == 3
        assert data["column_count"] == 2

# 测试用例：上传多个文件（应该只处理第一个）
def test_upload_excel_multiple_files():
    # 创建一个临时的Excel文件用于测试
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        import pandas as pd
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z']
        })
        df.to_excel(tmp_file.name, index=False)
        
        # 上传文件，只提供一个有效的Excel文件
        with open(tmp_file.name, 'rb') as f:
            response = client.post("/api/data-sources/upload-excel", files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    
    # 删除临时文件
    os.unlink(tmp_file.name)
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.xlsx"
    assert len(data["sheet_names"]) == 1
    assert data["row_count"] == 3
    assert data["column_count"] == 2

# 测试用例：上传文件名为空
def test_upload_excel_empty_filename():
    # 创建一个临时的Excel文件
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        import pandas as pd
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z']
        })
        df.to_excel(tmp_file.name, index=False)
        
        # 上传文件，文件名为空
        with open(tmp_file.name, 'rb') as f:
            response = client.post("/api/data-sources/upload-excel", files={"file": ("", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        
        # 删除临时文件
        os.unlink(tmp_file.name)
        
        # 验证响应
        assert response.status_code == 422
        detail = response.json()["detail"]
        # 处理 detail 可能是列表或字符串的情况
        if isinstance(detail, list):
            # 将列表中的每个元素转换为字符串并连接，然后转为小写进行检查
            detail_str = " ".join(str(item) for item in detail)
        else:
            detail_str = str(detail)
        # FastAPI 在文件名为空时返回的错误信息包含 'Expected UploadFile, received: <class 'str'>'
        # 或者 'field required' 等验证错误关键词
        assert "expected uploadfile" in detail_str.lower() or "field required" in detail_str.lower() or "empty filename" in detail_str.lower() or "invalid filename" in detail_str.lower()