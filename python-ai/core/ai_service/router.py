# -*- coding: utf-8 -*-
"""AI版本路由器：分发免费/付费/高级请求到对应模型，解耦接口与模型实现"""
from typing import Dict, Optional, Any, Type
from utils import logger
from ai_model.free.model import FreeAIModel
# from ai_model.pro.model import ProAIModel
from ai_model.free.config import free_model_config
# from ai_model.pro.config import pro_model_config
from core.ai_service.base import BaseAIModel

# 模型实例注册表（单例模式，避免重复加载模型）
MODEL_INSTANCES: Dict[str, BaseAIModel] = {
    "free": None,  # 免费版实例
    "pro": None,   # 付费版实例
    "advanced": None  # 高级版实例（预留）
}

# 模型配置注册表
MODEL_CONFIGS: Dict[str, Dict] = {
    "free": free_model_config,
    "pro": None,
    "advanced": {}  # 高级版配置（预留）
}

# 模型类注册表
MODEL_CLASSES: Dict[str, Type[BaseAIModel]] = {
    "free": FreeAIModel,
    "pro": None,
    "advanced": None  # 高级版类（预留）
}

class AIModelRouter:
    """AI模型路由器"""
    @staticmethod
    def get_model_instance(version: str = "free") -> Optional[BaseAIModel]:
        """
        获取模型实例（单例，首次调用自动初始化）
        :param version: 模型版本 free/pro/advanced
        :return: 模型实例/None
        """
        if version not in MODEL_INSTANCES:
            logger.error(f"模型版本不支持：{version}，仅支持free/pro/advanced")
            return None
        # 单例：未实例化则创建
        if MODEL_INSTANCES[version] is None:
            model_cls = MODEL_CLASSES[version]
            model_config = MODEL_CONFIGS[version]
            if model_cls is None or not model_config:
                logger.error(f"模型版本{version}未配置，无法实例化")
                return None
            MODEL_INSTANCES[version] = model_cls(model_config)
            logger.info(f"模型版本{version}实例化成功")
        return MODEL_INSTANCES[version]

    @staticmethod
    def route_load_quantize(version: str = "free") -> Dict[str, Any]:
        """
        路由：加载量化模型
        :param version: 模型版本
        :return: 加载结果
        """
        model = AIModelRouter.get_model_instance(version)
        if model is None:
            return {"code": 400, "msg": f"模型版本{version}无效，加载失败", "data": {}}
        return model.load_quantize_model()

    @staticmethod
    def route_generate_imitate(version: str = "free", context: str = "", question: str = "", **kwargs) -> Dict[str, Any]:
        """
        路由：风格模仿生成
        :param version: 模型版本
        :param context: 聊天上下文
        :param question: 生成指令
        :param kwargs: 扩展参数
        :return: 生成结果
        """
        model = AIModelRouter.get_model_instance(version)
        if model is None:
            return {"code": 400, "msg": f"模型版本{version}无效，生成失败", "data": {}}
        return model.generate_imitate(context, question, **kwargs)

    @staticmethod
    def route_get_status(version: str = "free") -> Dict[str, Any]:
        """
        路由：查询模型状态
        :param version: 模型版本
        :return: 状态结果
        """
        model = AIModelRouter.get_model_instance(version)
        if model is None:
            return {"code": 400, "msg": f"模型版本{version}无效，查询失败", "data": {}}
        return model.get_status()

    @staticmethod
    def route_release(version: str = "free") -> Dict[str, Any]:
        """
        路由：释放模型资源
        :param version: 模型版本
        :return: 释放结果
        """
        model = AIModelRouter.get_model_instance(version)
        if model is None or MODEL_INSTANCES[version] is None:
            return {"code": 400, "msg": f"模型版本{version}未实例化，释放失败", "data": {}}
        result = model.release()
        # 释放后置空实例，下次调用重新初始化
        MODEL_INSTANCES[version] = None
        return result

    # 预留：高级AI接口路由（后续扩展）
    @staticmethod
    def route_advanced_api(version: str = "advanced", **kwargs) -> Dict[str, Any]:
        """
        预留：高级AI接口通用路由
        :param version: 高级模型版本
        :param kwargs: 扩展参数
        :return: 接口结果
        """
        if version != "advanced":
            return {"code": 400, "msg": "仅支持高级模型版本", "data": {}}
        model = AIModelRouter.get_model_instance(version)
        if model is None:
            return {"code": 501, "msg": "高级AI接口尚未实现，敬请期待", "data": {}}
        # 后续实现高级模型的通用方法
        return {"code": 200, "msg": "高级AI接口调用成功", "data": {"version": "advanced"}}