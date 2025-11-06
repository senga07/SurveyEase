from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid
from database import get_db
from database.models import AISurveyTemplate, AISurveyTemplateStep, AISurveyTemplateVariable
from utils.unified_logger import get_logger
from graph.survey_graph import SurveyGraph
import re

router = APIRouter()
logger = get_logger(__name__)

# 模板缓存：避免重复创建相同模板的SurveyGraph实例
template_graph_cache: Dict[str, SurveyGraph] = {}


class SurveyStep(BaseModel):
    id: str
    content: str
    type: str = "linear"  # "linear" | "condition"
    condition: str = ""  # 条件跳转的匹配条件
    branches: List[str] = []  # 简化为字符串数组，[0]为是，[1]为否


class SurveyVariable(BaseModel):
    key: str
    value: str


class SurveyTemplate(BaseModel):
    id: str
    theme: str
    system_prompt: str
    background_knowledge: str = ""
    max_turns: int
    welcome_message: str
    steps: List[SurveyStep]
    end_message: str
    variables: List[SurveyVariable] = []
    host_id: str = ""


async def load_templates_from_db(db: AsyncSession) -> List[Dict[str, Any]]:
    """从数据库加载调研模板列表"""
    try:
        # 查询所有未删除的模板
        result = await db.execute(
            select(AISurveyTemplate).where(
                AISurveyTemplate.is_deleted == 0
            ).order_by(AISurveyTemplate.create_datetime.desc())
        )
        templates = result.scalars().all()
        
        template_list = []
        for template in templates:
            template_dict = await template_to_dict(template, db)
            template_list.append(template_dict)
        
        return template_list
    except Exception as e:
        logger.error(f"从数据库加载模板失败: {str(e)}")
        raise


async def template_to_dict(template: AISurveyTemplate, db: AsyncSession) -> Dict[str, Any]:
    """将数据库模板对象转换为字典格式"""
    # 加载步骤
    steps_result = await db.execute(
        select(AISurveyTemplateStep).where(
            and_(
                AISurveyTemplateStep.template_id == template.id,
                AISurveyTemplateStep.is_deleted == 0
            )
        ).order_by(AISurveyTemplateStep.step_order)
    )
    steps = steps_result.scalars().all()
    
    # 加载变量
    variables_result = await db.execute(
        select(AISurveyTemplateVariable).where(
            and_(
                AISurveyTemplateVariable.template_id == template.id,
                AISurveyTemplateVariable.is_deleted == 0
            )
        )
    )
    variables = variables_result.scalars().all()
    
    # 构建步骤列表
    steps_list = []
    for step in steps:
        step_dict = {
            "id": str(step.step_id),
            "content": step.content,
            "type": step.type,
            "condition": step.condition_text or "",
            "branches": step.branches if step.branches else []
        }
        steps_list.append(step_dict)
    
    # 构建变量列表
    variables_list = []
    for var in variables:
        var_dict = {
            "key": var.variable_key,
            "value": var.variable_value
        }
        variables_list.append(var_dict)
    
    # 构建模板字典
    template_dict = {
        "id": template.id,
        "theme": template.theme,
        "system_prompt": template.system_prompt or "",
        "background_knowledge": template.background_knowledge or "",
        "max_turns": template.max_turns or 5,
        "welcome_message": template.welcome_message or "",
        "end_message": template.end_message or "",
        "steps": steps_list,
        "variables": variables_list,
        "host_id": template.host_id or ""
    }
    
    return template_dict


async def load_template_by_id_from_db(template_id: str, db: AsyncSession) -> Dict[str, Any]:
    """根据模板ID从数据库加载特定模板（原始数据，不进行变量替换）"""
    try:
        result = await db.execute(
            select(AISurveyTemplate).where(
                and_(
                    AISurveyTemplate.id == template_id,
                    AISurveyTemplate.is_deleted == 0
                )
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(status_code=404, detail=f"模板ID {template_id} 未找到")
        
        return await template_to_dict(template, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从数据库加载模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="加载模板失败")


async def save_template_to_db(template: SurveyTemplate, db: AsyncSession) -> bool:
    """保存调研模板到数据库"""
    try:
        # 创建或更新模板主记录
        result = await db.execute(
            select(AISurveyTemplate).where(
                and_(
                    AISurveyTemplate.id == template.id,
                    AISurveyTemplate.is_deleted == 0
                )
            )
        )
        existing_template = result.scalar_one_or_none()
        
        if existing_template:
            # 更新现有模板
            existing_template.theme = template.theme
            existing_template.system_prompt = template.system_prompt
            existing_template.background_knowledge = template.background_knowledge
            existing_template.max_turns = template.max_turns
            existing_template.welcome_message = template.welcome_message
            existing_template.end_message = template.end_message
            existing_template.host_id = template.host_id
        else:
            # 创建新模板
            new_template = AISurveyTemplate(
                id=template.id,
                theme=template.theme,
                system_prompt=template.system_prompt,
                background_knowledge=template.background_knowledge,
                max_turns=template.max_turns,
                welcome_message=template.welcome_message,
                end_message=template.end_message,
                host_id=template.host_id,
                is_deleted=0
            )
            db.add(new_template)
        
        # 软删除所有现有步骤（标记为已删除）
        steps_result = await db.execute(
            select(AISurveyTemplateStep).where(
                and_(
                    AISurveyTemplateStep.template_id == template.id,
                    AISurveyTemplateStep.is_deleted == 0
                )
            )
        )
        old_steps = steps_result.scalars().all()
        for step in old_steps:
            step.is_deleted = 1
        
        # 创建新步骤
        for order, step in enumerate(template.steps):
            # step_id 直接使用顺序索引，与 Graph 中的索引保持一致
            new_step = AISurveyTemplateStep(
                template_id=template.id,
                step_id=order,
                content=step.content,
                type=step.type,
                condition_text=step.condition if step.condition else None,
                branches=step.branches if step.branches else None,
                step_order=order,
                is_deleted=0
            )
            db.add(new_step)
        
        # 软删除所有现有变量（标记为已删除）
        vars_result = await db.execute(
            select(AISurveyTemplateVariable).where(
                and_(
                    AISurveyTemplateVariable.template_id == template.id,
                    AISurveyTemplateVariable.is_deleted == 0
                )
            )
        )
        old_vars = vars_result.scalars().all()
        for var in old_vars:
            var.is_deleted = 1
        
        # 创建新变量
        for var in template.variables:
            new_var = AISurveyTemplateVariable(
                template_id=template.id,
                variable_key=var.key,
                variable_value=var.value,
                is_deleted=0
            )
            db.add(new_var)
        
        await db.commit()
        logger.info(f"模板保存成功: {template.id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"保存模板到数据库失败: {str(e)}")
        return False


def replace_variables(text: str, variables: List[SurveyVariable]) -> str:
    """替换文本中的变量占位符"""
    if not variables:
        return text

    # 创建变量映射字典
    var_map = {var.key: var.value for var in variables}

    # 使用正则表达式替换 {{key}} 格式的变量
    def replace_var(match):
        key = match.group(1)
        return var_map.get(key, match.group(0))  # 如果找不到变量，保持原样

    # 匹配 {{key}} 格式的变量
    pattern = r'\{\{([^}]+)\}\}'
    return re.sub(pattern, replace_var, text)


def apply_variable_substitution(template: Dict[str, Any]) -> Dict[str, Any]:
    """对模板应用变量替换"""
    variables = template.get('variables', [])
    if not variables:
        return template

    # 创建变量对象列表
    var_objects = [SurveyVariable(**var) for var in variables]

    # 替换各个字段中的变量
    updated_template = template.copy()

    # 替换主题
    if 'theme' in updated_template:
        updated_template['theme'] = replace_variables(updated_template['theme'], var_objects)

    # 替换系统提示
    if 'system_prompt' in updated_template:
        updated_template['system_prompt'] = replace_variables(updated_template['system_prompt'], var_objects)

    # 替换背景知识
    if 'background_knowledge' in updated_template:
        updated_template['background_knowledge'] = replace_variables(updated_template['background_knowledge'], var_objects)

    # 替换开场白
    if 'welcome_message' in updated_template:
        updated_template['welcome_message'] = replace_variables(updated_template['welcome_message'], var_objects)

    # 替换结束语
    if 'end_message' in updated_template:
        updated_template['end_message'] = replace_variables(updated_template['end_message'], var_objects)

    # 替换步骤内容
    if 'steps' in updated_template:
        for step in updated_template['steps']:
            if 'content' in step:
                step['content'] = replace_variables(step['content'], var_objects)
            # 替换步骤条件（跳转规则）
            if 'condition' in step:
                step['condition'] = replace_variables(step['condition'], var_objects)

    return updated_template


def clear_template_cache(template_id: str = None):
    """清理模板缓存，如果template_id为None则清理所有缓存"""
    if template_id:
        # 清理所有以该template_id开头的缓存
        keys_to_remove = [key for key in template_graph_cache.keys() if key.startswith(template_id)]
        for key in keys_to_remove:
            del template_graph_cache[key]
    else:
        template_graph_cache.clear()


async def validate_host_id(host_id: str, db: AsyncSession) -> bool:
    """验证主持人ID是否有效"""
    if not host_id or host_id.strip() == "":
        return True  # 空的主持人ID是允许的（可选字段）
    
    try:
        from api.host import get_host_by_id_from_db
        host = await get_host_by_id_from_db(host_id, db)
        return host is not None
    except Exception:
        return False


@router.get("/templates")
async def get_templates(db: AsyncSession = Depends(get_db)):
    """获取调研模板列表（用于配置页面，不进行变量替换）"""
    try:
        templates = await load_templates_from_db(db)
        return templates
    except Exception as e:
        logger.error(f"获取模板列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模板列表失败")


@router.get("/templates/runtime")
async def get_templates_for_runtime(db: AsyncSession = Depends(get_db)):
    """获取调研模板列表（用于运行时，进行变量替换）"""
    try:
        templates = await load_templates_from_db(db)
        # 对每个模板应用变量替换
        processed_templates = []
        for template in templates:
            processed_template = apply_variable_substitution(template)
            processed_templates.append(processed_template)
        return processed_templates
    except Exception as e:
        logger.error(f"获取模板列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模板列表失败")


@router.post("/templates")
async def create_template(template: SurveyTemplate, db: AsyncSession = Depends(get_db)):
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

        # 验证主持人ID（如果提供）
        if template.host_id and template.host_id.strip():
            if not await validate_host_id(template.host_id, db):
                raise HTTPException(status_code=400, detail="指定的主持人不存在")

        # 生成新的模板ID
        template.id = str(uuid.uuid4())

        # 保存模板到数据库
        if await save_template_to_db(template, db):
            return {"message": "模板创建成功", "template_id": template.id}
        else:
            raise HTTPException(status_code=500, detail="保存模板失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建模板失败")


@router.put("/templates/{template_id}")
async def update_by_id(template_id: str, template: SurveyTemplate, db: AsyncSession = Depends(get_db)):
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

        # 验证主持人ID（如果提供）
        if template.host_id and template.host_id.strip():
            if not await validate_host_id(template.host_id, db):
                raise HTTPException(status_code=400, detail="指定的主持人不存在")

        # 确保模板ID匹配
        if template.id != template_id:
            raise HTTPException(status_code=400, detail="模板ID不匹配")

        # 检查模板是否存在
        result = await db.execute(
            select(AISurveyTemplate).where(
                and_(
                    AISurveyTemplate.id == template_id,
                    AISurveyTemplate.is_deleted == 0
                )
            )
        )
        existing_template = result.scalar_one_or_none()
        if not existing_template:
            raise HTTPException(status_code=404, detail="模板未找到")

        # 更新模板
        if await save_template_to_db(template, db):
            # 清理对应的模板缓存
            clear_template_cache(template_id)
            return {"message": "模板更新成功"}
        else:
            raise HTTPException(status_code=500, detail="更新模板失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新模板失败")


@router.delete("/templates/{template_id}")
async def delete_template_by_id(template_id: str, db: AsyncSession = Depends(get_db)):
    """根据ID删除单个模板（软删除）"""
    try:
        # 检查模板是否存在
        result = await db.execute(
            select(AISurveyTemplate).where(
                and_(
                    AISurveyTemplate.id == template_id,
                    AISurveyTemplate.is_deleted == 0
                )
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(status_code=404, detail="模板未找到")
        
        # 软删除模板
        template.is_deleted = 1
        
        # 软删除所有相关步骤
        steps_result = await db.execute(
            select(AISurveyTemplateStep).where(
                and_(
                    AISurveyTemplateStep.template_id == template_id,
                    AISurveyTemplateStep.is_deleted == 0
                )
            )
        )
        steps = steps_result.scalars().all()
        for step in steps:
            step.is_deleted = 1
        
        # 软删除所有相关变量
        vars_result = await db.execute(
            select(AISurveyTemplateVariable).where(
                and_(
                    AISurveyTemplateVariable.template_id == template_id,
                    AISurveyTemplateVariable.is_deleted == 0
                )
            )
        )
        variables = vars_result.scalars().all()
        for var in variables:
            var.is_deleted = 1
        
        await db.commit()
        
        # 清理对应的模板缓存
        clear_template_cache(template_id)
        
        logger.info(f"删除模板成功: {template_id}")
        return {"message": "模板删除成功"}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除模板失败")
