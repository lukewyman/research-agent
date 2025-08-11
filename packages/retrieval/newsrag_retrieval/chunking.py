def simple_chunks(text: str, max_chars: int = 1200, overlap: int = 150):
    """Greedy char-based chunker with overlap (Phase-2 simple baseline)."""
    i, n = 0, len(text)
    while i < n:
        j = min(i + max_chars, n)
        yield text[i:j]
        if j == n: break
        i = max(0, j - overlap)
