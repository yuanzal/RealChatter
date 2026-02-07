# -*- coding: utf-8 -*-
"""健康检查接口：供Go后端检测AI服务是否可用，无业务逻辑"""
from fastapi import APIRouter, Response, HTTPException
from starlette.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE

from utils import logger
from core import wechat_chat_parser

health_router = APIRouter(prefix="/health", tags=["健康检查"])

@health_router.get("/live", summary="存活检查：仅返回200表示服务运行")
async def live_check():
    return Response(status_code=HTTP_200_OK, content="AI Service is live")

@health_router.get("/ready", summary="就绪检查：验证核心组件是否可用")
async def ready_check():
    try:
        # 验证解析器实例是否可用（简单测试）
        test_content = "【2025-02-03 10:00】测试：健康检查"
        wechat_chat_parser.parse(test_content, "txt", use_cache=False)
        logger.info("AI服务就绪检查通过")
        return {
            "status": "ready",
            "service": "python-ai",
            "message": "AI Service is ready to handle requests"
        }
    except Exception as e:
        logger.error(f"AI服务就绪检查失败：{str(e)}")
        raise HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail="AI Service not ready")