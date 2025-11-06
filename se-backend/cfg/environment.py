"""环境配置管理"""
from enum import Enum
from typing import Optional
import os


class Environment(str, Enum):
    """环境枚举"""
    LOCAL = "local"      # 本地开发环境
    TEST = "test"        # 测试环境
    PROD = "prod"        # 生产环境


def get_environment() -> Environment:
    """
    获取当前环境
    
    从环境变量 ENV 读取，默认为 LOCAL
    """
    env_str = os.getenv("ENV", "local")
    env_str = env_str.lower()
    
    try:
        return Environment(env_str)
    except ValueError:
        # 如果环境变量值不匹配，默认使用本地环境
        return Environment.LOCAL


def get_env_file(env: Optional[Environment] = None) -> str:
    """
    根据环境获取对应的 .env 文件路径
    
    Args:
        env: 环境枚举，如果为None则从环境变量获取
        
    Returns:
        .env 文件路径
    """
    if env is None:
        env = get_environment()
    
    # 根据环境返回对应的 .env 文件
    env_files = {
        Environment.LOCAL: ".env.local",
        Environment.TEST: ".env.test",
        Environment.PROD: ".env.prod",
    }
    
    return env_files.get(env, ".env.local")

