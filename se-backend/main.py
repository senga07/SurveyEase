import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import argparse
from cfg.setting import get_settings
from cfg.environment import Environment, get_environment
from services.service_manager import service_manager
from utils.unified_logger import initialize_logging, get_logger
from database import init_db, close_db
import os

# 禁用 LangChain 的自动追踪
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_API_KEY"] = ""

# 解析命令行参数
parser = argparse.ArgumentParser(description="SurveyEase Backend Server")
parser.add_argument(
    "--env",
    type=str,
    choices=["local", "test", "prod"],
    default=None,
    help="运行环境: local (本地), test (测试), prod (生产). 如果未指定，将从环境变量 ENV 读取"
)
args, unknown = parser.parse_known_args()

# 如果通过命令行指定了环境，设置环境变量
if args.env:
    os.environ["ENV"] = args.env
    current_env = Environment(args.env)
else:
    current_env = get_environment()

# 初始化统一日志系统
logging_config = initialize_logging(
    log_level=20,  # INFO
    log_dir="logs",
    main_log_filename="survey_ease.log",
    enable_console=True,
    enable_file=True
)

logger = get_logger(__name__)
logger.info(f"当前运行环境: {current_env.value}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 获取当前环境的配置
    settings = get_settings(current_env)
    logger.info(f"加载配置完成，环境: {settings.env.value}")
    
    # 启动时初始化数据库连接
    logger.info("正在初始化数据库连接...")
    try:
        await init_db()
        logger.info("数据库连接初始化成功")
    except Exception as e:
        logger.error(f"数据库连接初始化失败: {str(e)}")
        raise
    
    # 启动时初始化服务
    logger.info("正在初始化服务...")
    success = service_manager.initialize()
    if not success:
        logger.error("服务初始化失败，应用可能无法正常工作")
    else:
        logger.info("服务初始化完成")

    yield

    # 关闭时清理资源
    logger.info("正在清理资源...")
    try:
        await close_db()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {str(e)}")
    logger.info("服务清理完成")


app = FastAPI(
    title="Survey Ease API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件以支持前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入API路由
from api.survey import router as survey_router
from api.template import router as template_router
from api.host import router as host_router

# 注册路由
app.include_router(survey_router, prefix="/api/survey", tags=["survey"])
app.include_router(template_router, prefix="/api/template", tags=["template"])
app.include_router(host_router, prefix="/api/host", tags=["host"])



if __name__ == "__main__":
    settings = get_settings(current_env)
    logger.info(f"启动服务器: {settings.host}:{settings.port}")
    uvicorn.run(app, port=settings.port, host=settings.host)