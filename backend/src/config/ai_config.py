"""
AI模型配置管理
加载和管理AI模型的配置信息
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AIConfig:
    """AI模型配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        current_dir = Path(__file__).parent.parent.parent
        return str(current_dir / "config" / "ai_models.yml")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 替换环境变量
            config = self._substitute_env_vars(config)
            
            logger.info(f"AI config loaded from {self.config_path}")
            return config
            
        except FileNotFoundError:
            logger.warning(f"AI config file not found: {self.config_path}")
            return self._get_default_config()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing AI config file: {e}")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Unexpected error loading AI config: {e}")
            return self._get_default_config()
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """递归替换配置中的环境变量"""
        if isinstance(config, dict):
            return {key: self._substitute_env_vars(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            # 解析环境变量，支持默认值 ${VAR_NAME:-default_value}
            env_expr = config[2:-1]  # 去掉 ${ 和 }
            
            if ":-" in env_expr:
                var_name, default_value = env_expr.split(":-", 1)
                return os.getenv(var_name, default_value)
            else:
                return os.getenv(env_expr, config)
        else:
            return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置（兜底，优先读环境变量）"""
        return {
            "qwen_cloud": {
                "api_key": os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY", ""),
                "base_url": os.getenv("ALIYUN_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                "model_name": os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
                "max_tokens": 2000,
                "temperature": 0.1,
                "retry_count": 3,
                "retry_delay": 1.0
            },
            "openai_local": {
                "base_url": os.getenv("OPENAI_LOCAL_BASE_URL", "http://localhost:11434/v1"),
                "api_key": os.getenv("OPENAI_LOCAL_API_KEY", "ollama"),
                "model_name": os.getenv("OPENAI_LOCAL_MODEL", "llama2"),
                "max_tokens": 2000,
                "temperature": 0.7,
                "retry_count": 2,
                "retry_delay": 0.5
            },
            "security": {
                "cloud_data_sanitization": {
                    "enabled": True,
                    "blocked_patterns": [
                        "\\b\\d{4}-\\d{2}-\\d{2}\\b",
                        "\\b\\d+\\.\\d+\\b",
                        "'[^']*'",
                        '"[^"]*"'
                    ]
                }
            },
            "monitoring": {
                "performance_metrics": {
                    "enabled": True,
                    "response_time_threshold": 10.0
                },
                "token_usage_monitoring": {
                    "enabled": True,
                    "daily_report": True
                }
            }
        }
    
    def get_qwen_config(self) -> Dict[str, Any]:
        """获取Qwen模型配置"""
        return self.config.get("qwen_cloud", {})
    
    def get_openai_config(self) -> Dict[str, Any]:
        """获取OpenAI模型配置"""
        return self.config.get("openai_local", {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return self.config.get("security", {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        return self.config.get("monitoring", {})
    
    def is_qwen_enabled(self) -> bool:
        """检查Qwen模型是否启用"""
        qwen_config = self.get_qwen_config()
        return bool(qwen_config.get("api_key"))
    
    def is_openai_enabled(self) -> bool:
        """检查OpenAI模型是否启用"""
        openai_config = self.get_openai_config()
        return bool(openai_config.get("base_url"))
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置的有效性"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 验证Qwen配置
        qwen_config = self.get_qwen_config()
        if not qwen_config.get("api_key"):
            validation_result["errors"].append("Qwen API key is missing")
            validation_result["valid"] = False
        
        if not qwen_config.get("base_url"):
            validation_result["errors"].append("Qwen base URL is missing")
            validation_result["valid"] = False
        
        # 验证OpenAI配置
        openai_config = self.get_openai_config()
        if not openai_config.get("base_url"):
            validation_result["warnings"].append("OpenAI local base URL is missing")
        
        # 验证模型参数
        for model_name, config in [("qwen_cloud", qwen_config), ("openai_local", openai_config)]:
            max_tokens = config.get("max_tokens", 0)
            if max_tokens <= 0 or max_tokens > 32000:
                validation_result["warnings"].append(f"{model_name} max_tokens should be between 1 and 32000")
            
            temperature = config.get("temperature", 0)
            if temperature < 0 or temperature > 2:
                validation_result["warnings"].append(f"{model_name} temperature should be between 0 and 2")
        
        return validation_result
    
    def reload_config(self):
        """重新加载配置"""
        self.config = self._load_config()
        logger.info("AI config reloaded")
    
    def get_full_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self.config.copy()


# 全局配置实例
_ai_config: Optional[AIConfig] = None


def get_ai_config() -> AIConfig:
    """获取AI配置实例"""
    global _ai_config
    if _ai_config is None:
        _ai_config = AIConfig()
    return _ai_config


def init_ai_config(config_path: Optional[str] = None) -> AIConfig:
    """初始化AI配置"""
    global _ai_config
    _ai_config = AIConfig(config_path)
    return _ai_config


def validate_ai_config() -> Dict[str, Any]:
    """验证AI配置"""
    config = get_ai_config()
    return config.validate_config()


# 环境变量检查函数
def check_required_env_vars() -> Dict[str, Any]:
    """检查必需的环境变量"""
    required_vars = {
        "DASHSCOPE_API_KEY": "阿里云Qwen模型API密钥",
        "OPENAI_LOCAL_BASE_URL": "本地OpenAI模型API地址（可选）",
        "OPENAI_LOCAL_API_KEY": "本地OpenAI模型API密钥（可选）",
        "OPENAI_LOCAL_MODEL": "本地OpenAI模型名称（可选）"
    }
    
    result = {
        "all_set": True,
        "missing": [],
        "present": [],
        "optional_missing": []
    }
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            result["present"].append({
                "name": var_name,
                "description": description,
                "value": value[:10] + "..." if len(value) > 10 else value
            })
        else:
            if var_name == "DASHSCOPE_API_KEY":
                result["missing"].append({
                    "name": var_name,
                    "description": description
                })
                result["all_set"] = False
            else:
                result["optional_missing"].append({
                    "name": var_name,
                    "description": description
                })
    
    return result


if __name__ == "__main__":
    # 测试配置加载
    config = AIConfig()
    print("AI Config loaded successfully:")
    print(f"Qwen enabled: {config.is_qwen_enabled()}")
    print(f"OpenAI enabled: {config.is_openai_enabled()}")
    
    validation = config.validate_config()
    print(f"Config validation: {validation}")
    
    env_check = check_required_env_vars()
    print(f"Environment variables: {env_check}")