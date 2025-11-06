"""数据库模型定义"""
from sqlalchemy import Column, String, Text, Integer, DateTime, func, BigInteger, Index, UniqueConstraint
from sqlalchemy.dialects.mysql import TINYINT, JSON
from database.connection import Base


class AIHost(Base):
    """主持人表模型"""
    __tablename__ = "ai_hosts"
    __table_args__ = {"schema": "ecu_common_tool", "comment": "主持人表"}
    
    id = Column(
        String(36),
        primary_key=True,
        comment="主持人ID（UUID）"
    )
    
    name = Column(
        String(32),
        nullable=False,
        comment="主持人名称"
    )
    
    role = Column(
        Text,
        nullable=False,
        comment="主持人角色描述（包含角色、职责、提问技巧等）"
    )
    
    is_deleted = Column(
        TINYINT,
        default=0,
        nullable=False,
        comment="是否删除：1 已删除，0 正常"
    )
    
    create_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间"
    )
    
    update_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="修改时间"
    )


class AISurveyTemplate(Base):
    """调研模板表模型"""
    __tablename__ = "ai_survey_templates"
    __table_args__ = {"comment": "调研模板表"}
    
    id = Column(
        String(255),
        primary_key=True,
        comment="调研模板ID"
    )
    
    theme = Column(
        String(500),
        nullable=False,
        comment="调研主题"
    )
    
    system_prompt = Column(
        Text,
        nullable=True,
        comment="系统提示词"
    )
    
    background_knowledge = Column(
        Text,
        nullable=True,
        comment="背景知识"
    )
    
    max_turns = Column(
        Integer,
        default=5,
        nullable=True,
        comment="最大对话轮次"
    )
    
    welcome_message = Column(
        Text,
        nullable=True,
        comment="欢迎消息"
    )
    
    end_message = Column(
        Text,
        nullable=True,
        comment="结束消息"
    )
    
    host_id = Column(
        String(36),
        nullable=False,
        comment="关联的主持人ID"
    )
    
    is_deleted = Column(
        TINYINT,
        default=0,
        nullable=False,
        comment="是否删除：1 已删除，0 正常"
    )
    
    create_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间"
    )
    
    update_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="修改时间"
    )


class AISurveyTemplateStep(Base):
    """调研模板步骤表模型"""
    __tablename__ = "ai_survey_template_steps"
    __table_args__ = (
        Index('idx_step_order', 'template_id', 'step_order'),
        Index('idx_template_id', 'template_id'),
        UniqueConstraint('template_id', 'step_id', name='uk_template_step'),
        {"comment": "调研模板步骤表"}
    )
    
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="步骤记录ID"
    )
    
    template_id = Column(
        String(255),
        nullable=False,
        comment="关联的调研模板ID"
    )
    
    step_id = Column(
        Integer,
        nullable=False,
        comment="步骤ID（模板内的步骤编号）"
    )
    
    content = Column(
        Text,
        nullable=False,
        comment="步骤内容（包含目标、示例、必须信息清单等）"
    )
    
    type = Column(
        String(20),
        default='linear',
        nullable=False,
        comment="步骤类型：linear（线性）或condition（条件分支）"
    )
    
    condition_text = Column(
        Text,
        nullable=True,
        comment="条件文本（当type为condition时使用，用于判断分支）"
    )
    
    branches = Column(
        JSON,
        nullable=True,
        comment="分支列表（JSON数组，存储下一步步骤ID或\"END\"）"
    )
    
    step_order = Column(
        Integer,
        nullable=False,
        comment="步骤顺序（用于排序）"
    )
    
    is_deleted = Column(
        TINYINT,
        default=0,
        nullable=False,
        comment="是否删除：1 已删除，0 正常"
    )
    
    create_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间"
    )
    
    update_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="修改时间"
    )


class AISurveyTemplateVariable(Base):
    """调研模板变量表模型"""
    __tablename__ = "ai_survey_template_variables"
    __table_args__ = (
        Index('idx_template_id', 'template_id'),
        UniqueConstraint('template_id', 'variable_key', name='uk_template_variable'),
        {"comment": "调研模板变量表"}
    )
    
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="变量记录ID"
    )
    
    template_id = Column(
        String(255),
        nullable=False,
        comment="关联的调研模板ID"
    )
    
    variable_key = Column(
        String(100),
        nullable=False,
        comment="变量键名（如product_name、category等）"
    )
    
    variable_value = Column(
        String(500),
        nullable=False,
        comment="变量值（如\"三得利乌龙茶\"、\"无糖茶\"等）"
    )
    
    is_deleted = Column(
        TINYINT,
        default=0,
        nullable=False,
        comment="是否删除：1 已删除，0 正常"
    )
    
    create_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间"
    )
    
    update_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="修改时间"
    )


class AIConversation(Base):
    """会话记录表模型"""
    __tablename__ = "ai_conversations"
    __table_args__ = (
        Index('idx_conversation_id', 'conversation_id'),
        Index('idx_create_datetime', 'create_datetime'),
        Index('idx_template_id', 'template_id'),
        UniqueConstraint('conversation_id', name='uk_conversation_id'),
        {"comment": "会话记录表"}
    )
    
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="会话记录ID"
    )
    
    conversation_id = Column(
        String(255),
        nullable=False,
        comment="会话ID"
    )
    
    template_id = Column(
        String(255),
        nullable=False,
        comment="关联的调研模板ID"
    )
    
    timestamp = Column(
        String(14),
        nullable=False,
        comment="时间戳（yyyymmddHHmmss格式）"
    )
    
    message_count = Column(
        Integer,
        default=0,
        nullable=True,
        comment="消息总数"
    )
    
    is_deleted = Column(
        TINYINT,
        default=0,
        nullable=False,
        comment="是否删除：1 已删除，0 正常"
    )
    
    create_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间"
    )
    
    update_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="修改时间"
    )


class AIChatMessage(Base):
    """聊天消息表模型"""
    __tablename__ = "ai_chat_messages"
    __table_args__ = (
        Index('idx_conversation_id', 'conversation_id'),
        Index('idx_create_datetime', 'create_datetime'),
        Index('idx_message_order', 'conversation_id', 'message_order'),
        Index('idx_message_type', 'message_type'),
        {"comment": "聊天消息表"}
    )
    
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="消息记录ID"
    )
    
    conversation_id = Column(
        String(255),
        nullable=False,
        comment="关联的会话ID"
    )
    
    message_type = Column(
        String(50),
        nullable=False,
        comment="消息类型：HumanMessage, AIMessage, SystemMessage"
    )
    
    content = Column(
        Text,
        nullable=False,
        comment="消息内容"
    )
    
    message_order = Column(
        Integer,
        nullable=False,
        comment="消息顺序（在会话中的顺序）"
    )
    
    additional_kwargs = Column(
        JSON,
        nullable=True,
        comment="额外参数（JSON格式）"
    )
    
    is_deleted = Column(
        TINYINT,
        default=0,
        nullable=False,
        comment="是否删除：1 已删除，0 正常"
    )
    
    create_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间"
    )
    
    update_datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="修改时间"
    )

