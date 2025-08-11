import argparse
from newsrag_core import fetch_article_text, summarize

def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    args = p.parse_args()

    print(f"[+] Fetching: {args.url}")
    text = fetch_article_text(args.url)
    print(f"[+] Article length: {len(text)}")
    print("[+] Summarizing...")
    s = summarize(text, source_url=args.url)

    print("\n=== SUMMARY ===")
    print("TL;DR:", s.get("tldr"))
    print("\nKey Points:")
    for b in s.get("bullets", []): print("-", b)
    ev = s.get("evidence") or {}
    print("\nEvidence:", ev.get("quote"))
    if ev.get("note"): print("Note:", ev["note"])

if __name__ == "__main__":
    main()
