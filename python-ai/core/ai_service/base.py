# -*- coding: utf-8 -*-
"""AI模型抽象基类：定义通用接口协议，所有版本模型必须实现"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

class BaseAIModel(ABC):
    """AI模型通用抽象基类"""
    # 模型状态：未加载/已加载/运行中/异常
    STATUS_UNLOADED = 0
    STATUS_LOADED = 1
    STATUS_RUNNING = 2
    STATUS_ERROR = 3

    @abstractmethod
    def __init__(self, model_config: Dict[str, Any]):
        """
        初始化模型
        :param model_config: 模型配置（量化参数、设备、路径等）
        """
        self.config = model_config
        self.model = None  # 模型实例
        self.tokenizer = None  # 分词器实例
        self.status = self.STATUS_UNLOADED  # 初始状态：未加载
        self.load_error: Optional[str] = None  # 加载错误信息

    @abstractmethod
    def load_quantize_model(self) -> Dict[str, Any]:
        """
        加载4bit量化模型（核心方法）
        :return: 加载结果 {"code": int, "msg": str, "data": Dict}
        要求：适配16G内存，加载完成后状态置为STATUS_LOADED
        """
        pass

    @abstractmethod
    def generate_imitate(self, context: str, question: str, **kwargs) -> Dict[str, Any]:
        """
        风格模仿生成（核心方法）
        :param context: 聊天上下文（Go服务传入）
        :param question: 生成指令/问题（Go服务传入）
        :param kwargs: 扩展参数（如温度、顶P、最大生成长度等）
        :return: 生成结果 {"code": int, "msg": str, "data": {"content": str, "cost_time": float}}
        要求：接口返回耗时≤3s，生成内容符合Prompt模板风格
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        获取模型状态
        :return: 状态结果 {"code": int, "msg": str, "data": {"status": int, "status_desc": str, "load_error": str}}
        """
        pass

    @abstractmethod
    def release(self) -> Dict[str, Any]:
        """
        释放模型资源（可选）
        :return: 释放结果 {"code": int, "msg": str}
        """
        pass