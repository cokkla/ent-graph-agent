"""CLI 入口 —— 冒烟测试版: 注册演示工具跑通 提问→工具→回答 循环。

qcc 文档到位后: 在 tools/ 下新增 qcc.py / graph_query.py 并在此注册即可。
"""
import datetime
import uuid

from pydantic import BaseModel, Field

import config
from agent.loop import get_system_prompt, run_turn
from store.db import get_conn, init_db
from tools.base import Tool, registry


class NowArgs(BaseModel):
    pass


class DbStatsArgs(BaseModel):
    pass


def _now(_args: NowArgs) -> dict:
    return {"time": datetime.datetime.now().isoformat()}


def _db_stats(_args: DbStatsArgs) -> dict:
    conn = get_conn()
    out = {}
    for t in ("entity", "edge", "qcc_response", "query_log"):
        out[t] = conn.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
    conn.close()
    return out


registry.register(
    Tool("get_current_time", "获取当前时间", NowArgs, _now)
)
registry.register(
    Tool("db_stats", "查看本地图库统计(实体/关系/缓存数量)", DbStatsArgs, _db_stats)
)


def main() -> None:
    init_db()
    print(f"本地库: {config.DB_PATH} | 模型: {config.LLM_MODEL} | 工具: {len(registry.specs())}")
    messages: list[dict] = [{"role": "system", "content": get_system_prompt()}]
    session_id = uuid.uuid4().hex
    while True:
        try:
            q = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q in ("exit", "quit"):
            break
        messages.append({"role": "user", "content": q})
        answer = run_turn(messages, on_event=lambda e: print(e))
        print(f"\n助手> {answer}")
        conn = get_conn()
        conn.execute(
            "INSERT INTO query_log (session_id, question) VALUES (?,?)",
            (session_id, q),
        )
        conn.commit()
        conn.close()


if __name__ == "__main__":
    main()
