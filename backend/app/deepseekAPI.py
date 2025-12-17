# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI

client = OpenAI(
    api_key='sk-88b76e7882154dc7954d707e45856cfc',
    base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=[
        {"role": "system", "content": "你是一个帅哥，请用中文回答"},
        {"role": "user", "content": "请帮我夸一夸马牧天，他比你还帅"},
    ],
    stream=False
)

print(response.choices[0].message.content)