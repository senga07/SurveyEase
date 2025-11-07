"""
Redis Checkpointer - 支持分布式的状态持久化

使用 Redis 作为 LangGraph 的检查点存储后端，支持多实例分布式部署
"""
import asyncio
import pickle
import types
from collections import namedtuple
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Tuple, Union, cast

import redis
from redis.cluster import RedisCluster
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata
from langgraph.checkpoint.serde.base import SerializerProtocol

from utils.custom_serializer import CustomSerializer
from utils.unified_logger import get_logger

# 定义命名元组用于返回检查点、元数据和配置
CheckpointTuple = namedtuple('CheckpointTuple', ['checkpoint', 'metadata', 'config', 'parent_config', 'pending_writes'])


class RedisCheckpointer(BaseCheckpointSaver):
    """基于 Redis 的检查点保存器，支持分布式部署"""
    
    def __init__(self, redis_client: Union[redis.Redis, RedisCluster], key_prefix: str,
                 serde: Optional[SerializerProtocol] = None, ttl: Optional[int] = None) -> None:
        """
        初始化 Redis Checkpointer
        
        Args:
            redis_client: Redis 客户端实例（支持单机和集群模式）
            serde: 序列化器，默认使用 CustomSerializer
            key_prefix: Redis key 前缀
            ttl: 数据过期时间（秒），None 表示不过期
        """
        super().__init__(serde=serde)
        self.redis_client = redis_client
        self.serde = serde or CustomSerializer()
        self.key_prefix = key_prefix
        self.ttl = ttl
        self.logger = get_logger(__name__)
        
        # 测试 Redis 连接
        try:
            if isinstance(redis_client, RedisCluster):
                # 集群模式下，ping 可能需要在特定节点上执行
                # 先不测试，让它在实际使用时再连接
                self.logger.info("Redis checkpointer 初始化成功（集群模式）")
            else:
                self.redis_client.ping()
                self.logger.info("Redis checkpointer 初始化成功（单机模式）")
        except Exception as e:
            self.logger.warning(f"Redis ping 测试失败，但继续使用: {e}")
            # 不抛出异常，允许继续使用
    
    def _get_thread_key(self, thread_id: str) -> str:
        """获取线程的 Redis key"""
        return f"{self.key_prefix}thread:{thread_id}"
    
    def _get_checkpoint_key(self, thread_id: str, checkpoint_id: str) -> str:
        """获取检查点的 Redis key"""
        return f"{self.key_prefix}checkpoint:{thread_id}:{checkpoint_id}"
    
    def _get_checkpoint_list_key(self, thread_id: str) -> str:
        """获取检查点列表的 Redis key"""
        return f"{self.key_prefix}list:{thread_id}"
    
    def _scan_keys(self, pattern: str) -> List[str]:
        """
        使用 SCAN 命令扫描匹配模式的 key
        
        Args:
            pattern: 匹配模式，如 "prefix:*"
            
        Returns:
            匹配的 key 列表
        """
        keys = []
        try:
            if isinstance(self.redis_client, RedisCluster):
                # 集群模式：需要在每个主节点上扫描
                try:
                    # 尝试使用 get_primaries() 方法（redis-py 3.x+）
                    nodes = self.redis_client.get_primaries()
                except AttributeError:
                    # 如果不存在，尝试使用 get_nodes() 方法
                    try:
                        nodes = self.redis_client.get_nodes()
                    except AttributeError:
                        # 如果都不存在，使用默认方法
                        nodes = []
                        self.logger.warning("无法获取 Redis 集群节点，跳过 SCAN 扫描")
                        return keys
                
                for node in nodes:
                    cursor = 0
                    while True:
                        try:
                            cursor, batch_keys = node.scan(cursor, match=pattern, count=100)
                            if batch_keys:
                                for key in batch_keys:
                                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                                    if key_str not in keys:
                                        keys.append(key_str)
                            if cursor == 0:
                                break
                        except Exception as e:
                            self.logger.debug(f"在节点 {node} 上扫描失败: {e}")
                            break
            else:
                # 单机模式
                cursor = 0
                while True:
                    cursor, batch_keys = self.redis_client.scan(cursor, match=pattern, count=100)
                    if batch_keys:
                        for key in batch_keys:
                            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                            if key_str not in keys:
                                keys.append(key_str)
                    if cursor == 0:
                        break
        except Exception as e:
            self.logger.debug(f"扫描 key 模式 {pattern} 失败: {e}")
        return keys
    
    def clear_thread_state(self, thread_id: str) -> None:
        """
        清除指定 thread_id 的所有 Redis 状态
        
        使用模式匹配（SCAN）来查找所有相关的 key，确保清除完整
        
        Args:
            thread_id: 要清除的线程 ID
        """
        try:
            deleted_keys = []
            
            # 方法1: 从检查点列表中获取检查点 ID 并删除
            list_key = self._get_checkpoint_list_key(thread_id)
            try:
                checkpoints = self.redis_client.zrange(list_key, 0, -1)
                for checkpoint_id_bytes in checkpoints:
                    checkpoint_id = checkpoint_id_bytes.decode('utf-8') if isinstance(checkpoint_id_bytes, bytes) else checkpoint_id_bytes
                    checkpoint_key = self._get_checkpoint_key(thread_id, checkpoint_id)
                    if self.redis_client.delete(checkpoint_key):
                        deleted_keys.append(checkpoint_key)
            except Exception as e:
                self.logger.debug(f"从检查点列表获取检查点失败: {e}")
            
            # 方法2: 使用 SCAN 模式匹配查找所有相关的 key（更可靠）
            # 匹配模式: {key_prefix}checkpoint:{thread_id}:*
            checkpoint_pattern = f"{self.key_prefix}checkpoint:{thread_id}:*"
            scan_keys = self._scan_keys(checkpoint_pattern)
            for key in scan_keys:
                if key not in deleted_keys and self.redis_client.delete(key):
                    deleted_keys.append(key)
            
            # 删除检查点列表
            if self.redis_client.delete(list_key):
                deleted_keys.append(list_key)
            
            # 删除线程信息
            thread_key = self._get_thread_key(thread_id)
            if self.redis_client.delete(thread_key):
                deleted_keys.append(thread_key)
            
            # 也尝试使用 SCAN 查找其他可能的 key（如 list 和 thread），确保没有遗漏
            for pattern in [
                f"{self.key_prefix}list:{thread_id}",
                f"{self.key_prefix}thread:{thread_id}"
            ]:
                scan_keys = self._scan_keys(pattern)
                for key in scan_keys:
                    if key not in deleted_keys and self.redis_client.delete(key):
                        deleted_keys.append(key)
            
            self.logger.info(f"[Clear State] 已清除 thread_id: {thread_id} 的所有 Redis 状态，共删除 {len(deleted_keys)} 个 key")
            if deleted_keys:
                self.logger.debug(f"删除的 key 列表: {deleted_keys[:10]}...")  # 只记录前10个
            
        except Exception as e:
            self.logger.error(f"清除 thread_id: {thread_id} 的 Redis 状态失败: {e}")
            raise
    
    def _clean_for_serialization(self, obj: Any) -> Any:
        """
        清理对象，移除不可序列化的部分（如事件循环、函数、Future等）
        
        Args:
            obj: 要清理的对象
            
        Returns:
            清理后的可序列化对象
        """
        
        # 基本类型直接返回
        if obj is None or isinstance(obj, (str, int, float, bool, bytes)):
            return obj
        
        # 字典：递归清理每个值
        if isinstance(obj, dict):
            cleaned = {}
            for key, value in obj.items():
                # 跳过不可序列化的键
                if isinstance(key, (str, int, float, bool)):
                    try:
                        cleaned_value = self._clean_for_serialization(value)
                        # 如果清理后是 None 且原值不是 None，说明是不可序列化的对象，跳过
                        # 但如果原值是基本类型（str, int, float, bool），应该保留
                        if cleaned_value is not None:
                            cleaned[key] = cleaned_value
                        elif value is None:
                            # 原值就是 None，保留
                            cleaned[key] = None
                        elif isinstance(value, (str, int, float, bool, bytes)):
                            # 基本类型清理后变成 None 是不正常的，保留原值
                            cleaned[key] = value
                        # 否则跳过（不可序列化的对象）
                    except Exception as e:
                        # 如果清理过程中出错，尝试保留原值（如果是基本类型）
                        if isinstance(value, (str, int, float, bool, bytes, type(None))):
                            cleaned[key] = value
                        else:
                            # 如果清理失败且不是基本类型，记录警告但跳过
                            self.logger.debug(f"清理字段 {key} 时出错: {e}，跳过该字段")
                        continue
            return cleaned
        
        # 列表/元组：递归清理每个元素
        if isinstance(obj, (list, tuple)):
            cleaned_list = []
            for item in obj:
                try:
                    cleaned_item = self._clean_for_serialization(item)
                    # 如果清理后是 None 且原值不是 None，说明是不可序列化的对象，跳过
                    if cleaned_item is not None or item is None:
                        cleaned_list.append(cleaned_item)
                except Exception:
                    # 如果清理过程中出错，跳过这个元素
                    continue
            return cleaned_list if isinstance(obj, list) else tuple(cleaned_list)
        
        # 检测并移除所有异步相关和不可序列化的对象
        obj_type = type(obj)
        obj_type_name = obj_type.__name__
        obj_module = getattr(obj_type, '__module__', '')
        
        # 检查是否是异步相关对象
        if (obj_module.startswith('asyncio') or 
            obj_module.startswith('_asyncio') or
            obj_type_name in ('Loop', 'uvloop.loop.Loop', 'EventLoop', 'Future', '_Future', 'Task', '_Task') or
            isinstance(obj, (asyncio.AbstractEventLoop, 
                            asyncio.Future, 
                            asyncio.Task,
                            types.FunctionType, 
                            types.MethodType, 
                            types.BuiltinFunctionType, 
                            types.CoroutineType,
                            types.GeneratorType))):
            return None
        
        # 对于其他对象，尝试转换为字典
        if hasattr(obj, '__dict__'):
            try:
                obj_dict = {}
                for key, value in obj.__dict__.items():
                    # 跳过不可序列化的属性
                    if not self._is_unserializable(value):
                        try:
                            obj_dict[key] = self._clean_for_serialization(value)
                        except Exception:
                            # 如果清理失败，跳过这个属性
                            continue
                return obj_dict
            except Exception:
                # 如果转换失败，尝试返回字符串表示
                try:
                    return str(obj)
                except Exception:
                    return None
        
        # 其他情况，尝试使用序列化器处理
        try:
            pickle.dumps(obj)
            return obj
        except (TypeError, AttributeError, pickle.PicklingError):
            try:
                return str(obj)
            except Exception:
                return None
    
    def _is_unserializable(self, obj: Any) -> bool:
        """检查对象是否不可序列化"""
        
        if obj is None:
            return False
        
        obj_type = type(obj)
        obj_type_name = obj_type.__name__
        obj_module = getattr(obj_type, '__module__', '')
        
        # 检查是否是异步相关对象
        if (obj_module.startswith('asyncio') or 
            obj_module.startswith('_asyncio') or
            obj_type_name in ('Loop', 'uvloop.loop.Loop', 'EventLoop', 'Future', '_Future', 'Task', '_Task') or
            isinstance(obj, (asyncio.AbstractEventLoop, 
                            asyncio.Future, 
                            asyncio.Task,
                            types.FunctionType, 
                            types.MethodType, 
                            types.BuiltinFunctionType, 
                            types.CoroutineType,
                            types.GeneratorType))):
            return True
        
        return False
    
    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Dict[str, Any],
    ) -> Checkpoint:
        """
        保存检查点
        
        Args:
            config: 配置信息
            checkpoint: 检查点数据
            metadata: 检查点元数据
            new_versions: 新版本信息
            
        Returns:
            更新后的检查点对象（包含 id）
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        
        if not thread_id:
            raise ValueError("thread_id 必须在 config.configurable 中提供")
        
        # 生成检查点 ID（使用时间戳）
        # LangGraph 的 checkpoint 结构通常包含：
        # - id: 检查点 ID
        # - channel_values: 实际的状态数据
        # - channel_versions: 版本信息
        if isinstance(checkpoint, dict):
            checkpoint_id = checkpoint.get("id") or f"checkpoint_{int(datetime.now(timezone.utc).timestamp() * 1000000)}"
            checkpoint = {**checkpoint, "id": checkpoint_id}
        else:
            # 如果不是字典，尝试获取 id 属性
            checkpoint_id = getattr(checkpoint, "id", None) or f"checkpoint_{int(datetime.now(timezone.utc).timestamp() * 1000000)}"
            # 转换为字典格式以便序列化
            if hasattr(checkpoint, "__dict__"):
                checkpoint = {**checkpoint.__dict__, "id": checkpoint_id}
            else:
                checkpoint = {"id": checkpoint_id, "data": checkpoint}
        
        # 清理数据，移除不可序列化的对象
        cleaned_checkpoint = self._clean_for_serialization(checkpoint)
        
        cleaned_metadata = self._clean_for_serialization(metadata)
        cleaned_config = self._clean_for_serialization(config)
        cleaned_new_versions = self._clean_for_serialization(new_versions)
        
        # 序列化检查点数据
        checkpoint_data = {
            "checkpoint": cleaned_checkpoint,
            "metadata": cleaned_metadata,
            "config": cleaned_config,
            "new_versions": cleaned_new_versions,
        }
        
        try:
            # 序列化数据
            serialized_data = self.serde.dumps(checkpoint_data)  # type: ignore[attr-defined]
            
            # 保存检查点
            checkpoint_key = self._get_checkpoint_key(thread_id, checkpoint_id)
            self.redis_client.set(checkpoint_key, serialized_data, ex=self.ttl)
            
            # 将检查点 ID 添加到列表（使用有序集合维护顺序）
            list_key = self._get_checkpoint_list_key(thread_id)
            timestamp = datetime.now(timezone.utc).timestamp()
            self.redis_client.zadd(list_key, {checkpoint_id: timestamp})
            if self.ttl:
                self.redis_client.expire(list_key, self.ttl)
            
            # 更新线程的最新检查点
            thread_key = self._get_thread_key(thread_id)
            thread_data = {
                "latest_checkpoint": checkpoint_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.redis_client.hset(thread_key, mapping=thread_data)
            if self.ttl:
                self.redis_client.expire(thread_key, self.ttl)
            
            self.logger.info(f"[Checkpoint Save] 检查点已保存 - checkpoint_id: {checkpoint_id}, thread_id: {thread_id}")
            return cast(Checkpoint, checkpoint)
            
        except Exception as e:
            self.logger.error(f"保存检查点失败: {e}")
            raise
    
    def get(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        """
        获取检查点
        
        Args:
            config: 配置信息，包含 thread_id 和可选的 checkpoint_id
            
        Returns:
            检查点数据，如果不存在则返回 None
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if not thread_id:
            raise ValueError("thread_id 必须在 config.configurable 中提供")
        
        # 如果没有指定 checkpoint_id，获取最新的
        if not checkpoint_id:
            thread_key = self._get_thread_key(thread_id)
            latest = self.redis_client.hget(thread_key, "latest_checkpoint")
            if latest:
                checkpoint_id = latest.decode('utf-8') if isinstance(latest, bytes) else latest
            else:
                # 从列表中获取最新的
                list_key = self._get_checkpoint_list_key(thread_id)
                checkpoints = self.redis_client.zrevrange(list_key, 0, 0)
                if checkpoints:
                    checkpoint_id_bytes = checkpoints[0]  # type: ignore[index]
                    checkpoint_id = checkpoint_id_bytes.decode('utf-8') if isinstance(checkpoint_id_bytes, bytes) else checkpoint_id_bytes
                else:
                    return None
        
        checkpoint_key = self._get_checkpoint_key(thread_id, checkpoint_id)
        
        try:
            serialized_data = self.redis_client.get(checkpoint_key)
            if not serialized_data:
                self.logger.debug(f"[Checkpoint Get] 检查点不存在 - checkpoint_key: {checkpoint_key}")
                return None
            
            # 反序列化数据
            checkpoint_data = self.serde.loads(serialized_data)  # type: ignore[attr-defined]
            retrieved_checkpoint = checkpoint_data.get("checkpoint")
            
            self.logger.debug(f"[Checkpoint Get] 获取检查点成功 - checkpoint_id: {checkpoint_id}, thread_id: {thread_id}")
            return retrieved_checkpoint
            
        except Exception as e:
            self.logger.error(f"获取检查点失败: {e}")
            return None
    
    def list(
        self,
        config: Dict[str, Any],
        *,
        ft: dict[str, Any] | None = None,
        before: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointMetadata]:
        """
        列出检查点
        
        Args:
            config: 配置信息
            ft: 过滤条件（未使用）
            before: 在此检查点之前列出
            limit: 返回数量限制
            
        Yields:
            检查点元数据
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        
        if not thread_id:
            raise ValueError("thread_id 必须在 config.configurable 中提供")
        
        list_key = self._get_checkpoint_list_key(thread_id)
        
        try:
            # 获取检查点 ID 列表（按时间倒序）
            if before:
                # 获取 before 的时间戳
                before_score = self.redis_client.zscore(list_key, before)
                if before_score is not None:
                    checkpoints = self.redis_client.zrevrangebyscore(
                        list_key, f"({before_score}", "-inf", start=0, num=limit or 100
                    )
                else:
                    checkpoints = []
            else:
                checkpoints = self.redis_client.zrevrange(list_key, 0, limit - 1 if limit else -1)
            
            # 获取每个检查点的元数据
            for checkpoint_id_bytes in checkpoints:
                checkpoint_id = checkpoint_id_bytes.decode('utf-8') if isinstance(checkpoint_id_bytes, bytes) else checkpoint_id_bytes
                checkpoint_key = self._get_checkpoint_key(thread_id, checkpoint_id)
                
                serialized_data = self.redis_client.get(checkpoint_key)
                if serialized_data:
                    try:
                        checkpoint_data = self.serde.loads(serialized_data)  # type: ignore[attr-defined]
                        metadata = checkpoint_data.get("metadata", {})
                        yield CheckpointMetadata(
                            **metadata
                        )
                    except Exception as e:
                        self.logger.warning(f"解析检查点元数据失败 {checkpoint_id}: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"列出检查点失败: {e}")
    
    def put_writes(
        self,
        config: Dict[str, Any],
        writes: List[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """
        保存写入操作（用于并发控制）
        
        Args:
            config: 配置信息
            writes: 写入操作列表
            task_id: 任务 ID
            task_path: 任务路径（未使用）
        """
        pass
    
    def get_tuple(self, config: Dict[str, Any]) -> Optional[Tuple[Checkpoint, CheckpointMetadata]]:
        """
        获取检查点和元数据
        
        Args:
            config: 配置信息
            
        Returns:
            (检查点, 元数据) 元组，如果不存在则返回 None
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if not thread_id:
            raise ValueError("thread_id 必须在 config.configurable 中提供")
        
        # 如果没有指定 checkpoint_id，获取最新的
        if not checkpoint_id:
            thread_key = self._get_thread_key(thread_id)
            latest = self.redis_client.hget(thread_key, "latest_checkpoint")
            if latest:
                checkpoint_id = latest.decode('utf-8') if isinstance(latest, bytes) else latest
            else:
                list_key = self._get_checkpoint_list_key(thread_id)
                checkpoints = self.redis_client.zrevrange(list_key, 0, 0)
                if checkpoints:
                    checkpoint_id_bytes = checkpoints[0]  # type: ignore[index]
                    checkpoint_id = checkpoint_id_bytes.decode('utf-8') if isinstance(checkpoint_id_bytes, bytes) else checkpoint_id_bytes
                else:
                    return None
        
        checkpoint_key = self._get_checkpoint_key(thread_id, checkpoint_id)
        
        try:
            serialized_data = self.redis_client.get(checkpoint_key)
            if not serialized_data:
                return None
            
            checkpoint_data = self.serde.loads(serialized_data)  # type: ignore[attr-defined]
            retrieved_checkpoint = checkpoint_data.get("checkpoint")
            retrieved_metadata = checkpoint_data.get("metadata", {})
            retrieved_config = checkpoint_data.get("config", {})
            
            # parent_config 从 metadata 中获取，如果没有则使用 config
            parent_config = retrieved_metadata.get("parent_config") if isinstance(retrieved_metadata, dict) else retrieved_config
            
            result = CheckpointTuple(
                checkpoint=retrieved_checkpoint,
                metadata=retrieved_metadata,
                config=retrieved_config,
                parent_config=parent_config,
                pending_writes=None
            )
            return cast(Tuple[Checkpoint, CheckpointMetadata], result)
            
        except Exception as e:
            self.logger.error(f"获取检查点元组失败: {e}")
            return None
    
    # 异步方法实现
    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Dict[str, Any],
    ) -> Checkpoint:
        """异步保存检查点"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.put, config, checkpoint, metadata, new_versions)
    
    async def aget(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        """异步获取检查点"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get, config)
    
    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[Tuple[Checkpoint, CheckpointMetadata]]:
        """异步获取检查点和元数据"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_tuple, config)
    
    async def alist(
        self,
        config: Dict[str, Any],
        *,
        ft: dict[str, Any] | None = None,
        before: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointMetadata]:
        """异步列出检查点"""
        loop = asyncio.get_event_loop()
        
        def _list_sync() -> List[CheckpointMetadata]:
            return list(self.list(config, before=before, limit=limit))
        
        results = await loop.run_in_executor(None, _list_sync)  # type: ignore[arg-type]
        for item in results:
            yield item
    
    async def aput_writes(
        self,
        config: Dict[str, Any],
        writes: List[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """异步保存写入操作（用于并发控制）"""
        pass

