# -*- coding: utf-8 -*-
"""标准化响应工具：统一Go↔Python交互的JSON格式"""
from typing import Dict, Any

def standard_response(code: int, msg: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化响应格式，与/ai/v1/parse接口保持一致
    :param code: 状态码 200=成功，其他=失败
    :param msg: 状态信息
    :param data: 业务数据
    :return: 标准化JSON响应
    """
    return {
        "code": code,
        "msg": msg,
        "data": data
    }
