from openai import OpenAI

from config import LLM_BASE_URL, LLM_MODEL, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY, base_url=LLM_BASE_URL)


def call_llm(prompt: str) -> str:
    response = client.chat.completions.create(
        model=LLM_MODEL or "",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The LLM endpoint returned an empty response.")
    return content

def build_context(chunks):
    """Format retrieved chunks with their metadata for the prompt."""
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[Excerpt {i}] {c['title']} ({c['url']})\n"
            f"Categories: {', '.join(c.get('categories', [])) or 'none'}\n"
            f"{c['text']}"
        )
    return "\n\n".join(parts)

def generate_answer(question: str, chunks):
    prompt = f"""You are an assistant that answers questions about Japanese language learning
using ONLY the AJATT blog archive excerpts below.

Rules:
1. Answer ONLY using the provided excerpts.
2. If the excerpts do not contain enough information, say:
   "I don't have enough information in the AJATT archive to answer that."
3. Always cite the source post title and URL for each claim.
4. Frame advice as "According to AJATT..." — not as general truth.

--- EXCERPTS ---
{build_context(chunks)}
--- END EXCERPTS ---

Question: {question}

Answer (with citations):"""
    return call_llm(prompt)