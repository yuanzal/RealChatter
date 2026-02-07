# -*- coding: utf-8 -*-
"""
免费版AI模型Prompt模板：千问1.8B专用风格模仿模板
核心适配聊天场景风格模仿，简洁通用，保证生成结果贴合上下文风格
"""

def free_imitate_prompt(context: str, question: str) -> str:
    """
    构造免费版风格模仿的标准化Prompt
    :param context: Go服务传入的结构化聊天上下文（历史对话记录）
    :param question: Go服务传入的生成指令/问题（如“模仿上述风格回复：你怎么不回消息？”）
    :return: 模型可直接识别的标准化Prompt字符串
    """
    # 核心Prompt模板：明确指令+上下文+生成问题，适配千问1.8B 4bit量化模型的理解能力
    prompt_template = """
    请严格模仿以下聊天记录的语言风格、语气、口头禅，回答后续问题，生成内容需自然、简短，符合日常聊天场景，不要出现生硬的书面语。
    聊天记录上下文：
    {context}
    待回答问题：
    {question}
    模仿生成结果：
    """
    # 填充参数并清理多余空格/换行，减少无效token，节省推理内存
    prompt = prompt_template.format(context=context, question=question).strip()
    return prompt