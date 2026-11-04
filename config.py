"""环境配置：从 .env 读取，集中管理。"""
import os

from dotenv import load_dotenv

load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)

QCC_TOKEN = os.getenv("QCC_TOKEN", "")

DB_PATH = os.getenv("DB_PATH", "data/ent.db")
