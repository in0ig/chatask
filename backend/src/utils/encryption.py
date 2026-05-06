"""
密码加密工具模块

使用Fernet对称加密算法对数据库密码进行加密和解密。
密钥从环境变量 ENCRYPTION_KEY 读取，如果不存在则自动生成并提示用户保存。
加密后的密码使用base64编码存储。
"""

import logging
import os
import base64
from cryptography.fernet import Fernet, InvalidToken

# 设置日志
logger = logging.getLogger(__name__)

# 缓存已加载的密钥，确保在同一个进程中使用相同的密钥
_encryption_key_cache = None
_last_env_value = None

class EncryptionError(Exception):
    """加密相关异常基类"""
    pass

class KeyNotFoundError(EncryptionError):
    """加密密钥未找到异常"""
    pass

class EncryptionFailedError(EncryptionError):
    """加密失败异常"""
    pass

class DecryptionFailedError(EncryptionError):
    """解密失败异常"""
    pass

def get_encryption_key() -> bytes:
    """
    获取加密密钥
    
    从环境变量 ENCRYPTION_KEY 读取密钥，如果不存在则生成新的密钥并提示用户保存。
    使用缓存机制确保在同一个进程中使用相同的密钥进行加密和解密。
    如果环境变量被修改，则重新加载密钥。
    
    Returns:
        bytes: 加密密钥
        
    Raises:
        KeyNotFoundError: 当环境变量 ENCRYPTION_KEY 不存在时抛出
    """
    global _encryption_key_cache, _last_env_value
    
    # 获取当前环境变量值
    current_env_value = os.getenv('ENCRYPTION_KEY')
    
    # 如果环境变量值已更改，清除缓存
    if _last_env_value != current_env_value:
        _encryption_key_cache = None
        _last_env_value = current_env_value
    
    # 如果缓存中已有密钥，直接返回
    if _encryption_key_cache is not None:
        return _encryption_key_cache
    
    if not current_env_value:
        # 生成新的密钥
        key = Fernet.generate_key()
        key_str = key.decode('utf-8')
        
        # 提示用户保存密钥
        logger.warning(
            "ENCRYPTION_KEY 环境变量未设置，已自动生成新的加密密钥。请将以下密钥添加到 .env 文件中以确保数据持久化：\n" +
            f"ENCRYPTION_KEY={key_str}\n"
        )
        _encryption_key_cache = key
        return key
    
    try:
        # 验证密钥格式
        key_bytes = current_env_value.encode('utf-8')
        # 尝试创建Fernet实例来验证密钥有效性
        Fernet(key_bytes)
        _encryption_key_cache = key_bytes
        return key_bytes
    except Exception as e:
        logger.error(f"无效的 ENCRYPTION_KEY 格式: {str(e)}")
        raise KeyNotFoundError(f"无效的 ENCRYPTION_KEY: {str(e)}")

def encrypt_password(password: str) -> str:
    """
    加密密码
    
    Args:
        password (str): 要加密的明文密码
        
    Returns:
        str: 加密后的密码（base64编码的字符串）
        
    Raises:
        EncryptionFailedError: 加密失败时抛出
        KeyNotFoundError: 密钥未设置时抛出
    """
    if not isinstance(password, str):
        raise EncryptionFailedError("密码必须是字符串类型")
    
    try:
        # 获取加密密钥
        key = get_encryption_key()
        
        # 创建Fernet加密器
        fernet = Fernet(key)
        
        # 加密密码
        encrypted_data = fernet.encrypt(password.encode('utf-8'))
        
        # 返回base64编码的字符串
        return base64.b64encode(encrypted_data).decode('utf-8')
        
    except InvalidToken as e:
        logger.error(f"加密失败 - 无效令牌: {str(e)}")
        raise EncryptionFailedError("加密失败：密钥无效或已损坏")
    except Exception as e:
        logger.error(f"加密失败: {str(e)}")
        raise EncryptionFailedError(f"加密失败: {str(e)}")

def decrypt_password(encrypted_password: str) -> str:
    """
    解密密码
    
    Args:
        encrypted_password (str): 要解密的加密密码（base64编码的字符串）
        
    Returns:
        str: 解密后的明文密码
        
    Raises:
        DecryptionFailedError: 解密失败时抛出
        KeyNotFoundError: 密钥未设置时抛出
    """
    if not isinstance(encrypted_password, str):
        raise DecryptionFailedError("加密密码必须是字符串类型")
    
    try:
        # 获取加密密钥
        key = get_encryption_key()
        
        # 创建Fernet加密器
        fernet = Fernet(key)
        
        # 解码base64
        encrypted_data = base64.b64decode(encrypted_password.encode('utf-8'))
        
        # 解密密码
        decrypted_data = fernet.decrypt(encrypted_data)
        
        # 返回明文密码
        return decrypted_data.decode('utf-8')
        
    except (InvalidToken, ValueError) as e:
        logger.error(f"解密失败 - 无效令牌或数据格式错误: {str(e)}")
        raise DecryptionFailedError("解密失败：数据已损坏或格式不正确")
    except Exception as e:
        logger.error(f"解密失败: {str(e)}")
        raise DecryptionFailedError(f"解密失败: {str(e)}")