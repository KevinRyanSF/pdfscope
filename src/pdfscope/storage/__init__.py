from .json_store import JsonBookmarkStore, caminho_padrao
from .memory import InMemoryBookmarkStore

__all__ = ["InMemoryBookmarkStore", "JsonBookmarkStore", "caminho_padrao"]
