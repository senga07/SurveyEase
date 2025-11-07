from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """应用配置类 - 使用Pydantic Settings管理配置"""
    
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
    
    # 聊天记录保存配置
    chat_log_path: str = "logs/chat_logs"
    
    # Redis 配置
    # 单机模式配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    
    # 集群模式配置（优先使用集群模式）
    redis_cluster_nodes: str = ""  # 集群节点列表，逗号分隔，如: host1:port1,host2:port2
    redis_cluster_username: str = ""  # 集群用户名
    redis_cluster_password: str = ""  # 集群密码
    redis_cluster_timeout: int = 3000  # 超时时间（毫秒）
    
    # 连接池配置
    redis_pool_max_active: int = 8  # 最大活跃连接数
    redis_pool_max_wait: int = 8  # 最大等待时间（秒）
    redis_pool_max_idle: int = -1  # 最大空闲连接数（-1 表示无限制）
    redis_pool_min_idle: int = 0  # 最小空闲连接数
    
    # 通用配置
    redis_key_prefix: str
    redis_ttl: int
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings():
    return Settings()
