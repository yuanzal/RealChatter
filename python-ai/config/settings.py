# -*- coding: utf-8 -*-
"""AI服务统一配置：聊天解析、缓存、日志等"""
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# 加载.env环境变量
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

class Settings(BaseSettings):
    # 服务基础配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    API_RELOAD: bool = True  # 开发模式自动重载

    # 聊天记录解析配置
    PARSE_SUPPORT_FORMATS: list = ["txt", "xml"]  # 支持的解析格式
    PARSE_SYS_MSG_KEYWORDS: list = [              # 需过滤的系统消息关键词
        "撤回了一条消息", "发起了群聊", "加入了群聊", "退出了群聊",
        "修改了群聊名称", "发送了文件", "发送了图片", "发送了视频",
        "语音通话", "视频通话", "红包", "转账", "位置共享", "发送了小程序"
    ]
    PARSE_TIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"  # 标准化时间格式

    # 缓存配置
    CACHE_MAXSIZE: int = 100  # LRU缓存最大容量
    CACHE_EXPIRE_SEC: int = 3600  # 缓存过期时间（秒）

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/ai_service.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 单个日志文件10MB
    LOG_BACKUP_COUNT: int = 5  # 日志文件备份数

# 全局配置实例
settings = Settings()