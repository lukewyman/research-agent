import hashlib

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def key_page(url: str) -> str:
    return f"page:{sha1(url)}"

def key_embed(model: str, text: str) -> str:
    return f"embed:{model}:{sha1(text)}"
