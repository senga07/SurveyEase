from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from .environment import Environment, get_environment, get_env_file


class Settings(BaseSettings):
    """应用配置类 - 使用Pydantic Settings管理配置"""
    
    # 环境配置
    env: Environment = Environment.LOCAL
    
    # Azure OpenAI配置
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str
    # 百炼apikey
    dashscope_api_key: str

    fast_llm: str
    
    # 服务器配置
    host: str
    port: int

    embedding: str
    
    # MySQL数据库配置
    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_username: str
    mysql_password: str
    mysql_charset: str
    mysql_use_ssl: bool
    mysql_pool_size: int
    mysql_pool_recycle: int
    
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """自定义配置源加载顺序"""
        # 先从环境变量读取，然后从.env文件读取
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


def get_settings(env: Optional[Environment] = None) -> Settings:
    """
    获取配置实例（支持缓存）
    
    Args:
        env: 环境枚举，如果为None则从环境变量获取
        
    Returns:
        Settings实例
    """
    if env is None:
        env = get_environment()
    
    # 获取对应环境的.env文件
    env_file = get_env_file(env)
    
    # 手动加载.env文件（如果存在）
    env_file_path = Path(env_file)
    if env_file_path.exists():
        load_dotenv(env_file_path, override=False)  # override=False表示环境变量优先
    
    # 创建配置实例
    # pydantic-settings会按照以下顺序加载配置：
    # 1. 传入的参数（init_settings）
    # 2. 环境变量（env_settings）- 已通过load_dotenv加载
    # 3. .env文件（dotenv_settings）- 如果model_config中指定了env_file
    settings = Settings(
        env=env,
    )
    
    return settings
