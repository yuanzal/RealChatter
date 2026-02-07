# -*- coding: utf-8 -*-
import torch
import os
import json
from typing import Tuple
from config.model import MODEL_GLOBAL_CONFIG
from utils import logger
from transformers import AutoTokenizer, AutoConfig
from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig

def load_4bit_quant_model(
    model_path: str,
    quant_type: str = None,
    device: str = None,
    max_memory: str = None
) -> Tuple[AutoGPTQForCausalLM, AutoTokenizer]:
    """加载4bit GPTQ量化模型（终极稳定版：无任何多余参数，适配千问1.8B）"""
    # 基础参数处理
    use_quant_type = quant_type or MODEL_GLOBAL_CONFIG["quant_type"]
    use_device = device or MODEL_GLOBAL_CONFIG["device"]
    model_path = os.path.abspath(model_path).replace("\\", "/")
    logger.info(f"开始加载4bit量化模型 | 路径：{model_path} | 设备：{use_device}")

    try:
        # 1. 处理分词器参数（确保类型正确）
        tokenizer_params = MODEL_GLOBAL_CONFIG.get("tokenizer_params", {})
        if isinstance(tokenizer_params, str):
            tokenizer_params = json.loads(tokenizer_params) if tokenizer_params else {}

        # 加载千问分词器（仅保留必需参数）
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            **tokenizer_params,
            trust_remote_code=True  # 千问必需，仅传给分词器
        )
        logger.info(f"分词器加载成功 | 类型：{tokenizer.__class__.__name__}")

        # 2. 构建量化配置（AutoGPTQ 0.4.2 必需）
        quantize_config = BaseQuantizeConfig(
            bits=4,                # 4bit量化（固定）
            group_size=128,        # 千问1.8B默认分组
            sym=True,              # 对称量化
            desc_act=False         # 关闭激活描述符（CPU/GPU都兼容）
        )

        # 3. 规范化max_memory格式 + 设备key（仅保留合法格式）
        def normalize_max_memory(mem_str: str) -> str:
            if not mem_str:
                return "8.0GB"
            mem_str = mem_str.strip().lower()
            if "g" in mem_str and "gb" not in mem_str:
                num_part = mem_str.replace("g", "")
                try:
                    return f"{float(num_part):.1f}GB"
                except ValueError:
                    return "8.0GB"
            return mem_str

        normalized_mem = normalize_max_memory(max_memory) if max_memory else "8.0GB"
        max_memory_dict = {}
        if use_device.startswith("cuda"):
            # GPU设备：key用整数（0/1），值用规范格式
            gpu_id = int(use_device.split(":")[-1]) if ":" in use_device else 0
            max_memory_dict[gpu_id] = normalized_mem
        else:
            # CPU设备：key用字符串"cpu"
            max_memory_dict["cpu"] = normalized_mem

        # 4. 加载千问模型配置（仅保留必需参数）
        model_config = AutoConfig.from_pretrained(
            model_path,
            trust_remote_code=True  # 千问必需，仅传给模型配置
        )

        # ========== 核心：仅保留AutoGPTQ必需的参数，无任何多余参数 ==========
        model = AutoGPTQForCausalLM.from_pretrained(
            pretrained_model_name_or_path=model_path,  # 模型路径（唯一位置参数）
            quantize_config=quantize_config,           # 量化配置（必需）
            config=model_config,                       # 模型配置（必需）
            trust_remote_code=True,                    # 千问必需（仅透传，无冲突）
            device_map="auto",                         # 自动分配设备（替代use_cuda）
            max_memory=max_memory_dict                 # 内存限制（合法格式）
        )

        # 模型优化（推理模式，无多余参数）
        model.eval()
        torch.no_grad()
        logger.info(f"✅ 模型加载成功 | 设备：{use_device} | 最大内存限制：{normalized_mem}")
        return model, tokenizer

    except Exception as e:
        logger.error(f"❌ 模型加载失败：未知错误 | 错误详情：{str(e)}")
        raise