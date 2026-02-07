# -*- coding: utf-8 -*-
"""免费版AI模型：千问1.8B 4bit量化，适配16G内存，基础风格模仿"""
from core.ai_service.base import BaseAIModel
from ai_model.free.prompt import free_imitate_prompt  # 免费版Prompt模板
from utils.model_util import load_4bit_quant_model  # 通用4bit量化加载工具
from utils import logger
import time
import torch

class FreeAIModel(BaseAIModel):
    def __init__(self, model_config):
        super().__init__(model_config)
        self.model_path = model_config["model_path"]  # 千问1.8B量化模型路径
        self.quant_type = model_config["quant_type"]  # 4bit量化类型（GPTQ）
        self.device = model_config["device"]  # 设备（cpu/cuda）
        self.max_context_len = model_config["max_context_len"]  # 最大上下文长度
        self.max_gen_len = model_config["max_gen_len"]  # 最大生成长度
        self.timeout = model_config["timeout"]  # 推理超时时间（≤3s）

    def load_quantize_model(self):
        """加载千问1.8B 4bit量化模型，适配16G内存"""
        try:
            logger.info(f"开始加载免费版模型：千问1.8B，4bit量化，设备：{self.device}")
            # 调用通用量化加载工具，封装4bit量化细节，保证加载无卡顿
            self.model, self.tokenizer = load_4bit_quant_model(
                model_path=self.model_path,
                quant_type=self.quant_type,
                device=self.device,
                max_memory=self.config["max_memory"]  # 16G内存限制
            )
            self.status = self.STATUS_LOADED
            logger.info("免费版模型加载完成，状态：已就绪")
            return {
                "code": 200,
                "msg": "免费版模型加载成功",
                "data": {"model_name": "千问1.8B", "quant_type": "4bit", "device": self.device}
            }
        except Exception as e:
            self.status = self.STATUS_ERROR
            self.load_error = str(e)[:100]
            logger.error(f"免费版模型加载失败：{self.load_error}")
            return {
                "code": 500,
                "msg": f"免费版模型加载失败：{self.load_error}",
                "data": {}
            }

    def generate_imitate(self, context, question, **kwargs):
        """风格模仿生成，保证耗时≤3s"""
        start_time = time.time()
        # 校验模型状态
        if self.status != self.STATUS_LOADED:
            return {
                "code": 400,
                "msg": f"免费版模型未就绪，当前状态：{self.status}",
                "data": {}
            }
        try:
            # 1. 构造Prompt（调用免费版模板，风格模仿）
            prompt = free_imitate_prompt(context=context, question=question)
            # 2. 分词+上下文截断（适配最大上下文长度，避免内存溢出）
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.max_context_len).to(self.device)
            # 3. 推理生成（设置参数，保证耗时≤3s）
            with torch.no_grad():  # 关闭梯度，节省内存
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=kwargs.get("max_gen_len", self.max_gen_len),
                    temperature=kwargs.get("temperature", 0.7),
                    top_p=kwargs.get("top_p", 0.95),
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    timeout=self.timeout  # 超时限制≤3s
                )
            # 4. 解码结果
            generate_content = self.tokenizer.decode(outputs[0], skip_special_tokens=True).replace(prompt, "").strip()
            # 5. 计算耗时
            cost_time = round(time.time() - start_time, 3)
            logger.info(f"免费版模型生成完成，耗时：{cost_time}s，是否超时：{cost_time > self.timeout}")
            return {
                "code": 200,
                "msg": "生成成功",
                "data": {
                    "content": generate_content,
                    "cost_time": cost_time,
                    "model_name": "千问1.8B",
                    "version": "free"
                }
            }
        except Exception as e:
            cost_time = round(time.time() - start_time, 3)
            logger.error(f"免费版模型生成失败：{str(e)[:100]}，耗时：{cost_time}s")
            return {
                "code": 500,
                "msg": f"生成失败：{str(e)[:100]}",
                "data": {"cost_time": cost_time, "version": "free"}
            }

    def get_status(self):
        """获取免费版模型状态"""
        status_desc_map = {
            self.STATUS_UNLOADED: "未加载",
            self.STATUS_LOADED: "已就绪",
            self.STATUS_RUNNING: "运行中",
            self.STATUS_ERROR: "异常"
        }
        return {
            "code": 200,
            "msg": "查询成功",
            "data": {
                "status": self.status,
                "status_desc": status_desc_map[self.status],
                "load_error": self.load_error,
                "model_name": "千问1.8B",
                "version": "free",
                "quant_type": "4bit"
            }
        }

    def release(self):
        """释放免费版模型资源"""
        try:
            if self.model is not None:
                del self.model
                del self.tokenizer
                torch.cuda.empty_cache()  # 清理GPU缓存
            self.status = self.STATUS_UNLOADED
            logger.info("免费版模型资源释放成功")
            return {"code": 200, "msg": "免费版模型资源释放成功"}
        except Exception as e:
            logger.error(f"免费版模型资源释放失败：{str(e)[:100]}")
            return {"code": 500, "msg": f"释放失败：{str(e)[:100]}"}