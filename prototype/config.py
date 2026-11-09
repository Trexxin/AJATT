import os
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = "data/processed/posts.jsonl"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 200
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 10
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL")