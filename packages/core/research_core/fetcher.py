import requests
from readability import Document
from bs4 import BeautifulSoup

def fetch_article_text(url: str) -> str:
    """Fetches a webpage and extracts main article text."""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    doc = Document(resp.text)
    html = doc.summary()
    soup = BeautifulSoup(html, "html.parser")

    # Join all text parts
    text = " ".join(p.get_text() for p in soup.find_all("p"))
    return text.strip()
