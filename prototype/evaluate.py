"""Evaluate the AJATT RAG prototype.

Reports:
  1. Retrieval metrics (Hit@1/3/5/10, MRR at post level) for three configs:
       dense-only | sparse-only | hybrid (RRF)
  2. Generation quality via an LLM judge: faithfulness + answer relevance (1-5)
  3. Per-question results table

Usage:
    python evaluate.py                  # both splits
    python evaluate.py --split test     # test only (used for reporting if necessary)
"""
import argparse
import json
from config import TOP_K
from retrieve import dense_only, sparse_only, retrieve
from pipeline import ask
from generate import call_llm


# ---------- Retrieval metrics ----------

def post_level_hit(retrieved_chunks, gold_slugs):
    """Return the rank (1-based) of the first chunk from any gold post, or None."""
    if not gold_slugs:
        return None
    for rank, chunk in enumerate(retrieved_chunks, start=1):
        if chunk["slug"] in gold_slugs:
            return rank
    return None


def score_retrieval(fn, items, ks=(1, 3, 5, 10)):
    hits = {k: 0 for k in ks}
    mrr_total = 0.0
    n = 0
    for item in items:
        if item.get("expected_refusal"):
            continue  # no gold passage to retrieve
        n += 1
        results = fn(item["question"], top_k=max(ks))
        rank = post_level_hit(results, item["gold_slugs"])
        if rank is not None:
            for k in ks:
                if rank <= k:
                    hits[k] += 1
            mrr_total += 1.0 / rank
    return {
        **{f"Hit@{k}": hits[k] / n for k in ks},
        "MRR": mrr_total / n,
        "n": n,
    }


# ---------- Generation quality (LLM judge) ----------

JUDGE_PROMPT = """You are a strict evaluator for a retrieval-augmented QA system.

Question: {question}

Retrieved context:
{context}

System answer:
{answer}

Rate TWO things, each on a 1-5 integer scale:

FAITHFULNESS: Is every claim in the answer supported by the retrieved context?
  5 = every claim supported; 1 = major unsupported or hallucinated claims.

RELEVANCE: Does the answer actually address the question?
  5 = directly and completely; 1 = off-topic or evasive.

Reply with ONLY this JSON, no other text:
{{"faithfulness": <int>, "relevance": <int>}}
"""

def judge(question, chunks, answer):
    context = "\n\n".join(f"[{c['title']}] {c['text']}" for c in chunks[:5])
    raw = call_llm(JUDGE_PROMPT.format(
        question=question, context=context, answer=answer
    ))
    try:
        parsed = json.loads(raw.strip().strip("`").lstrip("json").strip())
        return int(parsed["faithfulness"]), int(parsed["relevance"])
    except Exception:
        return None, None


def score_generation(items):
    faith_scores, rel_scores, refusals_ok = [], [], 0
    n_refusals = 0
    per_item = []
    for item in items:
        answer, chunks = ask(item["question"], top_k=TOP_K)
        if item.get("expected_refusal"):
            n_refusals += 1
            refused = "don't have enough information" in answer.lower()
            if refused:
                refusals_ok += 1
            per_item.append({
                "id": item["id"], "question": item["question"],
                "answer": answer[:180], "refused": refused,
                "faithfulness": None, "relevance": None,
            })
            continue
        f, r = judge(item["question"], chunks, answer)
        if f is not None:
            faith_scores.append(f)
            rel_scores.append(r)
        per_item.append({
            "id": item["id"], "question": item["question"],
            "answer": answer[:180],
            "refused": None,
            "faithfulness": f, "relevance": r,
        })
    return {
        "faithfulness_avg": sum(faith_scores) / len(faith_scores) if faith_scores else None,
        "relevance_avg": sum(rel_scores) / len(rel_scores) if rel_scores else None,
        "refusal_accuracy": (refusals_ok / n_refusals) if n_refusals else None,
        "per_item": per_item,
    }


def load_items(split=None):
    with open("prototype/eval_questions.json", encoding="utf-8") as f:
        items = json.load(f)
    if split:
        items = [i for i in items if i["split"] == split]
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], default=None)
    args = ap.parse_args()

    items = load_items(args.split)
    print(f"\n=== Evaluating {len(items)} items (split={args.split or 'all'}) ===\n")

    print("--- Retrieval ---")
    for name, fn in [("dense-only", dense_only),
                     ("sparse-only", sparse_only),
                     ("hybrid-RRF", retrieve)]:
        res = score_retrieval(fn, items)
        print(f"{name:12s}  " + "  ".join(
            f"{k}={res[k]:.2f}" for k in ("Hit@1", "Hit@3", "Hit@5", "Hit@10", "MRR")
        ) + f"   (n={res['n']})")

    print("\n--- Generation ---")
    gen = score_generation(items)
    if gen["faithfulness_avg"] is not None:
        print(f"Faithfulness (1-5):   {gen['faithfulness_avg']:.2f}")
        print(f"Relevance    (1-5):   {gen['relevance_avg']:.2f}")
    if gen["refusal_accuracy"] is not None:
        print(f"Refusal accuracy:     {gen['refusal_accuracy']:.2f}")

    print("\n--- Per-question ---")
    for row in gen["per_item"]:
        if row["refused"] is not None:
            if row.get("refused"):
                print(f"[{row['id']}] REFUSED  — {row['question']}")
        else:
            print(f"[{row['id']}] F={row.get('faithfulness')} R={row.get('relevance')}  — {row['question']}")


if __name__ == "__main__":
    main()