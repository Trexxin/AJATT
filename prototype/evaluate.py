# prototype/evaluate.py
import json
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from pipeline import ask

# Load your hand-written questions
with open("prototype/eval_questions.json", encoding="utf-8") as f:
    eval_items = json.load(f)

rows = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
for item in eval_items:
    answer, chunks = ask(item["question"])
    rows["question"].append(item["question"])
    rows["answer"].append(answer)
    rows["contexts"].append([c["text"] for c in chunks])
    rows["ground_truth"].append(item["ground_truth"])

dataset = Dataset.from_dict(rows)

result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_precision],
)
print(result)