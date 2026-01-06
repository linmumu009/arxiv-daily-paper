"""
以下为必选项：
"""

"""API KEY 配置项"""

# minerU Token  
minerU_Token = ""
# Qwen API Key
qwen_api_key = ""




"""PROMPT 配置项"""

# 摘要生成系统提示词中的example
summary_example="""
微软：多模态大模型能力解耦分析
📖标题：What MLLMs Learn about When they Learn about Multimodal Reasoning: Perception, Reasoning, or their Integration?
🌐来源：arXiv, 2510.01719
	
🛎️文章简介
🔸研究问题：多模态大型语言模型（MLLM）在进行多模态推理时，如何分辨出来自感知、推理还是两者的整合的问题？
🔸主要贡献：论文提出了MATHLENS benchmark，旨在分离多模态推理中的感知、推理及其整合能力，提供了新方法以分析模型的性能。
	
📝重点思路
🔸引入MATHLENS基准，通过926道几何问题及其8种视觉修改，设计实验以分离感知、推理和整合能力。
🔸采用四种相关注释，分别测试感知（图形）、推理（文本描述）、多模态问题和微调探测器。
🔸通过先训练文本后训练图像的方式，以评估不同训练策略对模型的影响。
🔸进行对比实验，从开放模型中收集数据，评估7-9B参数范围内的多模态推理模型的表现。
	
🔎分析总结
🔸感知能力主要通过强化学习增强，且在已有文本推理能力的前提下效果更佳。
🔸多模态推理训练同时促进感知与推理的提升，但推理能力并未表现出独立的额外增益。
🔸整合能力是三者中提升最少的，表明存在持续的整合错误，成为主要的失败模式。
🔸在视觉输入变化的情况下，强化学习提高了一致性，而多模态监督微调则导致了过拟合，从而降低了一致性。
	
💡个人观点
论文通过基准明确分离多模态推理的关键能力，使得对模型性能的评估更加细致和准确。
"""
# 摘要生成系统提示词
system_prompt = "你是一个论文总结助手。参考示例的风格与结构，对给定的 Markdown 论文进行中文总结。仅输出纯文本，总结包含：机构、标题、来源、文章简介、重点思路、分析总结或个人观点。"
system_prompt = system_prompt + "\n示例：\n" + summary_example

# 机构判断系统提示词
org_system_prompt = """
你是一个严谨的机构识别助手。仅根据给出的论文前两页文本，识别第一作者与通讯作者各自所属的机构名称（如大学或公司），并从两者中挑选一个最主要的机构作为最终机构。
判断规则：若能识别到通讯作者（例如 *、† 或脚注“Corresponding author”），优先选择通讯作者机构；否则选择第一作者机构。
输出只返回一个 JSON 对象，至少包含键：文件名、机构名、is_large；且建议同时包含第一作者机构与通讯作者机构两个字段以便审阅。
机构名尽量使用中文名称；若无法确定中文名称则保留原文。对于 Google、Meta、Kimi 等全球知名品牌，请保留英文原文，不要翻译。
is_large 为布尔值，true 表示该机构为全球范围内广泛认可的大型或行业可信机构。
只返回 JSON，不要输出其他文本。
"""



"""模型参数配置项"""

# 摘要生成模型


# 摘要生成模型参数 pdfSummary.py
summary_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
summary_model = "qwen2.5-72b-instruct"
summary_max_tokens = 2048
summary_temperature = 1.0


# 机构判别模型参数 json2decide.py
org_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
org_model = "qwen-plus"
org_max_tokens = 2048
org_temperature = 1.0





"""
以下为可选项：
"""


