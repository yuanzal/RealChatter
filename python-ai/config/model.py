# -*- coding: utf-8 -*-
"""
模型全局量化配置文件：统一管理所有AI模型的量化框架、硬件设备、通用量化参数
所有版本模型（free/pro/advanced）均继承此全局配置，保证量化逻辑一致性
"""
from typing import Dict, Optional, Any
import torch

# ===================== 核心量化框架配置 =====================
# 统一指定量化框架（避免多版本模型使用不同框架导致的兼容问题）
# 可选：GPTQ/LLaMA.cpp/AWQ，本次适配4bit量化+16G内存，优先选择GPTQ（成熟、适配性强）
QUANT_FRAMEWORK: str = "GPTQ"

# 4bit量化通用参数（所有模型共用，保证量化精度/性能平衡）
QUANT_COMMON_PARAMS: Dict[str, Any] = {
    "bits": 4,  # 固定4bit量化（核心需求，适配16G内存）
    "group_size": 128,  # 量化分组大小，平衡精度和内存（GPTQ推荐值）
    "damp_percent": 0.01,  # 量化阻尼系数，提升量化后模型精度
    "sym": False,  # 非对称量化，比对称量化精度更高（4bit量化优选）
    "true_sequential": True  # 顺序量化，降低内存峰值（适配16G内存）
}

# ===================== 硬件设备配置 =====================
# 自动检测硬件（优先使用GPU/CUDA，无GPU则自动降级为CPU）
# 无需手动修改，代码自动适配本地硬件环境
def auto_detect_device() -> str:
    """自动检测运行设备，优先CUDA，其次CPU"""
    if torch.cuda.is_available():
        # 检测到GPU，返回cuda（支持多卡，默认使用第0卡）
        return "cuda:0"
    elif torch.backends.mps.is_available():
        # 苹果M系列芯片，返回mps（备选）
        return "mps"
    else:
        # 无专用加速硬件，返回cpu
        return "cpu"

# 全局运行设备（所有模型共用，自动检测无需手动配置）
DEVICE: str = auto_detect_device()

# 硬件资源通用限制（所有模型共用，避免单模型占满硬件资源）
DEVICE_RESOURCE_LIMIT: Dict[str, Any] = {
    "cpu": {"max_memory_ratio": 0.6},  # CPU内存最大占用比例（60%），预留内存给其他进程
    "cuda": {"max_memory_allocated": "8G"},  # GPU单卡最大分配显存（8G），适配16G内存主机
    "mps": {"max_memory_ratio": 0.7},  # 苹果M系列芯片内存占用比例（70%）
}

# ===================== 模型加载通用配置 =====================
# 模型/分词器加载通用参数，保证加载逻辑一致性
MODEL_LOAD_COMMON_PARAMS: Dict[str, Any] = {
    "trust_remote_code": True,  # 信任自定义模型代码（千问/ChatGLM均需开启）
    "low_cpu_mem_usage": True,  # 低CPU内存占用模式（核心，适配16G内存）
    "device_map": "auto",  # 自动设备映射，量化框架自动分配模型层到硬件
}

# ===================== 分词器通用配置 =====================
# 所有模型分词器共用参数，保证文本处理逻辑一致性
TOKENIZER_COMMON_PARAMS: Dict[str, Any] = {
    "padding_side": "right",  # 右侧填充，符合模型推理习惯
    "truncation_side": "left",  # 左侧截断，保留最新的上下文内容（聊天场景优选）
    "max_length": None,  # 全局不限制，各版本模型在专属配置中定义个性化值
}

# ===================== 配置对外导出 =====================
# 封装所有全局配置，供其他文件统一导入（简化导入逻辑）
MODEL_GLOBAL_CONFIG: Dict[str, Any] = {
    "quant_type": QUANT_FRAMEWORK,
    "quant_common_params": QUANT_COMMON_PARAMS,
    "device": DEVICE,
    "device_resource_limit": DEVICE_RESOURCE_LIMIT,
    "model_load_params": MODEL_LOAD_COMMON_PARAMS,
    "tokenizer_params": TOKENIZER_COMMON_PARAMS,
}

# 打印配置信息（启动时查看，方便调试）
print(f"===== AI模型全局量化配置加载完成 =====")
print(f"量化框架：{QUANT_FRAMEWORK} | 运行设备：{DEVICE}")
print(f"量化位数：{QUANT_COMMON_PARAMS['bits']}bit | 硬件资源限制：{DEVICE_RESOURCE_LIMIT[DEVICE.split(':')[0]]}")
print(f"=====================================")