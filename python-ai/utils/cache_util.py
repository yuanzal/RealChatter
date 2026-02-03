# -*- coding: utf-8 -*-
"""缓存工具：LRU缓存封装，支持容量限制、键生成"""
import hashlib
from lru import LRU
from config import settings
from utils.log_util import logger

class LRUCache:
    """LRU缓存类：封装LRU，提供通用缓存操作"""
    def __init__(self, maxsize: int = None):
        self.maxsize = maxsize or settings.CACHE_MAXSIZE
        # 修复位置：直接传数值，不写 maxsize=
        self.cache = LRU(self.maxsize)
        logger.info(f"LRU缓存初始化完成，最大容量：{self.maxsize}")

    def get(self, key: str):
        """获取缓存值，不存在返回None"""
        if key in self.cache:
            logger.debug(f"缓存命中：{key[:8]}...")
            return self.cache[key]
        logger.debug(f"缓存未命中：{key[:8]}...")
        return None

    def set(self, key: str, value):
        """设置缓存值，超量自动淘汰最久未使用"""
        self.cache[key] = value
        logger.debug(f"缓存设置成功：{key[:8]}...")

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")

# 生成内容唯一标识（缓存key）：MD5哈希，避免重复解析
def generate_content_key(content: str) -> str:
    """
    生成内容的MD5哈希值作为唯一key
    :param content: 原始内容（TXT/XML字符串）
    :return: MD5哈希字符串
    """
    if not content:
        return ""
    return hashlib.md5(content.strip().encode("utf-8")).hexdigest()

# 全局缓存实例
global_cache = LRUCache()

__all__ = ["global_cache", "generate_content_key"]
