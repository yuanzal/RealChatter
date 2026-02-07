# -*- coding: utf-8 -*-
"""AI模型接口层：与Go服务层交互，标准化请求/响应，添加鉴权"""
from fastapi import APIRouter, HTTPException, Body, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from core.ai_service.router import AIModelRouter
from utils import check_local_auth, check_api_key  # 本地访问鉴权+API密钥鉴权
from utils import logger
from utils.response import standard_response  # 标准化响应工具

# 定义路由，与Go服务层约定前缀/ai/v1，标签统一
ai_router = APIRouter(prefix="/ai/v1", tags=["AI模型服务"])

# 标准化请求模型（与Go服务层约定）
class ModelQuantizeRequest(BaseModel):
    version: str = Field(default="free", description="模型版本 free/pro", pattern=r"^free|pro$")

class GenerateImitateRequest(BaseModel):
    context: str = Field(..., description="聊天上下文（结构化解析后的内容）")
    question: str = Field(..., description="生成指令/问题（如：模仿上述风格回复）")
    version: str = Field(default="free", description="模型版本 free/pro", pattern=r"^free|pro$")
    max_gen_len: Optional[int] = Field(512, description="最大生成长度")
    temperature: Optional[float] = Field(0.7, description="生成温度，0-1")

# 依赖项：组合鉴权（仅本地访问 + API密钥鉴权）
def ai_auth(
    api_key: str = Query(..., description="API鉴权密钥"),
    local_check: bool = Depends(check_local_auth)
):
    """AI接口鉴权依赖：必须同时满足本地访问+正确API密钥"""
    if not check_api_key(api_key):
        raise HTTPException(status_code=401, detail="API密钥无效")
    return True

# 1. 模型量化加载接口：/ai/v1/model/quantize POST
@ai_router.post("/model/quantize", summary="模型量化加载", dependencies=[Depends(ai_auth)])
async def model_quantize(
    req: ModelQuantizeRequest = Body(...)
):
    """
    加载并初始化4bit量化模型，返回就绪状态
    - version：模型版本，free=千问1.8B，pro=ChatGLM-4
    - 鉴权：仅本地访问+API密钥
    - 适配16G内存，加载无卡顿
    """
    logger.info(f"收到模型量化加载请求，版本：{req.version}")
    result = AIModelRouter.route_load_quantize(version=req.version)
    if result["code"] != 200:
        raise HTTPException(status_code=result["code"], detail=result["msg"])
    return standard_response(**result)

# 2. 模仿生成接口：/ai/v1/generate/imitate POST
@ai_router.post("/generate/imitate", summary="风格模仿生成", dependencies=[Depends(ai_auth)])
async def generate_imitate(
    req: GenerateImitateRequest = Body(...)
):
    """
    风格模仿生成：Go传入上下文+问题，Python返回模仿结果
    - context：聊天上下文（从/ai/v1/parse接口获取的结构化数据）
    - question：生成指令
    - version：模型版本，free=基础版，pro=高级版
    - 要求：接口返回耗时≤3s，生成内容贴合风格
    - 鉴权：仅本地访问+API密钥
    """
    logger.info(f"收到风格模仿生成请求，版本：{req.version}，上下文长度：{len(req.context)}")
    result = AIModelRouter.route_generate_imitate(
        version=req.version,
        context=req.context,
        question=req.question,
        max_gen_len=req.max_gen_len,
        temperature=req.temperature
    )
    if result["code"] != 200:
        raise HTTPException(status_code=result["code"], detail=result["msg"])
    return standard_response(**result)

# 3. 模型状态查询接口：/ai/v1/model/status GET
@ai_router.get("/model/status", summary="模型状态查询", dependencies=[Depends(ai_auth)])
async def model_status(
    version: str = Query("free", description="模型版本 free/pro", pattern=r"^free|pro$")
):
    """
    查询模型是否加载完成、是否可用
    - version：模型版本
    - 鉴权：仅本地访问+API密钥
    """
    logger.info(f"收到模型状态查询请求，版本：{version}")
    result = AIModelRouter.route_get_status(version=version)
    if result["code"] != 200:
        raise HTTPException(status_code=result["code"], detail=result["msg"])
    return standard_response(**result)
