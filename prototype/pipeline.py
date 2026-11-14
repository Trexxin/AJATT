import sys

from retrieve import retrieve
from generate import generate_answer

SAMPLE_QUESTIONS = [
    "How does AJATT recommend learning vocabulary?",
    "What should I do when I don't understand everything while immersing?",
    "What is sentence mining?",
    "What does AJATT say about learning Korean grammar?",
    "How should I use an SRS?",
]

def ask(question: str, top_k: int = 10):
    chunks = retrieve(question, top_k=top_k)
    if not chunks:
        return "No relevant passages found.", []
    answer = generate_answer(question, chunks)
    return answer, chunks

def print_answer(question: str):
    print("=" * 70)
    print("Q:", question)
    answer, chunks = ask(question)
    print("\nANSWER:\n", answer)
    print("\nSOURCES:")
    for c in chunks[:3]:
        print(f"  - {c['title']} ({c['url']})")

if __name__ == "__main__":
    # Any questions typed after the script name get answered.
    # If there aren't any, it runs the sample questions.
    questions = sys.argv[1:] or SAMPLE_QUESTIONS
    for q in questions:
        print_answer(q)