from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
import uuid
from utils.unified_logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# 主持人配置文件路径
HOST_FILE = "template/host_config.json"


class Host(BaseModel):
    id: str
    name: str
    role: str


def load_hosts() -> List[Dict[str, Any]]:
    """加载主持人配置列表"""
    try:
        if os.path.exists(HOST_FILE):
            with open(HOST_FILE, 'r', encoding='utf-8') as f:
                hosts = json.load(f)
                # 确保返回的是列表格式
                if isinstance(hosts, list):
                    # 为没有ID的主持人自动生成ID
                    for host in hosts:
                        if 'id' not in host or not host['id']:
                            host['id'] = str(uuid.uuid4())
                    return hosts
        # 如果文件不存在，返回空列表
        return []
    except Exception as e:
        logger.error(f"加载主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="加载主持人配置失败")


def load_host_by_id(host_id: str) -> Dict[str, Any]:
    """根据主持人ID加载特定主持人配置"""
    try:
        hosts = load_hosts()
        host = next((h for h in hosts if h["id"] == host_id), None)
        if not host:
            raise HTTPException(status_code=404, detail=f"主持人ID {host_id} 未找到")
        return host
    except Exception as e:
        logger.error(f"加载主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="加载主持人配置失败")


def save_hosts(hosts: List[Host]) -> bool:
    """保存主持人配置列表"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(HOST_FILE), exist_ok=True)

        # 转换为字典格式
        hosts_dict = []
        for host in hosts:
            host_dict = {
                "id": host.id,
                "name": host.name,
                "role": host.role
            }
            hosts_dict.append(host_dict)

        with open(HOST_FILE, 'w', encoding='utf-8') as f:
            json.dump(hosts_dict, f, ensure_ascii=False, indent=2)

        logger.info("主持人配置列表保存成功")
        return True
    except Exception as e:
        logger.error(f"保存主持人配置失败: {str(e)}")
        return False


def update_host_by_id(host_id: str, updated_host: Host) -> bool:
    """根据ID更新单个主持人配置"""
    try:
        # 加载现有主持人配置列表
        existing_hosts = load_hosts()

        # 查找并更新指定ID的主持人配置
        host_found = False
        for i, host in enumerate(existing_hosts):
            if host.get("id") == host_id:
                existing_hosts[i] = {
                    "id": updated_host.id,
                    "name": updated_host.name,
                    "role": updated_host.role
                }
                host_found = True
                break

        if not host_found:
            return False

        # 保存更新后的主持人配置列表
        return save_hosts([Host(**h) for h in existing_hosts])
    except Exception as e:
        logger.error(f"根据ID更新主持人配置失败: {str(e)}")
        return False


def delete_host_by_id(host_id: str) -> bool:
    """根据ID删除单个主持人配置"""
    try:
        # 加载现有主持人配置列表
        existing_hosts = load_hosts()

        # 查找并删除指定ID的主持人配置
        original_count = len(existing_hosts)
        existing_hosts = [host for host in existing_hosts if host.get("id") != host_id]
        
        if len(existing_hosts) == original_count:
            return False  # 没有找到要删除的主持人配置

        # 保存更新后的主持人配置列表
        return save_hosts([Host(**h) for h in existing_hosts])
    except Exception as e:
        logger.error(f"根据ID删除主持人配置失败: {str(e)}")
        return False


@router.get("/hosts")
async def get_hosts():
    """获取主持人配置列表"""
    try:
        hosts = load_hosts()
        return hosts
    except Exception as e:
        logger.error(f"获取主持人配置列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取主持人配置列表失败")


@router.get("/hosts/{host_id}")
async def get_host_by_id(host_id: str):
    """根据ID获取单个主持人配置"""
    try:
        host = load_host_by_id(host_id)
        return host
    except Exception as e:
        logger.error(f"获取主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取主持人配置失败")


@router.post("/hosts")
async def create_host(host: Host):
    """创建新的主持人配置"""
    try:
        # 验证主持人配置内容
        if not host.name.strip():
            raise HTTPException(status_code=400, detail="主持人名称不能为空")

        if not host.role.strip():
            raise HTTPException(status_code=400, detail="主持人角色不能为空")

        # 检查名称是否重复
        existing_hosts = load_hosts()
        if any(h.get("name") == host.name for h in existing_hosts):
            raise HTTPException(status_code=400, detail="主持人名称已存在")

        # 生成新的主持人ID
        host.id = str(uuid.uuid4())

        # 添加新主持人配置
        existing_hosts.append(host.dict())

        # 保存更新后的主持人配置列表
        if save_hosts([Host(**h) for h in existing_hosts]):
            return {"message": "主持人配置创建成功", "host_id": host.id}
        else:
            raise HTTPException(status_code=500, detail="保存主持人配置失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建主持人配置失败")


@router.put("/hosts/{host_id}")
async def update_host_by_id(host_id: str, host: Host):
    """根据ID更新单个主持人配置"""
    try:
        # 验证主持人配置内容
        if not host.name.strip():
            raise HTTPException(status_code=400, detail="主持人名称不能为空")

        if not host.role.strip():
            raise HTTPException(status_code=400, detail="主持人角色不能为空")

        # 检查名称是否重复（排除当前主持人）
        existing_hosts = load_hosts()
        if any(h.get("name") == host.name and h.get("id") != host_id for h in existing_hosts):
            raise HTTPException(status_code=400, detail="主持人名称已存在")

        # 确保主持人ID匹配
        if host.id != host_id:
            raise HTTPException(status_code=400, detail="主持人ID不匹配")

        # 更新主持人配置
        if update_host_by_id(host_id, host):
            return {"message": "主持人配置更新成功"}
        else:
            raise HTTPException(status_code=404, detail="主持人配置未找到")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新主持人配置失败")


@router.delete("/hosts/{host_id}")
async def delete_host_by_id(host_id: str):
    """根据ID删除单个主持人配置"""
    try:
        if delete_host_by_id(host_id):
            return {"message": "主持人配置删除成功"}
        else:
            raise HTTPException(status_code=404, detail="主持人配置未找到")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除主持人配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除主持人配置失败")
