from pathlib import Path
from openai import OpenAI
 
client = OpenAI(
    api_key = "$MOONSHOT_API_KEY",
    base_url = "https://api.moonshot.cn/v1",
)
 
# xlnet.pdf 是一个示例文件, 我们支持 pdf, doc 以及图片等格式, 对于图片和 pdf 文件，提供 ocr 相关能力
file_object = client.files.create(file=Path("xlnet.pdf"), purpose="file-extract")
 
# 获取结果
# file_content = client.files.retrieve_content(file_id=file_object.id)
# 注意，之前 retrieve_content api 在最新版本标记了 warning, 可以用下面这行代替
# 如果是旧版本，可以用 retrieve_content
file_content = client.files.content(file_id=file_object.id).text

example = """
[机构名：如阿里]：解决LLM重复输出问题的实战研究

📘 标题：Solving LLM Repetition Problem in Production: A Comprehensive Study of Multiple Solutions

🌐 来源：(arXiv:2512.04419, 2025)



📝文章简介

🔸 研究问题：在真实生产环境（尤其是批量代码解析场景）中，大模型为什么会陷入“无限重复输出”的卡死状态（repetition / repeater problem），以及用什么方法才能系统地、可靠地把这种重复问题消掉？

🔸 主要贡献：论文基于真实生产故障，总结三类典型 BadCase，给出从解码策略、推理超参到DPO微调的三套方案，并用马尔可夫模型理论化解释“贪心解码为何一旦进环就出不来”。



🧠重点思路

🔸 理论上，重复来自“上下文重复→概率提升→自强化”三步闭环，在贪心解码下，一旦重复token概率被不断放大，就会在马尔可夫链上形成几乎不可逃的循环，期望退出时间趋于无穷。

🔸 方案1：Beam Search（必须搭配 early_stopping=True）保持多条候选路径，只要有一条非重复序列得分可竞争，就能跳出循环；

🔸 方案2：presence_penalty≈1.2 仅对“业务规则生成”这一类BadCase有效，通过惩罚已出现token降低再次生成概率，能在该场景把重复率压到 0。

🔸 方案3：对三类BadCase构造“正确输出 vs 不同重复倍数输出（2/4/8/16次）”的偏好对，做DPO微调，从根本上改变模型对重复模式的偏好，全部BadCase重复率降到 0–2%，处理时间恢复正常。



🔍分析总结

🔸 从工程视角看，Beam Search+early_stopping=True 是最立竿见影、可快速上线的“后处理方案”；presence_penalty 更轻量但强依赖任务形态，泛化有限。

🔸 DPO 微调成本更高，但提供了“模型级修复”，尤其对方法调用分析和PlantUML生成这类结构化任务，能从概率分布上根除“越重复越有利”的自强化偏好。



💡个人观点

🔸 指出 early_stopping 这种常被忽略的小参数其实是生产可用性的生死开关。



                
"""
 
# 把它放进请求中
messages = [
    {
        "role": "system",
        "content": example,
    },
    {
        "role": "system",
        "content": file_content,
    },
    {"role": "user", "content": "请简单介绍 xlnet.pdf 讲了啥"},
]
 
# 然后调用 chat-completion, 获取 Kimi 的回答
completion = client.chat.completions.create(
  model="kimi-k2-turbo-preview",
  messages=messages,
  temperature=0.6,
)
 
print(completion.choices[0].message)