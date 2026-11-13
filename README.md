# AJATT

A retrieval-augmented question-answering system built on the archive of the All Japanese All
The Time blog. Ask a question about learning Japanese in English and get an answer grounded
in retrieved blog excerpts, with links to the source posts.

The project has two stages:

1. The scraper downloads and parses the blog into structured JSON.
2. The RAG prototype chunks that JSON, builds dense and BM25 indexes, retrieves relevant
   excerpts, and sends them to an OpenAI-compatible chat-completions endpoint.

## Requirements

- Running on a node in Rosie (setup remote ssh viewing in VSCODE or ssh on to Rosie)
- Python 3.12.11
- Network access to the HPC LLM endpoint for answer generation
- The dependencies in `requirements.txt`

Run all commands below from the repository root (`AJATT`), not from `prototype/`. The scripts
use paths relative to the repository root.

## 1. Clone the repository

Clone the repository and enter its root directory:

```bash
git clone https://github.com/Trexxin/AJATT.git
cd AJATT
```

## 2. Set up the environment

Confirm that Python 3.12.11 is available:

```bash
python --version
```

Create and activate a virtual environment, then install both dependency manifests:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The virtual environment must remain active for the remaining commands. If it is deactivated,
run `source .venv/bin/activate` again from the repository root.

## 3. Get and parse the blog data

The original site is down. A community-run copy is available at
<https://alljapanesealltheti.me/blog/> and is served from the
[all-japanese-all-the-time repository](https://github.com/all-japanese-all-the-time/all-japanese-all-time).

Download posts:

```bash
python scraper/scrape.py --limit 20               # optional quick test
python scraper/scrape.py                          # crawl the whole site
python scraper/scrape.py --from-dir path/to/copy  # use a local site copy
```

Parse the downloaded HTML into JSONL:

```bash
python scraper/parse.py
```

This creates `data/processed/posts.jsonl`, which is the input consumed by the RAG indexer.
Downloaded HTML is stored under `data/raw/posts/`. Existing downloads are skipped, so an
interrupted scrape can be resumed.

## 4. Build the retrieval indexes

Run the index script after parsing the posts:

```bash
python prototype/index.py
```

The script chunks the posts and creates:

- `prototype/faiss.index`: dense vector index using
  `sentence-transformers/all-MiniLM-L6-v2`
- `prototype/bm25.pkl`: sparse BM25 index and chunk metadata
- `prototype/chunks.json`: serialized chunks for lookup and inspection

Re-run this command whenever `data/processed/posts.jsonl` changes. The first run downloads
the embedding model and may take several minutes.

## 5. Test retrieval without the LLM

Once the index files exist, run the retrieval smoke test:

```bash
python prototype/retrieve.py
```

It searches for a sample question and prints the top matching excerpts and their reciprocal
rank-fusion scores. The `retrieve` function can also be imported by code that runs with
`prototype/` on its Python path.

## 6. Configure the LLM endpoint

The generator uses the OpenAI-compatible `/v1/chat/completions` endpoint hosted on the HPC
node. Configure the endpoint by copying the example file to `.env`:

```bash
cp .env_example .env
```

The example uses the default HPC endpoint and model. Edit `.env` if you need different values:

```dotenv
LLM_BASE_URL="http://dh-dgxh100-2.hpc.msoe.edu:8000/v1"
LLM_MODEL="meta/llama-4-scout-17b-16e-instruct"
```

You must be on the network that can resolve and reach `dh-dgxh100-2.hpc.msoe.edu`. The
application defaults `OPENAI_API_KEY` to `not-needed` for this local endpoint. Add
`OPENAI_API_KEY` to `.env` if you use an authenticated endpoint, and do not commit `.env`.

## 7. Run the RAG pipeline

Run the built-in sample questions:

```bash
python prototype/pipeline.py
```

For each question, the pipeline retrieves the top passages, builds a citation-focused prompt,
calls the configured chat-completions endpoint, and prints the answer and source posts.

To call it from another Python program:

```python
from prototype.pipeline import ask

answer, sources = ask("How should I use an SRS?", top_k=10)
print(answer)
for source in sources:
    print(source["title"], source["url"])
```

## 8. Run the evaluation

Create `prototype/eval_questions.json` with evaluation items in this format:

```json
[
  {
    "question": "What is sentence mining?",
    "ground_truth": "The expected answer based on the AJATT archive."
  }
]
```

Then run:

```bash
python prototype/evaluate.py
```

The evaluation script runs every question through the same retrieval and generation pipeline
and reports the RAGAS `faithfulness`, `answer_relevancy`, and `context_precision` metrics.
The LLM endpoint must be configured and reachable because evaluation generates an answer for
each item.

## Project layout

| Path | Purpose |
|---|---|
| `scraper/` | Download and parse the blog archive |
| `data/processed/posts.jsonl` | Parsed post records used by chunking |
| `prototype/chunk.py` | Normalize posts and create overlapping chunks |
| `prototype/index.py` | Build FAISS and BM25 indexes |
| `prototype/retrieve.py` | Hybrid dense/sparse retrieval with reciprocal rank fusion |
| `prototype/generate.py` | OpenAI-compatible LLM client and grounded prompt |
| `prototype/pipeline.py` | Retrieval plus answer generation |
| `prototype/evaluate.py` | RAGAS evaluation |
