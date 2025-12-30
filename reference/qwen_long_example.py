import os
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    api_key="xxxc",  # 如果您没有配置环境变量，请在此处替换您的API-KEY
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 填写DashScope服务base_url
)

file_object = client.files.create(file=Path("阿里云百炼系列手机产品介绍.docx"), purpose="file-extract")
print(file_object.id)
