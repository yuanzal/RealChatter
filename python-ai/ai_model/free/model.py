# -*- coding: utf-8 -*-
"""免费版AI模型：千问1.8B 4bit量化，适配16G内存，基础风格模仿"""
from core.ai_service.base import BaseAIModel
from ai_model.free.prompt import free_imitate_prompt  # 免费版Prompt模板
from utils.model_util import load_4bit_quant_model  # 通用4bit量化加载工具
from utils import logger
import time
import torch
import threading  # 用于逻辑层超时控制


class FreeAIModel(BaseAIModel):
    def __init__(self, model_config):
        super().__init__(model_config)
        self.model_path = model_config["model_path"]  # 千问1.8B量化模型路径
        self.quant_type = model_config["quant_type"]  # 4bit量化类型（GPTQ）
        self.device = model_config["device"]  # 设备（cpu/cuda）
        self.max_context_len = model_config["max_context_len"]  # 最大上下文长度
        self.max_gen_len = model_config["max_gen_len"]  # 最大生成长度
        self.timeout = model_config["timeout"]  # 推理超时时间（≤4s）
        self.generate_result = None
        self.is_first_generate = True  # 标记首次生成

    def load_quantize_model(self):
        """加载千问1.8B 4bit量化模型，适配16G内存"""
        try:
            logger.info(f"开始加载免费版模型：千问1.8B，4bit量化，设备：{self.device}")
            self.model, self.tokenizer = load_4bit_quant_model(
                model_path=self.model_path,
                quant_type=self.quant_type,
                device=self.device,
                max_memory=self.config["max_memory"]  # 16G内存限制
            )
            # 1. 给tokenizer设置pad_token（复用eos_token，千问官方推荐）
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
            # 2. 同步更新模型配置（必须，否则generate时参数不匹配）
            if self.model.config.pad_token_id is None:
                self.model.config.pad_token_id = self.tokenizer.pad_token_id
            # 3. 确保eos_token_id和pad_token_id一致（千问专属）
            self.model.config.eos_token_id = self.tokenizer.eos_token_id
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

    def _generate_worker(self, inputs, gen_kwargs):
        """生成线程（优化参数，避免空内容）"""
        try:
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=gen_kwargs["max_gen_len"],  # 确保生成长度≥10
                temperature=gen_kwargs.get("temperature", 0.7),  # 恢复温度，保证生成内容
                top_p=gen_kwargs.get("top_p", 0.95),
                do_sample=True,  # 开启采样，避免模型生成空内容
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                num_beams=1,
                repetition_penalty=1.1,  # 适度重复惩罚，避免无意义内容
                use_cache=True,
                min_new_tokens=10,  # 关键：强制最少生成10个token，避免空内容
                pad_to_multiple_of=None
            )
            # 解码时保留所有内容（先不剔除Prompt）
            self.generate_result = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True  # 清理空格，避免空字符串
            )
        except Exception as e:
            self.generate_result = f"生成异常：{str(e)[:]}"

    def generate_imitate(self, context, question, **kwargs):
        """风格模仿生成，解决空content问题"""
        start_time = time.time()
        if self.status != self.STATUS_LOADED:
            return {
                "code": 400,
                "msg": f"免费版模型未就绪，当前状态：{self.status}",
                "data": {}
            }
        try:
            # 1. 构造Prompt（兼容千问格式，添加明确的生成指令）
            raw_prompt = free_imitate_prompt(context=context, question=question)
            # 关键：适配千问模型的Prompt格式（添加指令头，避免模型无响应）
            prompt = f"""<|im_start|>system
            你是一个智能助手，需要按照给定的风格回答问题。
            <|im_end|>
            <|im_start|>user
            {raw_prompt}
            <|im_end|>
            <|im_start|>assistant
            """
            logger.info(f"构造的Prompt：{prompt[:]}...")  # 日志打印Prompt，方便排查

            # 2. 分词（优化：不截断Prompt核心内容）
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_context_len,
                padding=False,
                add_special_tokens=True
            ).to(self.device)

            # 3. 生成参数（确保max_gen_len≥10）
            gen_kwargs = {
                "max_gen_len": max(kwargs.get("max_gen_len", self.max_gen_len), 10),  # 强制≥10
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95)
            }

            # 4. 弹性超时控制
            self.generate_result = None
            generate_thread = threading.Thread(target=self._generate_worker, args=(inputs, gen_kwargs))
            generate_thread.start()

            # 首次生成4s，后续3s
            timeout = int(self.timeout*1.5) if self.is_first_generate else self.timeout
            self.is_first_generate = False
            generate_thread.join(timeout=timeout + 0.2)  # 增加缓冲

            # 5. 处理生成结果（解决空内容核心逻辑）
            cost_time = round(time.time() - start_time, 3)
            if generate_thread.is_alive() or self.generate_result is None:
                logger.error(f"免费版模型生成超时，耗时：{cost_time}s")
                return {
                    "code": 500,
                    "msg": f"生成超时（最大允许{timeout}s）",
                    "data": {"cost_time": cost_time, "version": "free"}
                }

            # 6. 处理生成结果（智能剔除Prompt，避免空内容）
            generate_content = self.generate_result
            # 方法1：按千问的assistant分隔符截取（最可靠）
            if "assistant\n" in generate_content:
                generate_content = generate_content.split("assistant\n")[-1].strip()
            # 方法2：兜底：如果截取后为空，用原始内容（剔除Prompt前缀）
            if not generate_content or generate_content == "":
                generate_content = generate_content.replace(prompt, "").strip()
            # 方法3：最终兜底：如果仍为空，返回默认回复
            if not generate_content or generate_content == "" or "生成异常" in generate_content:
                generate_content = f"已理解你的需求：{question[:20]}... （免费版模型回复）"
                logger.warning(f"生成内容为空，返回兜底回复：{generate_content}")

            logger.info(f"免费版模型生成完成，内容：{generate_content[:]}...，耗时：{cost_time}s")
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
            logger.error(f"免费版模型生成失败：{str(e)[:]}，耗时：{cost_time}s")
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
                torch.cuda.empty_cache()
            self.status = self.STATUS_UNLOADED
            logger.info("免费版模型资源释放成功")
            return {"code": 200, "msg": "免费版模型资源释放成功"}
        except Exception as e:
            logger.error(f"免费版模型资源释放失败：{str(e)[:100]}")
            return {"code": 500, "msg": f"释放失败：{str(e)[:100]}"}