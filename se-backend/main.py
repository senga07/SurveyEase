import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from cfg.setting import get_settings
from services.service_manager import service_manager
from utils.unified_logger import initialize_logging, get_logger
import os

# 禁用 LangChain 的自动追踪
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_API_KEY"] = ""

# 初始化统一日志系统
logging_config = initialize_logging(
    log_level=20,  # INFO
    log_dir="logs",
    main_log_filename="survey_ease.log",
    enable_console=True,
    enable_file=True
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化服务
    logger.info("正在初始化服务...")
    success = service_manager.initialize()
    if not success:
        logger.error("服务初始化失败，应用可能无法正常工作")
    else:
        logger.info("服务初始化完成")

    yield

    # 关闭时清理资源
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

# 注册路由
app.include_router(survey_router, prefix="/api/survey", tags=["survey"])
app.include_router(template_router, prefix="/api/template", tags=["template"])



if __name__ == "__main__":
    uvicorn.run(app, port=get_settings().port, host=get_settings().host)