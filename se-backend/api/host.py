from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid
from database import get_db
from database.models import AIHost
from utils.unified_logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class HostBase(BaseModel):
    """主持人基础模型"""
    name: str
    role: str


class HostCreate(HostBase):
    """创建主持人请求模型"""
    pass


class HostUpdate(HostBase):
    """更新主持人请求模型"""
    pass


class HostResponse(HostBase):
    """主持人响应模型"""
    id: str
    create_datetime: datetime
    update_datetime: datetime
    
    class Config:
        from_attributes = True


async def get_host_by_id_from_db(host_id: str, db: AsyncSession) -> Optional[AIHost]:
    """从数据库获取主持人"""
    try:
        result = await db.execute(
            select(AIHost).where(
                and_(
                    AIHost.id == host_id,
                    AIHost.is_deleted == 0
                )
            )
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"从数据库获取主持人失败: {str(e)}")
        raise


async def check_host_name_exists(name: str, exclude_id: Optional[str] = None, db: AsyncSession = None) -> bool:
    """检查主持人名称是否已存在"""
    try:
        query = select(AIHost).where(
            and_(
                AIHost.name == name,
                AIHost.is_deleted == 0
            )
        )
        if exclude_id:
            query = query.where(AIHost.id != exclude_id)
        
        result = await db.execute(query)
        host = result.scalar_one_or_none()
        return host is not None
    except Exception as e:
        logger.error(f"检查主持人名称是否存在失败: {str(e)}")
        raise


@router.get("/hosts", response_model=List[HostResponse])
async def get_hosts(db: AsyncSession = Depends(get_db)):
    """获取主持人配置列表"""
    try:
        result = await db.execute(
            select(AIHost).where(AIHost.is_deleted == 0).order_by(AIHost.create_datetime.desc())
        )
        hosts = result.scalars().all()
        return [HostResponse.model_validate(host) for host in hosts]
    except Exception as e:
        logger.error(f"获取主持人配置列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取主持人配置列表失败")


@router.get("/hosts/{host_id}", response_model=HostResponse)
async def get_host_by_id(host_id: str, db: AsyncSession = Depends(get_db)):
    """根据ID获取单个主持人配置"""
    try:
        host = await get_host_by_id_from_db(host_id, db)
        if not host:
            raise HTTPException(status_code=404, detail=f"主持人ID {host_id} 未找到")
        return HostResponse.model_validate(host)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取主持人配置失败")


@router.post("/hosts", response_model=dict)
async def create_host(host: HostCreate, db: AsyncSession = Depends(get_db)):
    """创建新的主持人配置"""
    try:
        # 验证主持人配置内容
        if not host.name.strip():
            raise HTTPException(status_code=400, detail="主持人名称不能为空")
        
        if not host.role.strip():
            raise HTTPException(status_code=400, detail="主持人角色不能为空")
        
        # 检查名称是否重复
        if await check_host_name_exists(host.name, db=db):
            raise HTTPException(status_code=400, detail="主持人名称已存在")
        
        # 生成新的主持人ID
        host_id = str(uuid.uuid4())
        
        # 创建新主持人记录
        new_host = AIHost(
            id=host_id,
            name=host.name.strip(),
            role=host.role.strip(),
            is_deleted=0
        )
        
        db.add(new_host)
        await db.commit()
        await db.refresh(new_host)
        
        logger.info(f"创建主持人配置成功: {host_id}")
        return {"message": "主持人配置创建成功", "host_id": host_id}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"创建主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建主持人配置失败")


@router.put("/hosts/{host_id}", response_model=dict)
async def update_host_by_id(host_id: str, host: HostUpdate, db: AsyncSession = Depends(get_db)):
    """根据ID更新单个主持人配置"""
    try:
        # 验证主持人配置内容
        if not host.name.strip():
            raise HTTPException(status_code=400, detail="主持人名称不能为空")
        
        if not host.role.strip():
            raise HTTPException(status_code=400, detail="主持人角色不能为空")
        
        # 检查主持人是否存在
        existing_host = await get_host_by_id_from_db(host_id, db)
        if not existing_host:
            raise HTTPException(status_code=404, detail="主持人配置未找到")
        
        # 检查名称是否重复（排除当前主持人）
        if await check_host_name_exists(host.name, exclude_id=host_id, db=db):
            raise HTTPException(status_code=400, detail="主持人名称已存在")
        
        # 更新主持人配置
        existing_host.name = host.name.strip()
        existing_host.role = host.role.strip()
        
        await db.commit()
        await db.refresh(existing_host)
        
        logger.info(f"更新主持人配置成功: {host_id}")
        return {"message": "主持人配置更新成功"}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新主持人配置失败")


@router.delete("/hosts/{host_id}", response_model=dict)
async def delete_host_by_id(host_id: str, db: AsyncSession = Depends(get_db)):
    """根据ID删除单个主持人配置（软删除）"""
    try:
        # 检查主持人是否存在
        host = await get_host_by_id_from_db(host_id, db)
        if not host:
            raise HTTPException(status_code=404, detail="主持人配置未找到")
        
        # 软删除：设置 is_deleted = 1
        host.is_deleted = 1
        
        await db.commit()
        
        logger.info(f"删除主持人配置成功: {host_id}")
        return {"message": "主持人配置删除成功"}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除主持人配置失败")
