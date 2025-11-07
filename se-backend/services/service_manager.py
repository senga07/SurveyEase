"""
服务管理器

提供基本的服务管理功能，避免循环依赖
"""
import redis
from redis.cluster import RedisCluster, ClusterNode
from redis.connection import ConnectionPool
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
            self.redis_client = None

    
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
            
            # 初始化 Redis 连接
            self._initialize_redis(settings)
            
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
    
    def _initialize_redis(self, settings):
        """初始化 Redis 连接（支持单机和集群模式）"""
        try:
            # 优先使用集群模式
            if settings.redis_cluster_nodes:
                self.redis_client = self._create_redis_cluster(settings)
                self.logger.info(f"Redis 集群客户端创建成功: {settings.redis_cluster_nodes}")
            else:
                # 使用单机模式
                self.redis_client = self._create_redis_single(settings)
                self.logger.info(f"Redis 单机客户端创建成功: {settings.redis_host}:{settings.redis_port}")
            
            # 测试连接
            try:
                if isinstance(self.redis_client, RedisCluster):
                    # 集群模式下，尝试执行一个简单的命令来测试连接
                    # 使用 cluster_info 或直接调用 ping（RedisCluster 会处理）
                    self.redis_client.ping()
                else:
                    self.redis_client.ping()
                self.logger.info("Redis 连接测试成功")
            except Exception as ping_error:
                self.logger.warning(f"Redis ping 测试失败，但继续使用: {ping_error}")
                # 不抛出异常，允许继续使用（某些情况下 ping 可能失败但连接正常）
        except Exception as e:
            self.logger.error(f"Redis 初始化失败: {e}", exc_info=True)
            self.redis_client = None
            raise
    
    def _create_redis_cluster(self, settings):
        """创建 Redis 集群客户端"""
        # 解析集群节点 - 使用 ClusterNode 对象
        nodes = []
        for node_str in settings.redis_cluster_nodes.split(','):
            node_str = node_str.strip()
            if ':' in node_str:
                host, port = node_str.rsplit(':', 1)
                nodes.append(ClusterNode(
                    host=host.strip(),
                    port=int(port.strip())
                ))
            else:
                # 如果没有端口，使用默认端口
                nodes.append(ClusterNode(
                    host=node_str.strip(),
                    port=6379
                ))
        
        if not nodes:
            raise ValueError("Redis 集群节点列表不能为空")
        
        # 构建连接参数
        connection_kwargs = {
            "decode_responses": False,  # 保持二进制模式以支持 pickle 序列化
            "socket_connect_timeout": settings.redis_cluster_timeout / 1000,  # 转换为秒
            "socket_timeout": settings.redis_cluster_timeout / 1000,
            "retry_on_timeout": True,
        }
        
        # 添加认证信息
        if settings.redis_cluster_username:
            connection_kwargs["username"] = settings.redis_cluster_username
        if settings.redis_cluster_password:
            connection_kwargs["password"] = settings.redis_cluster_password
        
        # 创建集群客户端
        try:
            cluster = RedisCluster(
                startup_nodes=nodes,
                **connection_kwargs
            )
            return cluster
        except Exception as e:
            self.logger.error(f"创建 Redis 集群客户端失败: {e}")
            self.logger.debug(f"节点列表: {nodes}")
            self.logger.debug(f"连接参数: {connection_kwargs}")
            raise
    
    def _create_redis_single(self, settings):
        """创建 Redis 单机客户端"""
        # 创建连接池
        pool = ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password if settings.redis_password else None,
            max_connections=settings.redis_pool_max_active,
            max_connections_per_node=settings.redis_pool_max_active,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            decode_responses=False,  # 保持二进制模式以支持 pickle 序列化
        )
        
        return redis.Redis(connection_pool=pool)
    
    def get_redis_client(self):
        """获取 Redis 客户端实例"""
        if self.redis_client is None:
            raise RuntimeError("Redis 客户端未初始化，请先调用 initialize()")
        return self.redis_client


# 全局服务管理器实例
service_manager = ServiceManager()
