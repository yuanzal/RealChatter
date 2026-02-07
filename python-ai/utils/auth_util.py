# -*- coding: utf-8 -*-
"""AI接口鉴权工具：仅本地访问+API密钥鉴权"""
from fastapi import HTTPException, Request
from config import settings  # 全局配置的鉴权密钥

def check_local_auth(request: Request):
    """
    校验是否为本地访问（仅允许127.0.0.1/localhost访问）
    :param request: FastAPI请求对象
    :return: True/HTTPException
    """
    client_host = request.client.host
    local_ips = ["127.0.0.1", "localhost", "0.0.0.0"]
    if client_host not in local_ips:
        raise HTTPException(status_code=403, detail="仅允许本地访问AI接口")
    return True

def check_api_key(api_key: str) -> bool:
    """
    校验API密钥是否有效
    :param api_key: 请求传入的密钥
    :return: True/False
    """
    return api_key == settings.API_AUTH_KEY

__all__ = ["check_local_auth", "check_api_key"]