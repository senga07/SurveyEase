"""MySQL数据库连接管理"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from urllib.parse import quote_plus
from typing import AsyncGenerator
from cfg.setting import get_settings
from utils.unified_logger import get_logger

logger = get_logger(__name__)

# SQLAlchemy Base类，用于定义数据模型
Base = declarative_base()

# 全局数据库引擎和会话工厂
_engine = None
_async_session_maker = None


class Database:
    """数据库连接管理类"""
    
    @staticmethod
    def get_connection_url() -> str:
        """构建MySQL连接URL"""
        settings = get_settings()
        
        # URL编码用户名和密码，避免特殊字符导致连接失败
        username = quote_plus(settings.mysql_username)
        password = quote_plus(settings.mysql_password)
        database = quote_plus(settings.mysql_database)
        
        # 构建连接字符串
        # aiomysql格式: mysql+aiomysql://user:password@host:port/database
        url = (
            f"mysql+aiomysql://{username}:{password}"
            f"@{settings.mysql_host}:{settings.mysql_port}/{database}"
        )
        
        return url
    
    @staticmethod
    def get_connect_args():
        """获取连接参数"""
        settings = get_settings()
        connect_args = {
            "charset": settings.mysql_charset,
        }
        
        if not settings.mysql_use_ssl:
            connect_args["ssl"] = False
        
        return connect_args
    
    @staticmethod
    async def init_connection():
        """初始化数据库连接"""
        global _engine, _async_session_maker
        
        try:
            settings = get_settings()
            connection_url = Database.get_connection_url()
            connect_args = Database.get_connect_args()
            
            logger.info(f"正在连接数据库: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}")
            
            # 创建异步引擎
            # 注意：异步引擎会自动使用 AsyncAdaptedQueuePool，不需要指定 poolclass
            _engine = create_async_engine(
                connection_url,
                pool_size=settings.mysql_pool_size,
                pool_recycle=settings.mysql_pool_recycle,
                pool_pre_ping=True,  # 连接前检查连接是否有效
                echo=False,  # 设置为True可以查看SQL语句
                connect_args=connect_args,
            )
            
            # 创建异步会话工厂
            _async_session_maker = async_sessionmaker(
                _engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            
            logger.info(f"MySQL数据库连接初始化成功: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}")
            
            # 测试连接
            async with _engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info("MySQL数据库连接测试成功")
            
        except Exception as e:
            logger.error(f"MySQL数据库连接初始化失败: {str(e)}")
            raise
    
    @staticmethod
    async def close_connection():
        """关闭数据库连接"""
        global _engine, _async_session_maker
        
        try:
            if _engine:
                await _engine.dispose()
                _engine = None
                _async_session_maker = None
                logger.info("MySQL数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭MySQL数据库连接失败: {str(e)}")
    
# 便捷函数
async def init_db():
    """初始化数据库（便捷函数）"""
    await Database.init_connection()


async def close_db():
    """关闭数据库（便捷函数）"""
    await Database.close_connection()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（便捷函数，用于依赖注入）"""
    if _async_session_maker is None:
        raise RuntimeError("数据库连接未初始化，请先调用 init_connection()")
    
    async with _async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话错误: {str(e)}")
            raise
        finally:
            await session.close()

