"""
服务管理器

提供基本的服务管理功能，避免循环依赖
"""
from cfg.setting import get_settings
from llm_provider.base import get_llm
from utils.unified_logger import get_logger
from langgraph.store.memory import InMemoryStore
from memory.embeddings import Embeddings
from langgraph.store.base import IndexConfig


class ServiceManager:
    """服务管理器 - 单例模式"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.logger = get_logger(__name__)
            self.config = None
            self.fast_llm = None
            self._initialized = True
            self.store = None

    
    def initialize(self) -> bool:
        """初始化基本服务"""
        try:
            self.logger.info("开始初始化服务管理器...")

            settings = get_settings()
            
            # 解析LLM配置
            fast_llm_provider, fast_llm_model = self._parse_llm(settings.fast_llm)
            embedding_provider, embedding_model = self._parse_llm(settings.embedding)

            self._initialize_llms(fast_llm_provider, fast_llm_model)

            embedding = Embeddings(embedding_provider, embedding_model).get_embeddings()
            self.store = InMemoryStore(index=IndexConfig(dims=1024,embed = embedding))
            self.logger.info("服务管理器初始化完成")
            return True
        except Exception as e:
            self.logger.error(f"服务初始化失败: {e}")
            return False
    
    def _parse_llm(self, llm_str: str | None) -> tuple[str | None, str | None]:
        """解析LLM字符串为(provider, model)元组"""
        if llm_str is None:
            return None, None
        try:
            llm_provider, llm_model = llm_str.split(":", 1)
            return llm_provider, llm_model
        except ValueError:
            raise ValueError(
                "Set FAST_LLM or EMBEDDING = '<llm_provider>:<llm_model>' "
                "Eg 'azure_openai:gpt-4o-mini'"
            )

    def _initialize_llms(self, fast_llm_provider: str, fast_llm_model: str):
        """初始化LLM实例"""
        try:
            # 快速LLM
            self.fast_llm = get_llm(
                llm_provider=fast_llm_provider,
                model=fast_llm_model
            ).llm

            self.logger.info("LLM实例初始化完成")
        except Exception as e:
            self.logger.error(f"LLM初始化失败: {e}")
            raise
    
    def get_llms(self):
        """获取所有LLM实例"""
        return {
            'fast_llm': self.fast_llm,
        }
    
    def get_config(self):
        """获取配置实例"""
        return get_settings()


# 全局服务管理器实例
service_manager = ServiceManager()
