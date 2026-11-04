"""LLM 客户端封装 —— qwen-plus 走 DashScope 的 OpenAI 兼容端点。

Provider 边界: 循环层只依赖 openai 消息格式, 换 DeepSeek/GPT 只改这里。
"""
from openai import OpenAI

import config

_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=config.DASHSCOPE_API_KEY, base_url=config.LLM_BASE_URL
        )
    return _client
