# -*- coding: utf-8 -*-
"""日志工具：全局日志配置，统一输出格式"""
import logging
from logging.handlers import RotatingFileHandler
import os
from config import settings

# 确保日志目录存在
log_dir = os.path.dirname(settings.LOG_FILE)
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 初始化日志器
logger = logging.getLogger("python-ai")
logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
logger.handlers.clear()  # 清除默认处理器

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

# 文件处理器（按大小切割）
file_handler = RotatingFileHandler(
    filename=settings.LOG_FILE,
    maxBytes=settings.LOG_MAX_BYTES,
    backupCount=settings.LOG_BACKUP_COUNT,
    encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

# 添加处理器
logger.addHandler(console_handler)
logger.addHandler(file_handler)

__all__ = ["logger"]