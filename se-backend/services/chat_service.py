"""
聊天记录数据库服务

提供聊天记录的保存和查询功能
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from langchain_core.messages.base import BaseMessage
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.system import SystemMessage
from database.models import AIConversation, AIChatMessage
from utils.unified_logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """聊天记录服务类"""
    
    @staticmethod
    async def create_or_update_conversation(
        db: AsyncSession,
        conversation_id: str,
        template_id: str,
        message_count: int = 0
    ) -> AIConversation:
        """
        创建或更新会话记录
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            template_id: 模板ID
            message_count: 消息总数
            
        Returns:
            AIConversation: 会话记录对象
        """
        try:
            # 检查是否已存在
            stmt = select(AIConversation).where(
                and_(
                    AIConversation.conversation_id == conversation_id,
                    AIConversation.is_deleted == 0
                )
            )
            result = await db.execute(stmt)
            existing_conv = result.scalar_one_or_none()
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            if existing_conv:
                # 更新现有记录
                existing_conv.message_count = message_count
                existing_conv.timestamp = timestamp
                await db.commit()
                await db.refresh(existing_conv)
                logger.info(f"更新会话记录: {conversation_id}")
                return existing_conv
            else:
                # 创建新记录
                new_conv = AIConversation(
                    conversation_id=conversation_id,
                    template_id=template_id,
                    timestamp=timestamp,
                    message_count=message_count
                )
                db.add(new_conv)
                await db.commit()
                await db.refresh(new_conv)
                logger.info(f"创建会话记录: {conversation_id}")
                return new_conv
        except Exception as e:
            await db.rollback()
            logger.error(f"创建或更新会话记录失败: {str(e)}")
            raise
    
    @staticmethod
    async def save_message(
        db: AsyncSession,
        conversation_id: str,
        message: BaseMessage,
        message_order: int,
        additional_kwargs: Optional[Dict[str, Any]] = None
    ) -> AIChatMessage:
        """
        保存单条消息
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            message: 消息对象
            message_order: 消息顺序
            additional_kwargs: 额外参数
            
        Returns:
            AIChatMessage: 消息记录对象
        """
        try:
            # 确定消息类型
            if isinstance(message, HumanMessage):
                message_type = "HumanMessage"
            elif isinstance(message, AIMessage):
                message_type = "AIMessage"
            elif isinstance(message, SystemMessage):
                message_type = "SystemMessage"
            else:
                message_type = message.__class__.__name__
            
            # 获取消息内容
            content = message.content if hasattr(message, 'content') else str(message)
            
            # 获取额外参数
            if additional_kwargs is None and hasattr(message, 'additional_kwargs'):
                additional_kwargs = message.additional_kwargs
            
            new_message = AIChatMessage(
                conversation_id=conversation_id,
                message_type=message_type,
                content=content,
                message_order=message_order,
                additional_kwargs=additional_kwargs
            )
            db.add(new_message)
            await db.commit()
            await db.refresh(new_message)
            logger.debug(f"保存消息: {conversation_id}, order: {message_order}, type: {message_type}")
            return new_message
        except Exception as e:
            await db.rollback()
            logger.error(f"保存消息失败: {str(e)}")
            raise
    
    @staticmethod
    async def save_messages(
        db: AsyncSession,
        conversation_id: str,
        template_id: str,
        messages: List[BaseMessage]
    ) -> AIConversation:
        """
        批量保存消息并更新会话记录
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            template_id: 模板ID
            messages: 消息列表
            
        Returns:
            AIConversation: 会话记录对象
        """
        try:
            # 保存所有消息
            for order, message in enumerate(messages, start=1):
                await ChatService.save_message(
                    db=db,
                    conversation_id=conversation_id,
                    message=message,
                    message_order=order
                )
            
            # 更新或创建会话记录
            conversation = await ChatService.create_or_update_conversation(
                db=db,
                conversation_id=conversation_id,
                template_id=template_id,
                message_count=len(messages)
            )
            
            logger.info(f"批量保存消息完成: {conversation_id}, 共 {len(messages)} 条消息")
            return conversation
        except Exception as e:
            await db.rollback()
            logger.error(f"批量保存消息失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_conversation_by_id(
        db: AsyncSession,
        conversation_id: str
    ) -> Optional[AIConversation]:
        """
        根据会话ID获取会话记录
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            
        Returns:
            Optional[AIConversation]: 会话记录对象，如果不存在则返回None
        """
        try:
            stmt = select(AIConversation).where(
                and_(
                    AIConversation.conversation_id == conversation_id,
                    AIConversation.is_deleted == 0
                )
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取会话记录失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_messages_by_conversation_id(
        db: AsyncSession,
        conversation_id: str,
        include_system: bool = False
    ) -> List[AIChatMessage]:
        """
        获取会话的所有消息
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            include_system: 是否包含系统消息
            
        Returns:
            List[AIChatMessage]: 消息列表，按顺序排序
        """
        try:
            conditions = [
                AIChatMessage.conversation_id == conversation_id,
                AIChatMessage.is_deleted == 0
            ]
            
            if not include_system:
                conditions.append(AIChatMessage.message_type != "SystemMessage")
            
            stmt = select(AIChatMessage).where(
                and_(*conditions)
            ).order_by(AIChatMessage.message_order)
            
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"获取消息列表失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_conversation_list(
        db: AsyncSession,
        template_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AIConversation]:
        """
        获取会话列表
        
        Args:
            db: 数据库会话
            template_id: 可选的模板ID过滤
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            List[AIConversation]: 会话列表，按创建时间倒序
        """
        try:
            conditions = [AIConversation.is_deleted == 0]
            
            if template_id:
                conditions.append(AIConversation.template_id == template_id)
            
            stmt = select(AIConversation).where(
                and_(*conditions)
            ).order_by(AIConversation.create_datetime.desc()).limit(limit).offset(offset)
            
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"获取会话列表失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_conversation_detail(
        db: AsyncSession,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取会话详情（包含消息列表）
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            
        Returns:
            Optional[Dict]: 会话详情，包含会话信息和消息列表
        """
        try:
            conversation = await ChatService.get_conversation_by_id(db, conversation_id)
            if not conversation:
                return None
            
            messages = await ChatService.get_messages_by_conversation_id(
                db, conversation_id, include_system=False
            )
            
            # 转换为字典格式
            message_list = []
            for msg in messages:
                message_list.append({
                    "type": msg.message_type,
                    "content": msg.content,
                    "additional_kwargs": msg.additional_kwargs,
                    "timestamp": msg.create_datetime.isoformat() if msg.create_datetime else None
                })
            
            return {
                "conversation_id": conversation.conversation_id,
                "template_id": conversation.template_id,
                "timestamp": conversation.timestamp,
                "created_at": conversation.create_datetime.isoformat() if conversation.create_datetime else None,
                "message_count": conversation.message_count,
                "messages": message_list
            }
        except Exception as e:
            logger.error(f"获取会话详情失败: {str(e)}")
            raise

