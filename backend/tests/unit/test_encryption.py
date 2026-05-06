"""
密码加密工具单元测试

测试加密和解密功能的正确性、可逆性和异常处理
"""

import os
import sys
import pytest
from unittest.mock import patch
from unittest import TestCase

# 将backend目录的父目录添加到Python路径，以便正确导入src模块
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

from src.utils.encryption import encrypt_password, decrypt_password, EncryptionError, KeyNotFoundError, EncryptionFailedError, DecryptionFailedError
import base64

class TestEncryption(TestCase):
    """加密工具测试类"""
    
    def test_encrypt_password(self):
        """测试密码加密功能"""
        password = "my_secret_password123"
        encrypted = encrypt_password(password)
        
        # 验证返回值是字符串且非空
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        
        # 验证加密结果不是原始密码
        assert encrypted != password
        
        # 验证加密结果是base64编码
        try:
            base64.b64decode(encrypted.encode('utf-8'))
        except Exception:
            pytest.fail("加密结果不是有效的base64编码")
    
    def test_decrypt_password(self):
        """测试密码解密功能"""
        # 临时设置一个已知的密钥用于测试
        test_key = "7yqkTlsSpPQIV4MD3krXKfQXP2K9nPBiywuVquHcslk="
        original_key = os.environ.get('ENCRYPTION_KEY')
        os.environ['ENCRYPTION_KEY'] = test_key
        
        try:
            password = "my_secret_password123"
            encrypted = encrypt_password(password)
            decrypted = decrypt_password(encrypted)
            
            # 验证解密结果与原始密码一致
            assert decrypted == password
        finally:
            # 恢复原始环境变量
            if original_key is not None:
                os.environ['ENCRYPTION_KEY'] = original_key
            else:
                os.environ.pop('ENCRYPTION_KEY', None)
    
    def test_encrypt_decrypt_roundtrip(self):
        """测试加密解密往返一致性"""
        # 临时设置一个已知的密钥用于测试
        test_key = "7yqkTlsSpPQIV4MD3krXKfQXP2K9nPBiywuVquHcslk="
        original_key = os.environ.get('ENCRYPTION_KEY')
        os.environ['ENCRYPTION_KEY'] = test_key
        
        try:
            test_passwords = [
                "",
                "a",
                "password123",
                "特殊字符!@#$%^&*()_+-=[]{}|;:,.<>?",
                "中文密码测试",
                "a" * 1000,  # 长密码
            ]
            
            for password in test_passwords:
                with self.subTest(password=password):
                    encrypted = encrypt_password(password)
                    decrypted = decrypt_password(encrypted)
                    assert decrypted == password, f"密码 '{password}' 加密解密后不一致"
        finally:
            # 恢复原始环境变量
            if original_key is not None:
                os.environ['ENCRYPTION_KEY'] = original_key
            else:
                os.environ.pop('ENCRYPTION_KEY', None)
    
    def test_empty_password(self):
        """测试空密码处理"""
        # 临时设置一个已知的密钥用于测试
        test_key = "7yqkTlsSpPQIV4MD3krXKfQXP2K9nPBiywuVquHcslk="
        original_key = os.environ.get('ENCRYPTION_KEY')
        os.environ['ENCRYPTION_KEY'] = test_key
        
        try:
            # 测试空字符串加密
            encrypted = encrypt_password("")
            assert isinstance(encrypted, str)
            assert len(encrypted) > 0
            
            # 测试空字符串解密
            decrypted = decrypt_password(encrypted)
            assert decrypted == ""
        finally:
            # 恢复原始环境变量
            if original_key is not None:
                os.environ['ENCRYPTION_KEY'] = original_key
            else:
                os.environ.pop('ENCRYPTION_KEY', None)
    
    def test_invalid_encrypted_data(self):
        """测试无效加密数据处理"""
        # 临时设置一个已知的密钥用于测试
        test_key = "7yqkTlsSpPQIV4MD3krXKfQXP2K9nPBiywuVquHcslk="
        original_key = os.environ.get('ENCRYPTION_KEY')
        os.environ['ENCRYPTION_KEY'] = test_key
        
        try:
            # 测试无效的base64数据
            invalid_b64 = "this_is_not_base64"
            with pytest.raises(DecryptionFailedError):
                decrypt_password(invalid_b64)
            
            # 测试无效的加密数据（正确的base64但不是加密数据）
            valid_b64 = base64.b64encode(b"not encrypted data").decode('utf-8')
            with pytest.raises(DecryptionFailedError):
                decrypt_password(valid_b64)
            
            # 测试空字符串
            with pytest.raises(DecryptionFailedError):
                decrypt_password("")
            
            # 测试None值
            with pytest.raises(DecryptionFailedError):
                decrypt_password(None)
        finally:
            # 恢复原始环境变量
            if original_key is not None:
                os.environ['ENCRYPTION_KEY'] = original_key
            else:
                os.environ.pop('ENCRYPTION_KEY', None)
    
    def test_missing_encryption_key(self):
        """测试密钥不存在的情况"""
        # 临时清除ENCRYPTION_KEY环境变量
        original_key = os.environ.get('ENCRYPTION_KEY')
        if 'ENCRYPTION_KEY' in os.environ:
            del os.environ['ENCRYPTION_KEY']
        
        try:
            # 测试加密时密钥不存在 - 应该生成新密钥而不是抛出异常
            encrypted = encrypt_password("test_password")
            assert isinstance(encrypted, str)
            assert len(encrypted) > 0
            
            # 测试解密时密钥不存在 - 应该生成新密钥而不是抛出异常
            decrypted = decrypt_password(encrypted)
            assert decrypted == "test_password"
            
        finally:
            # 恢复原始环境变量
            if original_key is not None:
                os.environ['ENCRYPTION_KEY'] = original_key
    
    def test_invalid_input_types(self):
        """测试无效输入类型"""
        # 测试非字符串输入
        with pytest.raises(EncryptionFailedError):
            encrypt_password(None)
            
        with pytest.raises(EncryptionFailedError):
            encrypt_password(123)
            
        with pytest.raises(DecryptionFailedError):
            decrypt_password(None)
            
        with pytest.raises(DecryptionFailedError):
            decrypt_password(123)
    
    def test_encryption_key_validation(self):
        """测试密钥验证"""
        # 临时设置一个无效的密钥
        original_key = os.environ.get('ENCRYPTION_KEY')
        try:
            # 设置一个无效的密钥（不是base64编码的Fernet密钥）
            os.environ['ENCRYPTION_KEY'] = "invalid_key"
            
            # 测试加密时无效密钥
            with pytest.raises(EncryptionFailedError):
                encrypt_password("test_password")
                
            # 测试解密时无效密钥
            with pytest.raises(DecryptionFailedError):
                decrypt_password("some_encrypted_data")
                
        finally:
            # 恢复原始环境变量
            if original_key is not None:
                os.environ['ENCRYPTION_KEY'] = original_key
            else:
                os.environ.pop('ENCRYPTION_KEY', None)