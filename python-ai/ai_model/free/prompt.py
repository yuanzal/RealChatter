# -*- coding: utf-8 -*-
"""
免费版AI模型Prompt模板：千问1.8B专用风格模仿模板
核心适配聊天场景风格模仿，简洁通用，保证生成结果贴合上下文风格
"""

def free_imitate_prompt(context: str, question: str) -> str:
    """
      构造免费版风格模仿的标准化Prompt
      :param context: Go服务传入的结构化聊天上下文（历史对话记录）
      :param question: Go服务传入的生成指令/问题（如“我好想你”）
      :return: 模型可直接识别的标准化Prompt字符串
      """
    prompt_template = """
    以下是和我的聊天记录，学习她的说话风格、语气、常用词：
    {context_short}
    
    现在你是，回复这句话：{question}
    要求：
    1. 只说1-2句话，像日常聊天一样自然
    2. 用的语气，比如偶尔带哈哈哈、嗯嗯等口头禅
    3. 不要复制聊天记录，只回复问题
    回复：
    """
    # 填充参数并清理多余空格/换行，减少无效token，节省推理内存
    prompt = prompt_template.format(context=context, question=question).strip()
    return prompt