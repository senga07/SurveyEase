from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
import uuid
from utils.unified_logger import get_logger
from graph.survey_graph import SurveyGraph

router = APIRouter()
logger = get_logger(__name__)

# 模板文件路径
TEMPLATE_FILE = "template/survey_template.json"

# 模板缓存：避免重复创建相同模板的SurveyGraph实例
template_graph_cache: Dict[str, SurveyGraph] = {}


class SurveyStep(BaseModel):
    id: str
    content: str
    type: str = "linear"  # "linear" | "condition"
    default_branch: str = None  # 默认跳转的步骤ID
    branches: List[Dict[str, str]] = []  # 条件分支


class SurveyTemplate(BaseModel):
    id: str
    theme: str
    system_prompt: str
    max_turns: int
    welcome_message: str
    steps: List[SurveyStep]
    end_message: str


def load_templates() -> List[Dict[str, Any]]:
    """加载调研模板列表"""
    try:
        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                templates = json.load(f)
                # 确保返回的是列表格式
                if isinstance(templates, list):
                    # 为没有ID的模板自动生成ID
                    for template in templates:
                        if 'id' not in template or not template['id']:
                            template['id'] = str(uuid.uuid4())
                    return templates
        raise HTTPException(status_code=404, detail="模板未配置")
    except Exception as e:
        logger.error(f"加载模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="加载模板失败")


def load_template_by_id(template_id: str) -> Dict[str, Any]:
    """根据模板ID加载特定模板"""
    try:
        templates = load_templates()
        template = next((t for t in templates if t["id"] == template_id), None)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板ID {template_id} 未找到")
        return template
    except Exception as e:
        logger.error(f"加载模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="加载模板失败")


def save_templates(templates: List[SurveyTemplate]) -> bool:
    """保存调研模板列表"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(TEMPLATE_FILE), exist_ok=True)

        # 转换为字典格式
        templates_dict = []
        for template in templates:
            template_dict = {
                "id": template.id,
                "theme": template.theme,
                "system_prompt": template.system_prompt,
                "max_turns": template.max_turns,
                "welcome_message": template.welcome_message,
                "steps": [
                    {
                        "id": step.id, 
                        "content": step.content,
                        "type": step.type,
                        "default_branch": step.default_branch,
                        "branches": step.branches
                    } 
                    for step in template.steps
                ],
                "end_message": template.end_message
            }
            templates_dict.append(template_dict)

        with open(TEMPLATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates_dict, f, ensure_ascii=False, indent=2)

        logger.info("调研模板列表保存成功")
        return True
    except Exception as e:
        logger.error(f"保存模板失败: {str(e)}")
        return False


def update_template_by_id(template_id: str, updated_template: SurveyTemplate) -> bool:
    """根据ID更新单个模板"""
    try:
        # 加载现有模板列表
        existing_templates = load_templates()

        # 查找并更新指定ID的模板
        template_found = False
        for i, template in enumerate(existing_templates):
            if template.get("id") == template_id:
                existing_templates[i] = {
                    "id": updated_template.id,
                    "theme": updated_template.theme,
                    "system_prompt": updated_template.system_prompt,
                    "max_turns": updated_template.max_turns,
                    "welcome_message": updated_template.welcome_message,
                    "steps": [
                        {
                            "id": step.id, 
                            "content": step.content,
                            "type": step.type,
                            "default_branch": step.default_branch,
                            "branches": step.branches
                        } 
                        for step in updated_template.steps
                    ],
                    "end_message": updated_template.end_message
                }
                template_found = True
                break

        if not template_found:
            return False

        # 保存更新后的模板列表
        return save_templates([SurveyTemplate(**t) for t in existing_templates])
    except Exception as e:
        logger.error(f"根据ID更新模板失败: {str(e)}")
        return False


def clear_template_cache(template_id: str = None):
    """清理模板缓存，如果template_id为None则清理所有缓存"""
    if template_id:
        if template_id in template_graph_cache:
            del template_graph_cache[template_id]
    else:
        template_graph_cache.clear()


@router.get("/templates")
async def get_templates():
    """获取调研模板列表"""
    try:
        return load_templates()
    except Exception as e:
        logger.error(f"获取模板列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模板列表失败")


@router.post("/templates")
async def create_template(template: SurveyTemplate):
    """创建新的调研模板"""
    try:
        # 验证模板内容
        if not template.theme.strip():
            raise HTTPException(status_code=400, detail="调研主题不能为空")

        if not template.system_prompt.strip():
            raise HTTPException(status_code=400, detail="系统提示不能为空")

        if template.max_turns <= 0:
            raise HTTPException(status_code=400, detail="最大轮数必须大于0")

        if not template.welcome_message.strip():
            raise HTTPException(status_code=400, detail="开场白不能为空")

        if not template.end_message.strip():
            raise HTTPException(status_code=400, detail="结束语不能为空")

        if not template.steps or len(template.steps) == 0:
            raise HTTPException(status_code=400, detail="至少需要一个调研步骤")

        for step in template.steps:
            if not step.content.strip():
                raise HTTPException(status_code=400, detail="所有步骤内容不能为空")

        # 生成新的模板ID
        template.id = str(uuid.uuid4())

        # 获取现有模板列表
        existing_templates = load_templates()

        # 添加新模板
        existing_templates.append(template.dict())

        # 保存更新后的模板列表
        if save_templates([SurveyTemplate(**t) for t in existing_templates]):
            return {"message": "模板创建成功", "template_id": template.id}
        else:
            raise HTTPException(status_code=500, detail="保存模板失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建模板失败")


@router.put("/templates/{template_id}")
async def update_by_id(template_id: str, template: SurveyTemplate):
    """根据ID更新单个模板"""
    try:
        # 验证模板内容
        if not template.theme.strip():
            raise HTTPException(status_code=400, detail="调研主题不能为空")

        if not template.system_prompt.strip():
            raise HTTPException(status_code=400, detail="系统提示不能为空")

        if template.max_turns <= 0:
            raise HTTPException(status_code=400, detail="最大轮数必须大于0")

        if not template.welcome_message.strip():
            raise HTTPException(status_code=400, detail="开场白不能为空")

        if not template.end_message.strip():
            raise HTTPException(status_code=400, detail="结束语不能为空")

        if not template.steps or len(template.steps) == 0:
            raise HTTPException(status_code=400, detail="至少需要一个调研步骤")

        for step in template.steps:
            if not step.content.strip():
                raise HTTPException(status_code=400, detail="所有步骤内容不能为空")

        # 确保模板ID匹配
        if template.id != template_id:
            raise HTTPException(status_code=400, detail="模板ID不匹配")

        # 更新模板
        if update_template_by_id(template_id, template):
            # 清理对应的模板缓存
            clear_template_cache(template_id)
            return {"message": "模板更新成功"}
        else:
            raise HTTPException(status_code=404, detail="模板未找到")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新模板失败")
