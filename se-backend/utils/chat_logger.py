"""
聊天记录保存工具类

提供聊天记录持久化功能，支持按时间戳格式保存文件
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from langchain_core.messages.base import BaseMessage
from utils.unified_logger import get_logger


class ChatLogger:
    """聊天记录保存器"""
    
    def __init__(self, log_path: str = "logs/chat_logs"):
        """
        初始化聊天记录保存器
        
        Args:
            log_path: 聊天记录保存路径
        """
        self.log_path = log_path
        self.logger = get_logger(__name__)
        
        # 确保目录存在
        os.makedirs(self.log_path, exist_ok=True)
        self.logger.info(f"聊天记录保存路径: {self.log_path}")
    
    def save_chat_log(self, messages: List[BaseMessage], conversation_id: str = None) -> str:
        """
        保存聊天记录到文件
        
        Args:
            messages: 聊天消息列表
            conversation_id: 会话ID，如果提供则包含在文件名中
            
        Returns:
            str: 保存的文件路径
        """
        try:
            # 生成文件名：yyyymmddHHmmss格式
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            if conversation_id:
                filename = f"chat_{conversation_id}_{timestamp}.json"
            else:
                filename = f"chat_{timestamp}.json"
            
            file_path = os.path.join(self.log_path, filename)
            
            # 转换消息为可序列化的格式
            serializable_messages = self._serialize_messages(messages)
            
            # 构建聊天记录数据
            chat_log = {
                "conversation_id": conversation_id,
                "timestamp": timestamp,
                "created_at": datetime.now().isoformat(),
                "message_count": len(messages),
                "messages": serializable_messages
            }
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(chat_log, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"聊天记录已保存到: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"保存聊天记录失败: {str(e)}")
            raise
    
    def _serialize_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """
        将消息对象序列化为可保存的格式
        
        Args:
            messages: 消息列表
            
        Returns:
            List[Dict]: 序列化后的消息列表
        """
        serialized = []
        
        for message in messages:
            message_data = {
                "type": message.__class__.__name__,
                "content": message.content,
                "timestamp": datetime.now().isoformat()
            }
            
            # 添加额外的属性（如果存在）
            if hasattr(message, 'additional_kwargs'):
                message_data["additional_kwargs"] = message.additional_kwargs
            
            serialized.append(message_data)
        
        return serialized
    
    def load_chat_log(self, file_path: str) -> Dict[str, Any]:
        """
        加载聊天记录文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 聊天记录数据
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载聊天记录失败: {str(e)}")
            raise
    
    def list_chat_logs(self, conversation_id: str = None) -> List[str]:
        """
        列出聊天记录文件
        
        Args:
            conversation_id: 可选的会话ID过滤
            
        Returns:
            List[str]: 文件路径列表
        """
        try:
            files = []
            for filename in os.listdir(self.log_path):
                if filename.endswith('.json'):
                    if conversation_id and conversation_id not in filename:
                        continue
                    files.append(os.path.join(self.log_path, filename))
            
            # 按创建时间排序（最新的在前）
            files.sort(key=lambda x: os.path.getctime(x), reverse=True)
            return files
            
        except Exception as e:
            self.logger.error(f"列出聊天记录失败: {str(e)}")
            return []
