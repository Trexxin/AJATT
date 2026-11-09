import json
import re
import unicodedata
from config import DATA_PATH, CHUNK_SIZE, CHUNK_OVERLAP

def normalize_text(text: str):
    """Remove non-contextual formatting characters and normalize whitespace."""
    text = "".join(
        character
        for character in text
        if not unicodedata.category(character).startswith("C")
        or character in "\t\n\r"
    )
    return " ".join(text.split())

def split_into_sentences(text: str):
    """Naive but effective sentence splitter for English prose."""
    text = normalize_text(text)
    # split on ., !, ? followed by whitespace and a capital letter
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"])', text)
    return [p.strip() for p in parts if p.strip()]

def chunk_text(text: str, size: int, overlap: int):
    text = normalize_text(text)
    sentences = split_into_sentences(text)
    chunks, current, current_len = [], [], 0
    for sent in sentences:
        sent_len = len(sent.split())
        if current_len + sent_len > size and current:
            chunks.append(" ".join(current))
            # keep the last `overlap` tokens for the next chunk
            overlap_sents, overlap_len = [], 0
            for s in reversed(current):
                if overlap_len + len(s.split()) > overlap:
                    break
                overlap_sents.insert(0, s)
                overlap_len += len(s.split())
            current, current_len = overlap_sents, overlap_len
        current.append(sent)
        current_len += sent_len
    if current:
        chunks.append(" ".join(current))
    return chunks

def load_and_chunk(path=DATA_PATH):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            post = json.loads(line)
            if not post.get("body"):
                continue
            for i, chunk in enumerate(chunk_text(post["body"], CHUNK_SIZE, CHUNK_OVERLAP)):
                records.append({
                    "chunk_id": f"{post['slug']}__chunk_{i}",
                    "slug": post["slug"],
                    "url": post["url"],
                    "title": post["title"],
                    "author": post["author"],
                    "categories": post.get("categories", []),
                    "chunk_index": i,
                    "text": chunk,
                })
    return records

if __name__ == "__main__":
    chunks = load_and_chunk()
    print(f"Created {len(chunks)} chunks from posts.")
    # for chunk in chunks[:10]:
    #     print(chunk)