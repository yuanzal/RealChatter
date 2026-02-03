# -*- coding: utf-8 -*-
"""Python-AI服务入口：初始化FastAPI、注册路由、启动服务"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api import chat_router, health_router
from utils import logger

# 初始化FastAPI应用
app = FastAPI(
    title="RealChatter AI Service",
    description="RealChatter项目AI服务：聊天记录解析、AI风格模仿",
    version="1.0.0",
    docs_url="/docs",  # Swagger文档地址
    redoc_url="/redoc" # ReDoc文档地址
)

# 跨域配置（允许Go服务层跨域调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有，生产环境指定Go服务地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)
app.include_router(health_router)

# 根路径测试
@app.get("/", summary="根路径测试")
async def root():
    return {
        "service": "RealChatter AI Service",
        "status": "running",
        "docs": "/docs"
    }

if __name__ == "__main__":
    # 启动FastAPI服务
    logger.info(f"RealChatter AI服务启动中：http://{settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run(
        app="main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
