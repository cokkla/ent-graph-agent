"""Tool 协议 + 注册表 —— 抄 CC 的 buildTool 思路: 加能力 = 加一个工具定义, 主循环不动。

边界约定(为阶段二平迁 MCP server 预留):
- handler 只做纯业务输入输出, 不感知 LLM/消息格式
- 参数校验统一走 pydantic input_model, 错误以 JSON 返回给模型自纠
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ValidationError


@dataclass
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[..., Any]
    is_read_only: bool = True  # 权限语义: 写库/花钱的工具标 False, 供确认策略使用

    def spec(self) -> dict:
        """OpenAI/DashScope/DeepSeek 兼容的 function calling 格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }

    def run(self, raw_args: str | None) -> str:
        try:
            args = self.input_model.model_validate(json.loads(raw_args or "{}"))
        except (json.JSONDecodeError, ValidationError) as e:
            return json.dumps({"error": f"invalid args: {e}"}, ensure_ascii=False)
        try:
            return json.dumps(self.handler(args), ensure_ascii=False, default=str)
        except Exception as e:  # 错误回灌给模型, 让 agent 自己重试/换策略
            return json.dumps(
                {"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False
            )


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def specs(self) -> list[dict]:
        return [t.spec() for t in self._tools.values()]


registry = Registry()
