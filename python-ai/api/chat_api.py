# -*- coding: utf-8 -*-
"""聊天记录解析接口：仅封装请求响应，调用core层解析逻辑"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from core import wechat_chat_parser
from utils import logger

# 定义路由（前缀/ai/v1，与Go服务层约定）
chat_router = APIRouter(prefix="/ai/v1", tags=["聊天记录解析"])

# 请求体模型（标准化，与Go服务层约定）
class ChatParseRequest(BaseModel):
    content: str = Field(..., description="聊天记录原始内容字符串（TXT/XML）")
    format_type: str = Field(..., description="格式类型，可选txt/xml", pattern=r"^txt|xml$")
    use_cache: Optional[bool] = Field(True, description="是否使用缓存，默认True")

# 响应体模型（标准化）
class ChatParseResponse(BaseModel):
    code: int
    msg: str
    data: dict

@chat_router.post("/parse", response_model=ChatParseResponse, summary="微信聊天记录解析")
async def parse_chat_record(req: ChatParseRequest):
    """
    微信纯文字聊天记录解析接口：支持TXT/XML，返回清洗后记录+解析统计
    - content：原始内容字符串（Go服务层读取文件后传递）
    - format_type：固定值txt/xml
    - use_cache：是否启用LRU缓存，默认开启
    """
    logger.info(f"收到聊天记录解析请求，格式类型：{req.format_type}，是否使用缓存：{req.use_cache}")
    # 调用core层解析逻辑（同步调用，解析为CPU密集型，无需async）
    result = wechat_chat_parser.parse(
        content=req.content.replace("\\n", "\n"),
        format_type=req.format_type,
        use_cache=req.use_cache
    )
    # 非200码抛出HTTP异常，供Go服务层捕获
    if result["code"] != 200:
        raise HTTPException(status_code=result["code"], detail=result["msg"])
    return result