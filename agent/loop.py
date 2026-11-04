"""ReAct 主循环 —— 无意图识别, LLM 自主决定工具调用, 直到产出最终回答。

对标 CC 的 query.ts/queryLoop: 加场景不改这里, 只改 registry 里的工具。
"""
from __future__ import annotations

import os
from typing import Callable

import config
from agent.llm import client
from tools.base import registry

_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "system.md"
)

MAX_TURNS = 12  # 防失控: 单轮用户提问内工具调用循环上限


def get_system_prompt() -> str:
    with open(_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def run_turn(
    messages: list[dict],
    on_event: Callable[[str], None] | None = None,
) -> str:
    """处理一个用户轮次(最后一条消息应为 user)。就地追加 assistant/tool 消息, 返回最终文本。"""
    for _ in range(MAX_TURNS):
        resp = client().chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            tools=registry.specs() or None,
        )
        msg = resp.choices[0].message
        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content or ""

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )
        for tc in msg.tool_calls:
            if on_event:
                on_event(f"⚙ 调用工具 {tc.function.name} {tc.function.arguments}")
            tool = registry.get(tc.function.name)
            result = (
                tool.run(tc.function.arguments)
                if tool
                else '{"error": "unknown tool"}'
            )
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )
    return "（已达到单轮工具调用上限，请缩小问题范围后重试。）"
