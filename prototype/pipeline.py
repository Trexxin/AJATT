from retrieve import retrieve
from generate import generate_answer

def ask(question: str, top_k: int = 10):
    chunks = retrieve(question, top_k=top_k)
    if not chunks:
        return "No relevant passages found.", []
    answer = generate_answer(question, chunks)
    return answer, chunks

if __name__ == "__main__":
    questions = [
        "How does AJATT recommend learning vocabulary?",
        "What should I do when I don't understand everything while immersing?",
        "What is sentence mining?",
        "How should I use an SRS?",
    ]
    for q in questions:
        print("=" * 70)
        print("Q:", q)
        answer, chunks = ask(q)
        print("\nANSWER:\n", answer)
        print("\nSOURCES:")
        for c in chunks[:3]:
            print(f"  - {c['title']} ({c['url']})")