import json
import logging
import re


def json_match(content: str):
    """简化的JSON解析函数"""
    if not content:
        return {}
    
    try:
        # 首先尝试直接解析整个内容
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    try:
        # 尝试查找JSON块
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    logging.error(f"JSON解析失败，原始内容: {content[:200]}...")
    return {}