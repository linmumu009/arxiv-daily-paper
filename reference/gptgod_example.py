from openai import OpenAI

client = OpenAI(api_key="xxx", base_url="https://gptgod.cloud/v1")

completion = client.chat.completions.create(
    model="claude-sonnet-4-5-all",
    stream=False,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)

print(completion.choices[0].message)